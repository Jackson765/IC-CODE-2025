#!/usr/bin/env python3
"""
Servo Controller - Controls two servo channels with toggle positions
GPIO outputs 5V for servo signals - duty cycle adjusted accordingly
"""

import pigpio
import time
from typing import Dict

class ServoController:
    def __init__(self, pi: pigpio.pi, config: Dict):
        self.pi = pi
        self.config = config['servos']
        self.servos = {}
        
        # Voltage compensation: GPIO is 3.3V but servos need 5V signals
        # For PWM servo signals, the pulse timing matters, not voltage
        # pigpio handles this correctly - no compensation needed
        
        self.setup_servos()
    
    def setup_servos(self):
        """Initialize servo channels with toggle positions"""
        print("[Servo] Initializing servo controller...")
        
        for name, servo_config in self.config.items():
            # Skip comment fields
            if name.startswith('_'):
                continue
            
            # Ensure servo_config is a dict
            if not isinstance(servo_config, dict):
                print(f"[Servo] Skipping {name} - invalid config type")
                continue
            
            if not servo_config.get('enabled', False):
                print(f"[Servo] {name} disabled in config")
                continue
            
            gpio = servo_config['gpio']
            if gpio == 0:
                print(f"[Servo] {name} not configured (GPIO = 0)")
                continue
            
            # Setup GPIO for servo - CRITICAL: Set mode first!
            self.pi.set_mode(gpio, pigpio.OUTPUT)
            
            # IMPORTANT: Stop any existing servo signal first
            self.pi.set_servo_pulsewidth(gpio, 0)
            time.sleep(0.1)
            
            # Start at MIN position (lower limit)
            min_pulse = servo_config.get('min_pulse_us', 575)
            self.pi.set_servo_pulsewidth(gpio, min_pulse)
            
            # Verify it's working
            actual_pulse = self.pi.get_servo_pulsewidth(gpio)
            if actual_pulse == 0:
                print(f"[Servo] ⚠️ {name} - Failed to set pulse! Check GPIO {gpio}")
            else:
                print(f"[Servo] {name} initialized on GPIO {gpio} - pulse: {actual_pulse}us")
            
            self.servos[name] = {
                'gpio': gpio,
                'min_pulse': min_pulse,
                'max_pulse': servo_config.get('max_pulse_us', 2460),
                'current_pulse': min_pulse,
                'at_max': False  # Track position state
            }
            
            print(f"[Servo] {name} ready - Range: {min_pulse}us to {self.servos[name]['max_pulse']}us")
        
        if not self.servos:
            print("[Servo] No servos configured")
    
    def toggle_servo(self, name: str):
        """Toggle servo between MIN and MAX positions"""
        if name not in self.servos:
            return False
        
        servo = self.servos[name]
        
        # Toggle between min and max
        if servo['at_max']:
            # Go to MIN
            pulse = servo['min_pulse']
            servo['at_max'] = False
        else:
            # Go to MAX
            pulse = servo['max_pulse']
            servo['at_max'] = True
        
        self.pi.set_servo_pulsewidth(servo['gpio'], pulse)
        servo['current_pulse'] = pulse
        
        print(f"[Servo] {name} toggled to {'MAX' if servo['at_max'] else 'MIN'} ({pulse}us)")
        
        return True
    
    def set_servo_pulse(self, name: str, pulse_width_us: int):
        """Set servo pulse width directly (for compatibility)"""
        if name not in self.servos:
            return False
        
        servo = self.servos[name]
        
        # Clamp to valid range
        pulse_width_us = max(servo['min_pulse'], min(servo['max_pulse'], pulse_width_us))
        
        self.pi.set_servo_pulsewidth(servo['gpio'], pulse_width_us)
        servo['current_pulse'] = pulse_width_us
        
        # Update toggle state based on position
        mid_point = (servo['min_pulse'] + servo['max_pulse']) / 2
        servo['at_max'] = pulse_width_us > mid_point
        
        return True
        
        servo = self.servos[name]
        
        # Clamp value
        value = max(-1.0, min(1.0, value))
        
        # Map to pulse width
        center = (servo['min_pulse'] + servo['max_pulse']) / 2
        half_range = (servo['max_pulse'] - servo['min_pulse']) / 2
        pulse_width = int(center + (value * half_range))
        
        return self.set_servo_pulse(name, pulse_width)
    
    def set_servo_percent(self, name: str, percent: float):
        """
        Set servo position with percentage (0-100)
        0% = min pulse, 100% = max pulse
        """
        if name not in self.servos:
            return False
        
        servo = self.servos[name]
        
        # Clamp percent
        percent = max(0, min(100, percent))
        
        # Map to pulse width
        pulse_range = servo['max_pulse'] - servo['min_pulse']
        pulse_width = int(servo['min_pulse'] + (pulse_range * percent / 100))
        
        return self.set_servo_pulse(name, pulse_width)
    
    def get_servo_pulse(self, name: str) -> int:
        """Get current pulse width"""
        if name not in self.servos:
            return 0
        return self.servos[name]['current_pulse']
    
    def disable_servo(self, name: str):
        """Disable servo (stop sending pulses)"""
        if name not in self.servos:
            return False
        
        servo = self.servos[name]
        self.pi.set_servo_pulsewidth(servo['gpio'], 0)
        return True
    
    def cleanup(self):
        """Clean up servo resources"""
        print("[Servo] Cleaning up...")
        for name, servo in self.servos.items():
            self.pi.set_servo_pulsewidth(servo['gpio'], 0)
