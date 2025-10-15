# UTi 260B Thermal Camera Recording Tools

Dual camera recording system for synchronizing UTi 260B thermal camera with 4K webcam.

## Directory Structure

```
uti_thermal/
├── scripts/           # Python recording tools
├── old_recordings/    # Previous test recordings
├── test_files/        # Test images and previews
├── utilities/         # Third-party utilities (UNI-T tools)
└── recording_*/       # New recordings (auto-created with timestamps)
```

## Quick Start

### Dual Camera Recording (Thermal + 4K Webcam)
```bash
cd C:\Users\andre\Claude\uti_thermal
python scripts\dual_recorder.py 1
```

**Controls:**
- Press **'q'** or **ESC** to stop recording
- Press **'s'** to save snapshot from both cameras

**Output:** Creates a timestamped folder with:
- `*_thermal.avi` - Raw thermal feed (240x321)
- `*_webcam.avi` - Raw 4K webcam feed (3840x2160 or 1920x1080)
- `*_combined.avi` - Side-by-side view with overlays
- `*_timestamps.json` - UTC timestamp for every frame
- `*_summary.txt` - Recording summary

### Thermal Camera Only
```bash
python scripts\thermal_recorder.py
```

### Extract Frames with UTC Timestamps
```bash
# Extract all frames
python scripts\extract_frames.py recording_*/recording_*_thermal.avi recording_*/recording_*_timestamps.json

# Extract every 30 frames (~1 per second)
python scripts\extract_frames.py recording_*/recording_*_thermal.avi recording_*/recording_*_timestamps.json 30
```

## Available Scripts

### Main Scripts
- **`dual_recorder.py`** - Record from thermal camera + webcam simultaneously
- **`thermal_recorder.py`** - Record from thermal camera only
- **`extract_frames.py`** - Extract frames with exact UTC timestamps

### Utility Scripts
- **`detect_4k.py`** - Test which cameras support high resolution
- **`quick_detect.py`** - Quick camera detection
- **`capture_bmp_utc.py`** - Capture thermal BMPs with UTC timestamps
- **`keep_alive_test.py`** - Test thermal camera auto-shutoff prevention

## Camera Setup

### UTi 260B Settings
1. Connect via USB-C
2. Navigate to USB mode on device
3. Select **"USB Camera"** mode (not USB Disk)
4. Make sure device is showing thermal image (not menu)
5. Set auto power-off to 30 minutes in device settings

### 4K Webcam
- Automatically detected and configured
- Camera index 1 typically
- Resolution: 3840x2160 or 1920x1080 depending on camera

## Timestamp System

Every frame has an exact UTC timestamp recorded in the JSON file:

```json
{
  "frame_number": 150,
  "utc_time": "2025-10-15T02:33:24.443717+00:00",
  "unix_timestamp": 1729831404.443717,
  "elapsed_seconds": 3.003
}
```

This allows frame-perfect synchronization between thermal and webcam videos, even if they have different framerates.

## Tips

- **Keep UTi 260B alive:** Set auto power-off to 30 min in device settings
- **Choose correct webcam:** Use `python dual_recorder.py [camera_index]` to specify
- **Organize recordings:** New recordings auto-create timestamped folders
- **Extract temperature data:** Use UNI-T-Thermal-Utilities for saved BMP files from device

## Notes

- USB camera mode provides RGB video, not raw radiometric data
- For raw temperature per-pixel, save images on device and use utilities/UNI-T-Thermal-Utilities
- OCR can be used to extract temperature values from overlays in video
