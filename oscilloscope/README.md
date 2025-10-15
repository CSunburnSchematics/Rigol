# DS1054Z Oscilloscope USB Control Scripts

Python scripts for controlling and capturing data from a Rigol DS1054Z oscilloscope with DS1104Z firmware over USB.

## Setup

### Prerequisites
- Python 3.12+
- DS1054Z oscilloscope connected via USB
- WinUSB driver installed (via Zadig)
- libusb-1.0.dll (located in `lib/`)

### Installation
All required Python packages:
```bash
pip install ds1054z pyvisa pyvisa-py pyusb numpy matplotlib pandas
```

## Key Scripts

### Working Scripts (Recommended)

**capture_waveform.py**
- Single waveform capture from Channel 1
- Saves CSV data and PNG plot
- Shows voltage statistics
- ~1,200 points per capture

**capture_10sec.py**
- Continuous capture over 10 seconds
- Custom timebase setting (currently 200μs/div)
- Creates comprehensive 4-panel visualization
- UTC timestamped data
- Gap detection

**optimized_long_capture.py**
- Long-term data logging (30 seconds default)
- Real-time progress display
- Timestamps on every sample
- Gap analysis
- Handles timeout errors gracefully

**view_waveform.py**
- View existing CSV waveform files
- Add UTC timestamps to data
- Create plots with statistics

### Utility Scripts

**connect_scope.py**
- Test basic connection to oscilloscope
- Display scope information
- Check channel status

**check_usb_devices.py**
- Diagnose USB connection issues
- Verify PyUSB backend
- List available devices

**live_monitor.py**
- Real-time oscilloscope monitoring with live-updating plots
- 4-panel vertical visualization:
  - UTC timeline showing waveform data and capture gaps
  - Transfer times for gap detection
  - Sample waveforms (last 3 captures, scatter plot)
  - Voltage distribution histogram
- Auto-saves all raw data to CSV with UTC timestamps
- Auto-saves final plot when complete
- Interactive window updates as data is captured

**live_monitor_demo.py**
- Non-interactive version of live_monitor.py
- Auto-saves plot and exits (no window required)
- Same CSV logging and 4-panel layout
- Good for testing or running in headless environments

### Experimental Scripts

**deep_memory_capture.py**
- Attempts to capture deep memory using RAW mode
- Currently has timeout issues over USB
- May require NI-VISA instead of PyVISA-py

## Performance Characteristics

### Screen Buffer Captures (What Works)
- **Buffer size**: 1,200 points per capture
- **Transfer time**: ~0.2-0.3 seconds per capture
- **Capture rate**: ~3-5 captures/second
- **Effective sampling**: ~4,000-6,000 points/second
- **Reliability**: Good with proper delays

### Deep Memory Transfers (Experimental)
- **Theoretical max**: Up to 24M points
- **Current status**: Timeout issues over USB
- **Possible solution**: NI-VISA drivers instead of PyVISA-py

## Folder Structure

```
oscilloscope/
├── scripts/      # Python scripts
├── data/         # CSV data files
├── plots/        # PNG visualizations
├── docs/         # Documentation and guides
└── lib/          # libusb libraries and dependencies
```

## Usage Examples

### Basic Capture
```bash
cd oscilloscope/scripts
python capture_waveform.py
```

### 10-Second Continuous Capture
```bash
cd oscilloscope/scripts
python capture_10sec.py
```

### Long-Term Logging
```bash
cd oscilloscope/scripts
python optimized_long_capture.py
```

### View Existing Data
```bash
cd oscilloscope/scripts
python view_waveform.py ../data/waveform_ch1.csv
```

## Data Format

All CSV files include:
- **UTC_Timestamp**: ISO 8601 format timestamp
- **Time_Offset_s**: Time from start of capture
- **Voltage_V**: Measured voltage value
- **Capture_Num**: Which capture this sample belongs to (for continuous captures)

## Known Issues

1. **Timeout errors**: Occur after 2-5 captures in continuous mode
   - Workaround: Increase delays between captures

2. **RAW mode not working**: Deep memory transfers timeout
   - May need NI-VISA drivers
   - Alternative: Use screen buffer captures

3. **Fast timebase issues**: Very fast timebases (< 200μs/div) cause more timeouts
   - Workaround: Use slower timebases

## Connection Details

- **Device**: RIGOL TECHNOLOGIES, DS1104Z
- **Serial**: DS1ZA192006991
- **Firmware**: 00.04.05.SP2
- **Resource**: USB0::6833::1230::DS1ZA192006991::0::INSTR

## Documentation

See `docs/` folder for:
- USB setup guide
- libusb installation guide
- Programming guide excerpts from Grok
