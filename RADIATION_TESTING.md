# Radiation Testing Workflow

Simple workflow for running radiation tests with synchronized oscilloscope and camera data capture.

## Quick Start

### 1. Launch Test Systems

```bash
python launch_radiation_test.py GAN_HV_TESTCONFIG.json gan_test_1
```

This will:
- Create a timestamped test directory: `radiation_tests/YYYYMMDD_HHMMSS_UTC_gan_test_1/`
- Launch oscilloscope capture in a new window
- Launch webcam recorder in a new window
- Exit immediately (both systems run independently)

### 2. Run Your Test

- **Oscilloscope window**: Shows live 16-channel waveform capture
- **Webcam window**: Shows live thermal + 4K webcam feed
- Let both systems run during your radiation test
- Press **'q'** in each window when test is complete

### 3. Organize Test Files

After stopping both recordings:

```bash
python organize_test.py 20251015_123456_UTC_gan_test_1
```

This will:
- Move all oscilloscope CSV files into test directory
- Move oscilloscope plots into test directory
- Move webcam videos into test directory
- Create TEST_SUMMARY.txt with complete file listing
- Clean up empty temporary directories

## Available Configurations

### GaN High Voltage Test
```bash
python launch_radiation_test.py GAN_HV_TESTCONFIG.json gan_hv_test
```

16 channels monitoring:
- **Scope *260**: EPC2206 devices (4 channels @ 20V/div)
- **Scope *375**: IGT65 devices (4 channels @ 200V/div)
- **Scope *665**: GPI900 devices (4 channels @ 200V/div)
- **Scope *823**: IGL65 devices (4 channels @ 200V/div)

### Linear Technology RAD Test
```bash
python launch_radiation_test.py LT_RAD_TESTCONFIG.json lt_rad_test
```

16 channels @ 60µs/div, 240 points per channel

## Test Directory Structure

After organizing, your test directory will contain:

```
radiation_tests/20251015_123456_UTC_gan_test_1/
├── oscilloscope_data/
│   ├── multiscope_DS1ZA273M00260_20251015_123502.csv
│   ├── multiscope_DS1ZA269M00375_20251015_123502.csv
│   ├── multiscope_DS1ZA172215665_20251015_123502.csv
│   ├── multiscope_DS1ZA276M00823_20251015_123503.csv
│   └── performance_GAN_HV_TESTCONFIG_20251015_123515.txt
├── oscilloscope_plots/
│   └── multiscope_16ch_20251015_123515.png
├── webcam_videos/
│   ├── recording_20251015_123502_UTC_thermal.avi
│   ├── recording_20251015_123502_UTC_webcam.avi
│   ├── recording_20251015_123502_UTC_combined.avi
│   ├── recording_20251015_123502_UTC_timestamps.json
│   └── recording_20251015_123502_UTC_summary.txt
├── test_metadata/
│   └── test_info.txt
└── TEST_SUMMARY.txt
```

## Troubleshooting

### Oscilloscope window doesn't open
- Check that all 4 scopes are connected via USB
- Verify libusb drivers are installed
- Run `python oscilloscope/scripts/detect_scopes.py` to verify connectivity

### Webcam window doesn't open
- Ensure UTi 260B thermal camera is connected (USB-C)
- Ensure 4K webcam is connected
- Close Uti-Live Screen software if running
- Set UTi 260B to 'USB Camera' mode (not USB Disk)
- Run `python uti_thermal/scripts/detect_cameras.py` to test

### Files don't move when organizing
- Check that timestamps match (files created on same date as test)
- Verify files exist in `data/`, `plots/`, and `recordings/` directories
- Files are matched by date in filename (YYYYMMDD)

## Tips

1. **Use descriptive test names**: `python launch_radiation_test.py GAN_HV_TESTCONFIG.json epc2206_batch3_dose100krad`

2. **Take notes during test**: Edit `test_metadata/test_info.txt` in the test directory to add observations

3. **Check coverage**: Look at `performance_*.txt` files for temporal coverage percentage

4. **Verify sync**: Check `timestamps.json` in webcam videos to correlate with oscilloscope capture times

## Why Two Scripts?

The original approach tried to manage both processes from a master script, but the oscilloscope window blocked execution. This two-step approach:

1. **Launches** both systems as truly independent Windows processes
2. **Organizes** files afterward when both have completed

This ensures both windows work properly without interference.
