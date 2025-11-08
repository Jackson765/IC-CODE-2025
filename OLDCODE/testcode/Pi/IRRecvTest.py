import pigpio
import time

# GPIO pins for IR receivers  
IR_RX_GPIOS = [4, 27, 12]

# Protocol timing
BIT_0_BURST = 800
BIT_1_BURST = 1600  
START_END_BURST = 2400
TOLERANCE = 200

class BufferedIRReceiver:
    def __init__(self, gpio_pin):
        self.gpio = gpio_pin
        self.pi = pigpio.pi()
        self.bursts = []
        self.last_tick = 0
        self.last_burst_time = 0
        
        self.pi.set_mode(self.gpio, pigpio.INPUT)
        self.pi.set_pull_up_down(self.gpio, pigpio.PUD_UP)
        
        self.cb = self.pi.callback(self.gpio, pigpio.EITHER_EDGE, self.edge_callback)
        print(f"Monitoring GPIO {self.gpio}")
        
    def edge_callback(self, gpio, level, tick):
        current_time = time.time()
        
        if level == 0:  # Start of IR burst
            self.last_tick = tick
            
        elif level == 1 and self.last_tick:  # End of IR burst
            burst_width = pigpio.tickDiff(self.last_tick, tick)
            
            # If it's been more than 100ms since last burst, start new transmission
            if current_time - self.last_burst_time > 0.1:
                if len(self.bursts) > 0:
                    self.process_bursts()
                self.bursts = []
                print(f"GPIO {gpio}: New transmission started")
            
            self.bursts.append(burst_width)
            self.last_burst_time = current_time
            print(f"GPIO {gpio}: Burst {len(self.bursts)}: {burst_width}µs")
            
            # If we have 10 bursts, process immediately
            if len(self.bursts) == 10:
                self.process_bursts()
                self.bursts = []
    
    def process_bursts(self):
        if len(self.bursts) != 10:
            print(f"GPIO {self.gpio}: Incomplete transmission: {len(self.bursts)} bursts")
            return
            
        print(f"GPIO {self.gpio}: Complete transmission: {self.bursts}")
        
        # Check start and end bursts
        if (abs(self.bursts[0] - START_END_BURST) > TOLERANCE or 
            abs(self.bursts[9] - START_END_BURST) > TOLERANCE):
            print(f"GPIO {self.gpio}: Invalid start/end bursts")
            return
            
        # Decode middle 8 bits
        player_id = 0
        bits_str = ""
        
        for i in range(1, 9):
            burst = self.bursts[i]
            bit_pos = 7 - (i - 1)
            
            if abs(burst - BIT_1_BURST) <= TOLERANCE:
                player_id |= (1 << bit_pos)
                bits_str += "1"
            elif abs(burst - BIT_0_BURST) <= TOLERANCE:
                bits_str += "0"
            else:
                print(f"GPIO {self.gpio}: Invalid burst {burst}µs at position {i}")
                return
                
        print(f"GPIO {self.gpio}: Bits: {bits_str}")
        print(f"GPIO {self.gpio}: *** PLAYER ID: {player_id} ***")
        print()
        
    def cleanup(self):
        # Process any remaining bursts
        if len(self.bursts) > 0:
            self.process_bursts()
        self.cb.cancel()

def main():
    print("Buffered IR Receiver")
    print("Expected values:")
    print(f"  Start/End: ~{START_END_BURST}µs")
    print(f"  Bit 1: ~{BIT_1_BURST}µs") 
    print(f"  Bit 0: ~{BIT_0_BURST}µs")
    print("Press Ctrl+C to stop\n")
    
    pi = pigpio.pi()
    if not pi.connected:
        print("Run: sudo pigpiod")
        raise SystemExit
    pi.stop()
    
    receivers = []
    for gpio in IR_RX_GPIOS:
        receivers.append(BufferedIRReceiver(gpio))
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        for receiver in receivers:
            receiver.cleanup()

if __name__ == "__main__":
    main()
