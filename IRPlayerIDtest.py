import pigpio
import time

IR_TX_GPIO = 17  # GPIO pin to MOSFET gate

# IR carrier setup
CARRIER_FREQ = 38000
CARRIER_PERIOD_US = int(1_000_000 / CARRIER_FREQ)
PULSE_ON_US = CARRIER_PERIOD_US // 2
PULSE_OFF_US = CARRIER_PERIOD_US - PULSE_ON_US

PLAYER_ID = 3  # change this for each player (1–255)

pi = pigpio.pi()
if not pi.connected:
    print("Run: sudo pigpiod")
    raise SystemExit

pi.set_mode(IR_TX_GPIO, pigpio.OUTPUT)
pi.write(IR_TX_GPIO, 0)

def send_burst(burst_us):
    """Send a modulated IR burst for burst_us microseconds."""
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

def send_bit(bit):
    if bit == 1:
        send_burst(1600)  # '1' = 1.6 ms burst
    else:
        send_burst(800)   # '0' = 0.8 ms burst
    time.sleep(0.0008)    # space between bits

def send_player_id(pid):
    # Start bit
    send_burst(2400)  
    time.sleep(0.0008)
    # Send 8-bit player ID
    for i in range(8):
        send_bit((pid >> (7 - i)) & 1)
    # End burst
    send_burst(2400)

try:
    while True:
        send_player_id(PLAYER_ID)
        print(f"Sent Player ID: {PLAYER_ID}")
        time.sleep(1)  # send once per second
except KeyboardInterrupt:
    pass
finally:
    pi.write(IR_TX_GPIO, 0)
    pi.stop()
