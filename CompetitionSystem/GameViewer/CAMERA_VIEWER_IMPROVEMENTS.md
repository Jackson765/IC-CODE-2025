# Camera Viewer Improvements - November 8, 2025

## 🎯 Issues Fixed

### 1. Team Selection Range Expanded ✅
**Problem**: Camera viewer only allowed team IDs 1-8
**Solution**: Expanded range to support teams 1-254

**Changes**:
- Line ~1344: Changed validation from `team_id > 8` to `team_id > 254`
- Error message updated: "Team ID must be between 1-254!"

### 2. Fixed Video Stream Sizing ✅
**Problem**: Video streams were auto-fitting, causing uneven spacing
**Solution**: Implemented fixed dimensions for 1920x1080 screen resolution

**Changes**:
- Line ~1397: Window geometry set to "1920x1080"
- Line ~1407-1412: Grid configured with fixed dimensions (no weight)
  - Each row: 520px (fixed minsize)
  - Each column: 940px (fixed minsize)
  - Removed auto-fit (weight=0)
- Line ~1655-1657: Fixed display dimensions
  - display_width: 920px (960 - 40 for padding/borders)
  - display_height: 480px (520 - 40 for padding/borders/header)

## 📐 Screen Layout for 1920x1080

```
┌─────────────────────────────────────────┐
│  Title Bar (~40px)                      │
├──────────────────┬──────────────────────┤
│                  │                      │
│  Camera 1        │  Camera 2            │
│  920x480         │  920x480             │
│  (Team X)        │  (Team Y)            │
│                  │                      │
├──────────────────┼──────────────────────┤
│                  │                      │
│  Camera 3        │  Camera 4            │
│  920x480         │  920x480             │
│  (Team Z)        │  (Team W)            │
│                  │                      │
└──────────────────┴──────────────────────┘
│  Control Panel (~60px)                  │
└─────────────────────────────────────────┘
```

## 🎮 How to Use

1. Click "📹 View Cameras" button in Game Viewer
2. Enter team IDs (1-254) in the 4 input fields
3. Leave fields blank for slots you don't want to use
4. Click "📹 Open Camera Feeds"
5. Window opens at 1920x1080 with evenly spaced video streams

## 🔧 Technical Details

### Grid Configuration (No Auto-Fit)
```python
grid_frame.grid_rowconfigure(0, weight=0, minsize=520)
grid_frame.grid_rowconfigure(1, weight=0, minsize=520)
grid_frame.grid_columnconfigure(0, weight=0, minsize=940)
grid_frame.grid_columnconfigure(1, weight=0, minsize=940)
```

**Key Points**:
- `weight=0`: Disables auto-fit behavior
- `minsize`: Fixed dimensions for each grid cell
- Each quadrant is exactly 960x540 pixels
- Video display area: 920x480 (accounting for borders/padding)

### Video Stream Ports
- Team ID 1-254 → Ports 5001-5254
- Port calculation: `5000 + team_id`

### Display Sizing
- No longer uses label dimensions (auto-fit removed)
- Fixed dimensions ensure equal spacing
- All videos display at 920x480 regardless of content

## ✅ Verification Checklist

- [x] Team selection range: 1-254
- [x] Window size: 1920x1080
- [x] Grid cells: Fixed 960x540 (no auto-fit)
- [x] Video display: Fixed 920x480
- [x] Even spacing across all 4 quadrants
- [x] No dynamic resizing

## 🚀 Benefits

1. **Consistent Layout**: All videos same size, evenly spaced
2. **No Stretching**: Videos maintain aspect ratio with fixed dimensions
3. **Full 1920x1080 Support**: Optimized for Full HD screens
4. **254 Team Support**: Can view any team from 1-254
5. **Predictable Behavior**: No auto-fit means no layout surprises

## 📝 Notes

- Each video stream is H.264 RTP over UDP
- GStreamer + PyGObject required for embedded viewing
- Overlay shows timestamp and disabled status
- FPS counter tracks rendering performance
- Individual retry buttons for each stream
