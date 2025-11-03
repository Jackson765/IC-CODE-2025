# 📹 Camera Viewer Updates

## ✅ Changes Made

### 1. **Open with Less Than 4 Teams**
- ✅ Removed the requirement for teams to be connected before opening
- ✅ Can now select 1-4 teams (any combination)
- ✅ Empty slots show "-- Empty Slot --" 
- ✅ Works even if no teams are registered yet

### 2. **Individual Retry Buttons**
- ✅ Each camera feed now has its own **🔄 Retry** button
- ✅ Retry a single feed without affecting others
- ✅ Retry button is always visible at the bottom of each feed
- ✅ Shows status: "🔄 Retrying..." when clicked

### 3. **Better Error Handling**
- ✅ Team ID validation (must be 1-8)
- ✅ No longer requires team to be connected to open viewer
- ✅ Shows clear error messages on each feed
- ✅ Click "Retry" button to attempt reconnection

## 🎮 How to Use

### Opening Camera Viewer

1. Click **"📹 View Cameras"** button (works anytime!)
2. Enter team IDs (1-8) - leave empty slots blank
3. Click **"📹 Open Camera Feeds"**

**Examples:**
- Want to watch 2 teams? Enter IDs in Camera 1 and 2, leave 3 and 4 empty
- Want to watch 1 team? Enter ID in Camera 1 only
- Teams not connected yet? No problem! Enter IDs and they'll connect when available

### Using Retry Buttons

**For Individual Feeds:**
- Lost connection on Camera 2? 
- Click the **🔄 Retry** button below that specific feed
- Only that feed reconnects, others keep running

**For All Feeds:**
- Click the **🔄 Reconnect All** button at the bottom
- All feeds will attempt to reconnect simultaneously

## 📊 Status Indicators

Each feed shows:
- ✅ **Connected** (green) - Stream is active
- 🟢 **Live** (green) - Receiving frames
- ⏳ **Initializing** (yellow) - Starting connection
- 🔄 **Retrying** (yellow) - Attempting reconnection
- ⚠️ **No Frames** (orange) - Connected but no data
- ❌ **Failed to Open** (red) - Connection failed
- ❌ **Error** (red) - Technical error occurred

## 💡 Pro Tips

1. **Pre-configure before teams arrive:**
   - Open camera viewer with team IDs 1, 2, 3, 4
   - Feeds will auto-connect when teams register
   - No need to wait!

2. **Selective monitoring:**
   - Only watch teams 2 and 5? Enter just those IDs
   - Don't waste screen space on teams you don't care about

3. **Quick recovery:**
   - Robot rebooted? Click individual retry
   - Network glitch? Click reconnect all
   - No need to close and reopen window

4. **Multiple viewers:**
   - Open multiple camera viewer windows
   - Each can show different teams
   - Monitor finals on one screen, practice on another

## 🔧 Technical Details

- Each feed operates independently
- Failed connections don't block other feeds
- Automatic frame dropping prevents UI lag
- GStreamer pipeline auto-recovers from network issues
- Maximum 4 feeds per window (2x2 grid)

## 🎯 Use Cases

### Scenario 1: Tournament Setup
```
Teams haven't arrived yet, but you want to be ready:
- Open camera viewer
- Enter IDs 1, 2, 3, 4
- Feeds show "Connecting..." until teams arrive
- Auto-connect when robots start streaming
```

### Scenario 2: Finals Match
```
Only 2 teams competing:
- Camera 1: Team 3
- Camera 2: Team 7  
- Camera 3: (empty)
- Camera 4: (empty)
Focus on just the active match!
```

### Scenario 3: Connection Issues
```
Team 2's robot lost WiFi:
- Other 3 feeds still working perfectly
- Click retry button on Team 2's feed
- Connection restored without disrupting others
```

### Scenario 4: Multi-Monitor Setup
```
Open 2 camera viewer windows:
- Monitor 1: Teams 1-4 (arena A)
- Monitor 2: Teams 5-8 (arena B)
Simultaneous tournament management!
```

## 🚀 Quick Reference

| Action | Button/Method |
|--------|--------------|
| Open viewer | Click "📹 View Cameras" |
| Retry single feed | Click "🔄 Retry" below feed |
| Retry all feeds | Click "🔄 Reconnect All" at bottom |
| Close viewer | Close window (auto-cleanup) |
| Change teams | Close window, click "View Cameras" again |

---

**All changes are backwards compatible!**
Existing functionality still works, just with more flexibility. 🎉
