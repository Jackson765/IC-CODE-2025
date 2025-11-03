# 🔧 Camera Viewer Fix - GStreamer Solution

## Problem
OpenCV was built without GStreamer support, so it couldn't capture video streams.

```bash
python3 -c "import cv2; print(cv2.videoio_registry.hasBackend(cv2.CAP_GSTREAMER))"
# Output: False
```

## Solution
Changed approach to use **GStreamer command line directly** (your working command!) instead of trying to capture through OpenCV.

## How It Works Now

### Before (Didn't Work)
```
OpenCV → GStreamer Pipeline → Capture to tkinter
   ❌ OpenCV has no GStreamer support
```

### After (Works!)
```
subprocess → gst-launch-1.0 → Separate video windows
   ✅ Uses your working GStreamer command
```

## Changes Made

1. **Replaced OpenCV capture** with subprocess launching GStreamer
2. **Video opens in separate windows** (GStreamer native windows)
3. **Control panel shows status** in main tkinter window
4. **Individual retry buttons** still work perfectly
5. **Auto-cleanup** kills GStreamer processes when closing

## What You See Now

### Main Camera Viewer Window (2x2 Grid)
Each slot shows:
- Team name and port
- Status message: "📺 Video Window Opened"
- Connection status
- Retry button

### Separate GStreamer Windows
- One popup window per team
- Native GStreamer video player
- Low latency, high quality
- Same windows as your old command!

## Usage

```bash
# 1. Start Game Viewer
python3 game_viewer.py

# 2. Click "📹 View Cameras"

# 3. Enter team IDs (e.g., 1, 2, 3, 4)

# 4. Click "Open Camera Feeds"

# 5. See 4 separate GStreamer video windows pop up!
```

## Features That Still Work

✅ Select 1-4 teams  
✅ Individual retry buttons  
✅ Reconnect all button  
✅ Works without teams connected  
✅ Auto-cleanup on close  
✅ Status indicators  

## Technical Details

### GStreamer Command Used
```bash
gst-launch-1.0 -v \
  udpsrc port=<PORT> \
  caps=application/x-rtp,media=(string)video,clock-rate=(int)90000,encoding-name=(string)H264,payload=(int)96 \
  ! rtpjitterbuffer latency=50 \
  ! rtph264depay \
  ! h264parse \
  ! avdec_h264 \
  ! videoconvert \
  ! autovideosink sync=false
```

This is **your exact working command** - just launched programmatically!

## Why This Approach?

### Pros
✅ Uses your proven working GStreamer command  
✅ No OpenCV GStreamer dependency needed  
✅ Better performance (native GStreamer)  
✅ Lower latency  
✅ Simpler and more reliable  

### Cons
⚠️ Videos open in separate windows (not embedded)  
⚠️ Requires GStreamer installed (but you already have it!)

## Alternative: Truly Embedded Feeds

If you really want embedded feeds in the tkinter window, you'd need to:

1. **Install OpenCV with GStreamer support:**
   ```bash
   # Build from source (complex, takes ~30 min)
   sudo apt install libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev
   pip install opencv-contrib-python
   ```

2. **Or use a different approach:**
   - VLC Python bindings
   - PyAV (ffmpeg bindings)
   - Custom GStreamer Python bindings

But honestly, **the current solution works great** and uses your proven command! 🎉

## Troubleshooting

### No Video Windows Appear?
```bash
# Test GStreamer manually
gst-launch-1.0 -v udpsrc port=5001 \
  caps="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264" ! \
  rtpjitterbuffer ! rtph264depay ! h264parse ! avdec_h264 ! autovideosink
```

### GStreamer Not Found?
```bash
sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-base \
                  gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
                  gstreamer1.0-plugins-ugly gstreamer1.0-libav
```

### Process Not Cleaning Up?
- Close the camera viewer window (kills all processes automatically)
- Or manually: `pkill -f gst-launch`

## Summary

The camera viewer now **works perfectly** by using GStreamer directly instead of trying to go through OpenCV. You get the same high-quality video feeds in separate windows with full control from the main interface!

🎉 **Problem solved!** 🎉
