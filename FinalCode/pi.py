#!/usr/bin/env python3
"""
Integrated Laser Tag Robot Control System with Self-Hit Detection
Combines: Xbox controller input, IR transmission/reception, motor control, video streaming
"""

import asyncio
import json
import math
import os
import signal
import subprocess
import sys
import time
import threading
import pigpio

import requests

# ===================== USER CONFIG =====================
PI_UDP_PORT = 5005
PC_VIDEO_IP = "192.168.50.142"  # Your laptop IP - UPDATED
# GV_IP = "game_viewer.local"
GV_IP = "192.168.50.142:8080"
PC_VIDEO_PORT = 5600

# Motor pins (BCM)
MOTORS = {
    "A": {"EN": 18, "IN1": 23, "IN2": 24, "corner": "FL"},
    "B": {"EN": 19, "IN1": 25, "IN2": 8, "corner": "FR"},
    "C": {"EN": 5, "IN1": 22, "IN2": 26, "corner": "RL"},
    "D": {"EN": 6, "IN1": 16, "IN2": 20, "corner": "RR"},
}

# IR Configuration
IR_TX_GPIO = 17  # IR transmitter pin
IR_RX_GPIOS = [4, 27, 12]  # IR receiver pins

# IR Protocol timing
CARRIER_FREQ = 38000
CARRIER_PERIOD_US = int(1_000_000 / CARRIER_FREQ)
PULSE_ON_US = CARRIER_PERIOD_US // 2
PULSE_OFF_US = CARRIER_PERIOD_US - PULSE_ON_US

BIT_0_BURST = 800
BIT_1_BURST = 1600
START_END_BURST = 2400
TOLERANCE = 200

# Motor configuration
DIR_OFFSET = {"A": 1, "B": 1, "C": 1, "D": 1}
STBY_PINS = [9, 11]
PWM_FREQ_HZ = 10000
MIN_DUTY_FLOOR = 30
PURE_DC_THRESHOLD = 80

# Timeouts
COMMAND_TIMEOUT_S = 0.8
POWER_SAVE_TIMEOUT_S = 10.0
HIT_DISABLE_TIME = 10.0  # Seconds robot is disabled when hit
# =======================================================

# Global variables
pi = None
last_cmd_time = 0.0
last_input_time = 0.0
in_standby = False
gst_proc = None
ir_receivers = []

# Robot state
state = {
    "vx": 0.0, "vy": 0.0, "omega": 0.0, "speed": 1.0, 
    "estop": False, "fire": False, "team_id": 1
}

# Laser tag state
laser_tag_state = {
    "is_hit": False,
    "hit_by_team": 0,
    "hit_time": 0,
    "time_remaining": 0,
    "is_self_hit": False  # Added for self-hit detection
}

def init_pigpio():
    """Initialize pigpio connection"""
    global pi
    pi = pigpio.pi()
    if not pi.connected:
        print("ERROR: pigpiod not running. Run: sudo pigpiod", file=sys.stderr)
        sys.exit(1)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def setup_io():
    """Setup all GPIO pins"""
    # Enable STBY pins
    for s in STBY_PINS:
        pi.set_mode(s, pigpio.OUTPUT)
        pi.write(s, 1)
    
    # Motor pins
    for m in MOTORS.values():
        for k in ("EN", "IN1", "IN2"):
            pi.set_mode(m[k], pigpio.OUTPUT)
            pi.write(m[k], 0)
        pi.set_PWM_frequency(m["EN"], PWM_FREQ_HZ)
    
    # IR transmitter
    pi.set_mode(IR_TX_GPIO, pigpio.OUTPUT)
    pi.write(IR_TX_GPIO, 0)

def stop_all_motors():
    """Stop all motors"""
    for m in MOTORS.values():
        pi.set_PWM_dutycycle(m["EN"], 0)
        pi.write(m["IN1"], 0)
        pi.write(m["IN2"], 0)

def enter_standby():
    """Enter power saving mode"""
    print("[Power] Entering standby mode")
    stop_all_motors()
    for s in STBY_PINS:
        pi.write(s, 0)

def exit_standby():
    """Exit power saving mode"""
    print("[Power] Exiting standby mode")
    for s in STBY_PINS:
        pi.write(s, 1)
    time.sleep(0.01)

def apply_motor(name, norm):
    """Apply motor control with PWM"""
    norm = clamp(norm, -1.0, 1.0) * DIR_OFFSET[name]
    pins = MOTORS[name]
    
    if abs(norm) < 1e-3:
        pi.set_PWM_dutycycle(pins["EN"], 0)
        pi.write(pins["IN1"], 0)
        pi.write(pins["IN2"], 0)
        return
    
    forward = norm > 0
    pi.write(pins["IN1"], 1 if forward else 0)
    pi.write(pins["IN2"], 0 if forward else 1)
    
    pct = int(abs(norm) * 100)
    if pct >= PURE_DC_THRESHOLD:
        pi.write(pins["EN"], 1)
    else:
        pct = max(MIN_DUTY_FLOOR, pct)
        duty = pct * 255 // 100
        pi.set_PWM_dutycycle(pins["EN"], duty)

def drive_mecanum(vx, vy, omega, max_speed=1.0):
    """Drive mecanum wheels"""
    fl = vy + vx + omega
    fr = -vy + vx - omega
    rl = -vy + vx + omega
    rr = vy + vx - omega
    
    scale = max(1.0, abs(fl), abs(fr), abs(rl), abs(rr))
    fl /= scale; fr /= scale; rl /= scale; rr /= scale
    
    fl *= max_speed; fr *= max_speed; rl *= max_speed; rr *= max_speed
    
    apply_motor("A", fl)
    apply_motor("B", fr)
    apply_motor("C", rl)
    apply_motor("D", rr)

# ========== IR TRANSMISSION ==========
def send_ir_burst(burst_us):
    """Send modulated IR burst"""
    pi.wave_clear()
    cycle = [
        pigpio.pulse(1 << IR_TX_GPIO, 0, PULSE_ON_US),
        pigpio.pulse(0, 1 << IR_TX_GPIO, PULSE_OFF_US)
    ]
    pi.wave_add_generic(cycle)
    wid = pi.wave_create()
    cycles = burst_us // CARRIER_PERIOD_US
    pi.wave_chain([255, 0, wid, 255, 1, cycles & 255, (cycles >> 8) & 255])
    while pi.wave_tx_busy():
        time.sleep(0.0001)
    pi.wave_delete(wid)

def send_ir_bit(bit):
    """Send IR bit"""
    if bit == 1:
        send_ir_burst(BIT_1_BURST)
    else:
        send_ir_burst(BIT_0_BURST)
    time.sleep(0.0008)

def send_team_id(team_id):
    """Send team ID via IR"""
    if laser_tag_state["is_hit"]:
        return  # Can't fire when hit
    
    print(f"[IR] Firing! Team {team_id}")
    
    # Start bit
    send_ir_burst(START_END_BURST)
    time.sleep(0.0008)
    
    # Send 8-bit team ID
    for i in range(8):
        send_ir_bit((team_id >> (7 - i)) & 1)
    
    # End burst
    send_ir_burst(START_END_BURST)

# ========== IR RECEPTION ==========
class IRReceiver:
    def __init__(self, gpio_pin):
        self.gpio = gpio_pin
        self.bursts = []
        self.last_tick = 0
        self.last_burst_time = 0
        
        pi.set_mode(self.gpio, pigpio.INPUT)
        pi.set_pull_up_down(self.gpio, pigpio.PUD_UP)
        
        self.cb = pi.callback(self.gpio, pigpio.EITHER_EDGE, self.edge_callback)
        print(f"[IR] Monitoring receiver on GPIO {self.gpio}")
    
    def edge_callback(self, gpio, level, tick):
        current_time = time.time()
        
        if level == 0:  # Start of IR burst
            self.last_tick = tick
        elif level == 1 and self.last_tick:  # End of IR burst
            burst_width = pigpio.tickDiff(self.last_tick, tick)
            
            # New transmission if gap > 100ms
            if current_time - self.last_burst_time > 0.1:
                if len(self.bursts) > 0:
                    self.process_bursts()
                self.bursts = []
            
            self.bursts.append(burst_width)
            self.last_burst_time = current_time
            
            # Process when we have complete transmission
            if len(self.bursts) == 10:
                self.process_bursts()
                self.bursts = []
    
    def process_bursts(self):
        """Process received IR bursts to decode team ID"""
        if len(self.bursts) != 10:
            return
        
        # Check start and end bursts
        if (abs(self.bursts[0] - START_END_BURST) > TOLERANCE or 
            abs(self.bursts[9] - START_END_BURST) > TOLERANCE):
            return
        
        # Decode middle 8 bits
        team_id = 0
        for i in range(1, 9):
            burst = self.bursts[i]
            bit_pos = 7 - (i - 1)
            
            if abs(burst - BIT_1_BURST) <= TOLERANCE:
                team_id |= (1 << bit_pos)
            elif abs(burst - BIT_0_BURST) <= TOLERANCE:
                pass  # bit is 0
            else:
                return  # Invalid burst
        
        # Valid hit received - including self-hits for testing!
        on_laser_hit(team_id)
    
    def cleanup(self):
        self.cb.cancel()

def on_laser_hit(attacking_team):
    """Handle being hit by laser - UPDATED with self-hit detection"""
    global laser_tag_state
    
    if laser_tag_state["is_hit"]:
        return  # Already hit
    
    # Check for self-hit (for testing)
    if attacking_team == state["team_id"]:
        print(f"[LaserTag] SELF HIT DETECTED! Team {attacking_team} hit themselves!")
        # For testing, we'll still register it but mark it as a self-hit
        laser_tag_state.update({
            "is_hit": True,
            "hit_by_team": attacking_team,
            "hit_time": time.time(),
            "time_remaining": HIT_DISABLE_TIME,
            "is_self_hit": True  # Add this flag
        })
    else:
        print(f"[LaserTag] HIT! Attacked by team {attacking_team}")
        laser_tag_state.update({
            "is_hit": True,
            "hit_by_team": attacking_team,
            "hit_time": time.time(),
            "time_remaining": HIT_DISABLE_TIME,
            "is_self_hit": False
        })
    
    # Disable robot immediately (even for self-hits in testing)
    stop_all_motors()
    enter_standby()

# ========== VIDEO STREAMING ==========
def start_gstreamer_sender():
    """Start video stream to laptop"""
    global gst_proc
    cmd = (
        f"rpicam-vid -t 0 --width 1280 --height 720 --framerate 30 "
        f"--codec h264 --bitrate 4000000 --profile baseline --intra 30 --inline "
        f"--nopreview -o - | "
        f"gst-launch-1.0 -v fdsrc ! h264parse ! "
        f"rtph264pay config-interval=1 pt=96 ! "
        f"udpsink host={PC_VIDEO_IP} port={PC_VIDEO_PORT} sync=false async=false"
    )
    
    gst_proc = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
    print(f"[Video] Stream started → {PC_VIDEO_IP}:{PC_VIDEO_PORT}")

def stop_gstreamer_sender():
    """Stop video stream"""
    global gst_proc
    if gst_proc and gst_proc.poll() is None:
        try:
            os.killpg(os.getpgid(gst_proc.pid), signal.SIGTERM)
            gst_proc.wait(timeout=2)
        except:
            pass
        print("[Video] Stream stopped")
    gst_proc = None

# ========== UDP CONTROL ==========
class ControlProtocol(asyncio.DatagramProtocol):
    def datagram_received(self, data, addr):
        global last_cmd_time, last_input_time, in_standby, laser_tag_state
        
        try:
            msg = json.loads(data.decode("utf-8"))
        except Exception:
            return
        
        # Update state from controller
        state["vx"] = float(msg.get("vx", state["vx"]))
        state["vy"] = float(msg.get("vy", state["vy"]))
        state["omega"] = float(msg.get("omega", state["omega"]))
        state["speed"] = clamp(float(msg.get("speed", state["speed"])), 0.0, 1.0)
        state["estop"] = bool(msg.get("estop", False))
        state["fire"] = bool(msg.get("fire", False))
        state["team_id"] = int(msg.get("team_id", state["team_id"]))
        
        last_cmd_time = time.time()
        
        if "last_input_time" in msg:
            last_input_time = float(msg["last_input_time"])
        
        # Handle fire command
        if state["fire"] and not laser_tag_state["is_hit"]:
            # Fire IR in separate thread to avoid blocking
            threading.Thread(target=lambda: send_team_id(state["team_id"]), daemon=True).start()
        
        # Exit standby if needed
        if in_standby and (abs(state["vx"]) > 0.05 or abs(state["vy"]) > 0.05 or 
                          abs(state["omega"]) > 0.05 or state["estop"]):
            exit_standby()
            in_standby = False
        
        # Send status back to laptop - UPDATED with self-hit info
        response = {
            "team_id": state["team_id"],
            "is_hit": laser_tag_state["is_hit"],
            "hit_by_team": laser_tag_state["hit_by_team"],
            "time_remaining": laser_tag_state["time_remaining"],
            "is_self_hit": laser_tag_state["is_self_hit"]  # Add this
        }
        
        try:
            self.transport.sendto(json.dumps(response).encode("utf-8"), addr)
        except Exception:
            pass

async def control_loop():
    """Main control loop"""
    global last_cmd_time, last_input_time, in_standby, laser_tag_state
    
    while True:
        now = time.time()
        
        # Update laser tag timer
        if laser_tag_state["is_hit"]:
            elapsed = now - laser_tag_state["hit_time"]
            laser_tag_state["time_remaining"] = max(0, HIT_DISABLE_TIME - elapsed)
            
            if elapsed >= HIT_DISABLE_TIME:
                if laser_tag_state["is_self_hit"]:
                    print("[LaserTag] Self-hit timer expired - Respawning!")
                else:
                    print("[LaserTag] Respawning!")
                
                laser_tag_state.update({
                    "is_hit": False,
                    "hit_by_team": 0,
                    "hit_time": 0,
                    "time_remaining": 0,
                    "is_self_hit": False  # Reset self-hit flag
                })
                exit_standby()
                in_standby = False
        
        # Motor control logic
        if laser_tag_state["is_hit"] or state["estop"] or (now - last_cmd_time) > COMMAND_TIMEOUT_S:
            stop_all_motors()
        elif (now - last_input_time) > POWER_SAVE_TIMEOUT_S and not in_standby:
            enter_standby()
            in_standby = True
        elif not in_standby and not laser_tag_state["is_hit"]:
            drive_mecanum(state["vx"], state["vy"], state["omega"], state["speed"])
        
        await asyncio.sleep(0.02)  # 50 Hz

def setup_ir_receivers():
    """Initialize IR receivers"""
    global ir_receivers
    for gpio in IR_RX_GPIOS:
        ir_receivers.append(IRReceiver(gpio))

def cleanup():
    """Clean up resources"""
    print("\n[Shutdown] Cleaning up...")
    
    # Stop motors and disable standby
    stop_all_motors()
    for s in STBY_PINS:
        pi.write(s, 0)
    
    # Clean up IR
    for receiver in ir_receivers:
        receiver.cleanup()
    
    # Stop video
    stop_gstreamer_sender()
    
    # Close pigpio
    if pi:
        pi.stop()

async def main():
    """Main function"""
    global last_cmd_time, last_input_time
    
    print("🎯 Integrated Laser Tag Robot System 🎯")
    print("🧪 TESTING MODE: Self-hit detection enabled!")
    print("=" * 50)
    
    # Initialize everything
    init_pigpio()
    setup_io()
    setup_ir_receivers()
    start_gstreamer_sender()
    # r = requests.get(f"http://{GV_IP}/")
    r = requests.put(f"http://{GV_IP}/robots",json = {"team_id":"-1"})
    r = requests.put(f"http://{GV_IP}/robots",json = {"team_id":-1})
    # r = requests.get("http://192.168.50.200:8080/")
    
    # Initialize timestamps
    now = time.time()
    last_cmd_time = now
    last_input_time = now
    
    print(f"[LaserTag] Team ID: {state['team_id']}")
    print(f"[Testing] Self-hits will be detected and reported!")
    
    # Start UDP server
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: ControlProtocol(),
        local_addr=("0.0.0.0", PI_UDP_PORT)
    )
    
    print(f"[Control] UDP listening on 0.0.0.0:{PI_UDP_PORT}")
    print(f"[Safety] Robot stops if no command for {COMMAND_TIMEOUT_S}s")
    print(f"[Power] Standby after {POWER_SAVE_TIMEOUT_S}s of no input")
    print(f"[LaserTag] {HIT_DISABLE_TIME}s disable time when hit")
    print(f"[Video] Streaming to {PC_VIDEO_IP}:{PC_VIDEO_PORT}")
    
    try:
        await control_loop()
    finally:
        transport.close()
        cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Shutdown] Received interrupt")
    except Exception as e:
        print(f"[Error] {e}")
    finally:
        cleanup()
