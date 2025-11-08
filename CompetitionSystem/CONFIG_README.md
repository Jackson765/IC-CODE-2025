# Configuration System - Single Source of Truth

## Overview
The robot's `Pi/team_config.json` is now the **ONLY** configuration file you need to manage. The laptop automatically requests and receives this config from the Pi at startup.

## How It Works

### 1. **Pi is the Source of Truth**
   - All team info, network settings, and hardware config lives in `Pi/team_config.json`
   - Pi sends its config to the laptop when requested

### 2. **Laptop Startup Flow**
   1. Laptop prompts user for robot IP address
   2. Laptop sends `CONFIG_REQUEST` to Pi
   3. Pi responds with `CONFIG_RESPONSE` containing full config
   4. Laptop uses this config for all operations

### 3. **Auto-Calculated Values**
   - **GV Video Port**: Automatically `5000 + team_id`
     - Team 1 → Port 5001
     - Team 2 → Port 5002
     - etc.
   - **Laptop IP**: Auto-detected from first connection
   - **Laptop Listen Port**: `6100 + team_id`

### 4. **Laptop Controls**
   - Keyboard controls are laptop-specific and saved in `laptop_controls.json`
   - These are NOT in the Pi config since they're personal preferences

## What You Need to Configure

### In `Pi/team_config.json`:
- `team.team_id` - Your team number
- `team.team_name` - Your team name
- `team.robot_name` - Your robot's name
- `network.robot_ip` - Your Pi's IP address
- `network.game_viewer_ip` - Game Viewer computer IP
- All GPIO pins, motors, servos, etc.

### At Laptop Startup:
- Robot IP address (saved for next time)

## Benefits
✅ **No More Duplicate Configs** - One file to rule them all  
✅ **Auto-Calculated Ports** - No manual port assignment needed  
✅ **Dynamic Laptop IP** - Works from any laptop without config changes  
✅ **Team ID Determines Everything** - Just set your team ID once  

## Network Ports Summary
| Service | Port Formula | Example (Team 1) |
|---------|-------------|------------------|
| Pi Listen | 5005 (constant) | 5005 |
| Laptop Video | 5100 (constant) | 5100 |
| GV Video | 5000 + team_id | 5001 |
| GV Control | 6000 (constant) | 6000 |
| Laptop Listen | 6100 + team_id | 6101 |

## Migration from Old System
If you had `laptop_config.json`, you can delete it. The laptop now gets everything from the Pi.
