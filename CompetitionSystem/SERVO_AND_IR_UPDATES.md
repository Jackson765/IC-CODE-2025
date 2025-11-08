# Servo and IR System Updates

## Changes Made

### 1. IR System - Now Hardcoded ✅
**Location**: `Pi/ir_controller.py`

- **IR configuration removed from `team_config.json`**
- All IR settings are now **HARDCODED** in `ir_controller.py`
- Teams **CANNOT** modify IR protocol, timing, or pins
- Settings locked:
  ```python
  Transmitter GPIO: 20
  Receiver GPIOs: [3, 25, 21]
  Carrier Frequency: 38kHz
  Weapon Cooldown: 2000ms
  Hit Disable Time: 10s
  ```

### 2. Servo Control - Toggle Mode 🔄
**Location**: `Pi/servo_controller.py`, `Laptop/laptop_control.py`

#### Old Behavior:
- Hold Q/Z to continuously move servo 1
- Hold E/C to continuously move servo 2
- Position shown as percentage (0-100%)

#### New Behavior:
- **Q or Z** - Toggle Servo 1 between MIN and MAX
- **E or C** - Toggle Servo 2 between MIN and MAX
- Position shown as **MIN** or **MAX**
- Instant switching between positions
- No continuous movement

#### Technical Details:
- Servos start at **MIN position** (575µs)
- Toggle switches to **MAX position** (2460µs)
- Full 202° range for HS-311 servos
- GPIO outputs PWM signal (pigpio handles voltage correctly)
- No voltage compensation needed - PWM timing is what matters

### 3. Shot Counter - Actually Accurate Now 🎯
**Location**: `Pi/main.py`, `Laptop/laptop_control.py`

#### Old Problem:
- Laptop counted fire button presses
- Didn't account for weapon cooldown
- Showed more shots than actually fired

#### New Solution:
- Pi sends `fire_success: true` back to laptop when weapon actually fires
- Laptop only increments counter when Pi confirms
- Respects 2-second cooldown properly
- **Accurate shot count** now! 🎉

### 4. Voltage Handling 🔌
**Note in `servo_controller.py`**:
- GPIO outputs 3.3V logic levels
- Servos expect 5V signal lines (separate servo power is 5V)
- **PWM pulse timing** is what controls servos, not voltage amplitude
- pigpio library handles this correctly
- No manual voltage compensation needed

## Configuration Changes

### team_config.json
**Removed Section**:
```json
"ir_system": {
  // DELETED - now hardcoded
}
```

**Servo Section** (unchanged):
```json
"servos": {
  "servo_1": {
    "gpio": 19,
    "min_pulse_us": 575,    // MIN position
    "max_pulse_us": 2460,   // MAX position
    "enabled": true
  },
  "servo_2": {
    "gpio": 11,
    "min_pulse_us": 575,
    "max_pulse_us": 2460,
    "enabled": true
  }
}
```

## User Controls

### Laptop GUI
- **Q/Z** - Toggle Servo 1 (same key both directions now)
- **E/C** - Toggle Servo 2 (same key both directions now)
- Servo display shows: **MIN** or **MAX**
- Shot counter now accurate with IR cooldown

### Message Format (Laptop → Pi)
```json
{
  "type": "CONTROL",
  "servo1_toggle": true,   // true = MAX, false = MIN
  "servo2_toggle": false,
  "fire": true
}
```

### Response Format (Pi → Laptop)
```json
{
  "type": "STATUS",
  "fire_success": true  // Only true if weapon actually fired
}
```

## Benefits

✅ **IR Protocol Locked** - No accidental/intentional modifications  
✅ **Faster Servo Response** - Instant toggle vs slow continuous  
✅ **Accurate Shot Tracking** - Respects cooldown properly  
✅ **Simpler Controls** - Same key toggles both directions  
✅ **Voltage Handling** - Documented and correct  

## Technical Notes

### Servo PWM Details
- Frequency: 50Hz (20ms period)
- Min Pulse: 575µs = ~2.9% duty cycle
- Max Pulse: 2460µs = ~12.3% duty cycle
- Range: 202° of rotation (HS-311 spec)

### IR Protocol (Locked)
- Carrier: 38kHz
- Bit 0: 800µs burst
- Bit 1: 1600µs burst
- Start/End: 2400µs burst
- Tolerance: ±200µs
