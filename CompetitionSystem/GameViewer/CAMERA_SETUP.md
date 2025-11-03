# 📹 Camera Viewer Setup Guide

## Installation (Ubuntu 24.04)

### Required Packages

```bash
# Install OpenCV and Pillow for embedded video feeds
sudo apt install -y python3-opencv python3-pil python3-pil.imagetk

# Install GStreamer for video pipeline support
sudo apt install -y gstreamer1.0-tools gstreamer1.0-plugins-base \
                     gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
                     gstreamer1.0-plugins-ugly gstreamer1.0-libav
```

### Verify Installation

```bash
python3 -c "import cv2; print('OpenCV:', cv2.__version__)"
python3 -c "from PIL import Image; print('Pillow: OK')"
```

## How to Use

### 1. Start the Game Viewer

```bash
cd /home/rbandaru/Desktop/IC-CODE-2025/CompetitionSystem/GameViewer
python3 game_viewer.py
```

### 2. Wait for Robots to Register

- Teams will automatically register when they connect
- You'll see them appear in the "Connected Teams" panel

### 3. Open Camera Viewer

1. Click the **"📹 View Cameras"** button
2. A dialog will appear asking you to select 4 teams
3. Enter the Team IDs (1-8) for the teams you want to watch
4. The dialog pre-fills with the first 4 connected teams
5. Click **"📹 Open Camera Feeds"**

### 4. Embedded Video Window

The camera viewer will open showing a 2x2 grid with:
- **Team name and ID** for each feed
- **Live video stream** embedded in the window
- **Status indicators** (Connected/No Signal/Error)
- **FPS counter** showing performance
- **Reconnect button** to restart failed streams

## Features

✅ **Embedded Feeds** - Videos display directly in the window (no popups!)
✅ **Team Selection** - Choose exactly which 4 teams to watch
✅ **Live Updates** - Real-time video at ~30 FPS
✅ **Status Monitoring** - See connection status for each feed
✅ **Easy Reconnect** - One-click to reconnect all streams
✅ **Timestamp Overlay** - Each video shows current time

## Troubleshooting

### No Video Appearing?

1. **Check if robots are streaming:**
   ```bash
   # On Game Viewer machine, check if UDP packets are arriving
   sudo tcpdump -i any udp port 5001 -c 10
   ```

2. **Test GStreamer directly:**
   ```bash
   gst-launch-1.0 -v udpsrc port=5001 \
     caps="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264" ! \
     rtpjitterbuffer ! rtph264depay ! h264parse ! avdec_h264 ! autovideosink
   ```

3. **Check firewall:**
   ```bash
   sudo ufw allow 5001:5008/udp
   ```

### "Connection Failed" Error?

- Make sure the robot is actually streaming video
- Verify the team is registered (appears in Connected Teams list)
- Check that the UDP port matches (Team 1 = 5001, Team 2 = 5002, etc.)
- Try clicking "🔄 Reconnect All"

### Low FPS or Laggy Video?

- This is normal on slower machines
- The system automatically drops frames to prevent lag
- Video is optimized for tournament monitoring, not recording

### OpenCV Import Error?

```bash
# Make sure packages are installed
sudo apt install python3-opencv python3-pil python3-pil.imagetk

# Verify installation
python3 -c "import cv2; print('OK')"
```

## Technical Details

- **Video Format:** H.264 over RTP/UDP
- **Resolution:** 640x480 (configurable on Pi)
- **Frame Rate:** ~30 FPS (adaptive)
- **Latency:** 50ms jitter buffer
- **Port Range:** 5001-5008 (8 teams max)

## Camera Viewer Architecture

```
Robot Pi → UDP Stream → Game Viewer Machine
   ↓                           ↓
Camera                    OpenCV Capture
   ↓                           ↓
H.264                    GStreamer Pipeline
   ↓                           ↓
RTP/UDP                  Decode & Display
Port 5001-5008           Tkinter Window
```

## Example Usage

```python
# Game starts with 4 teams registered: 1, 2, 5, 7

1. Click "📹 View Cameras"
2. Enter:
   - Camera 1: 1
   - Camera 2: 2  
   - Camera 3: 5
   - Camera 4: 7
3. Click "Open Camera Feeds"
4. Enjoy the 2x2 grid of live robot cameras!
```

## Notes

- You can open multiple camera viewer windows
- Each window can show different teams
- Closing the viewer stops the streams automatically
- The main Game Viewer continues running independently
