# Radiation Testing - Quick Start

## Single Command Workflow

```bash
python launch_test.py GAN_HV_TESTCONFIG.json my_test_name
```

That's it! Everything is automatic:

1. **Launch**: Both oscilloscope and cameras start
2. **Record**: Let it capture data during your test
3. **Stop**: Press **'q'** in EITHER window
4. **Done**: All files automatically organized with manifest

## What Happens Automatically

When you press 'q' in any window:
- ✅ Both systems stop immediately
- ✅ All oscilloscope CSVs moved to test directory
- ✅ All oscilloscope plots moved to test directory
- ✅ All webcam videos moved to test directory
- ✅ Test manifest created with full metadata
- ✅ Human-readable summary created

## Output Directory Structure

```
radiation_tests/20251015_130000_UTC_my_test_name/
├── oscilloscope_data/
│   ├── multiscope_DS1ZA273M00260_20251015_130015.csv
│   ├── multiscope_DS1ZA269M00375_20251015_130015.csv
│   ├── multiscope_DS1ZA172215665_20251015_130015.csv
│   ├── multiscope_DS1ZA276M00823_20251015_130016.csv
│   └── performance_GAN_HV_TESTCONFIG_20251015_130045.txt
├── oscilloscope_plots/
│   └── multiscope_16ch_20251015_130045.png
├── webcam_videos/
│   ├── recording_20251015_130002_UTC_thermal.avi
│   ├── recording_20251015_130002_UTC_webcam.avi
│   ├── recording_20251015_130002_UTC_combined.avi
│   ├── recording_20251015_130002_UTC_timestamps.json
│   └── recording_20251015_130002_UTC_summary.txt
├── test_metadata/
│   └── test_manifest.json
└── TEST_SUMMARY.txt
```

## Available Configurations

### GaN High Voltage Test
```bash
python launch_test.py GAN_HV_TESTCONFIG.json gan_hv_test
```
- 16 channels: EPC2206, IGT65, GPI900, IGL65 devices
- 4 oscilloscopes monitoring voltage transients

### Linear Technology RAD Test
```bash
python launch_test.py LT_RAD_TESTCONFIG.json lt_rad_test
```
- 16 channels @ 60µs/div
- 240 points per channel

## Tips

**Descriptive Test Names:**
```bash
python launch_test.py GAN_HV_TESTCONFIG.json epc2206_batch3_100krad
```

**Quick Tests:**
```bash
python launch_test.py GAN_HV_TESTCONFIG.json quicktest
```

**Press 'q' in ANY Window:**
- Oscilloscope window? Press 'q' → both stop
- Webcam window? Press 'q' → both stop
- No need to close both separately!

## What Changed From Old Workflow?

**Old Way (Clunky):**
1. `python launch_radiation_test.py config.json name`
2. Wait for both to start
3. Press 'q' in oscilloscope window
4. Press 'q' in webcam window
5. `python organize_test.py 20251015_HHMMSS_UTC_name`
6. Check if files moved correctly

**New Way (Simple):**
1. `python launch_test.py config.json name`
2. Press 'q' in ANY window
3. Done! Everything organized automatically

## Troubleshooting

**Cameras don't appear:**
- Check USB connections
- Close Uti-Live Screen software
- Ensure UTi 260B in 'USB Camera' mode
- Script waits 15 seconds for camera initialization

**Oscilloscopes not found:**
- Verify USB connections to all 4 scopes
- Run `python oscilloscope/scripts/detect_scopes.py`

**Files not in test directory:**
- Check timestamp matching (files must have same date)
- Look in `data/`, `plots/`, `recordings/` for recent files
- Check console output for errors during file moving
