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

### Memory Depth vs Capture Rate Trade-offs

The DS1054Z oscilloscope has a fundamental trade-off between memory depth (points per capture) and capture rate. Based on empirical testing at 10us/div timebase:

| Memory Depth | Time/Capture | Capture Rate | Coverage | Sample Rate | Use Case |
|--------------|--------------|--------------|----------|-------------|----------|
| 300 pts      | ~30 us      | ~4.7 cap/s   | ~0.01%   | 25 MSa/s    | Fast events, low coverage |
| 600 pts      | ~60 us      | ~4.7 cap/s   | ~0.03%   | 25 MSa/s    | Fast events |
| 1200 pts     | ~120 us     | ~4.6 cap/s   | ~0.06%   | 25 MSa/s    | Balanced |
| **3000 pts** | **~300 us** | **~4.6 cap/s** | **~0.14%** | **25 MSa/s** | **Recommended default** |
| 6000 pts     | ~600 us     | ~4.6 cap/s   | ~0.28%   | 25 MSa/s    | Longer waveforms |
| 12000 pts    | ~1.2 ms     | ~4.5 cap/s   | ~0.54%   | 25 MSa/s    | Full switching events |
| 24000 pts    | ~2.4 ms     | ~4.3 cap/s   | ~1.03%   | 25 MSa/s    | Maximum detail |

**Key Findings:**
- **Capture rate remains ~4.5-4.7 cap/s** regardless of memory depth (USB transfer is the bottleneck)
- **Coverage increases linearly** with memory depth
- **Sample rate auto-adjusts** based on timebase (not memory depth)
- **3000 points is recommended** - good balance between waveform detail and system performance

### Timebase Settings Impact

The timebase setting determines how much time each capture spans:

**Example with 3000 points:**
- 500ns/div → 15us per capture (250 MSa/s sample rate)
- 10us/div → 300us per capture (25 MSa/s sample rate) ← Current default
- 100us/div → 3ms per capture (2.5 MSa/s sample rate)

**Recommendation:** Use longer timebase (10us+) to capture full switching waveforms without needing excessive memory depth.

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

## Multi-Scope 16-Channel Capture

### live_16ch_multiscope_enhanced.py

Advanced real-time capture system for up to 4 oscilloscopes (16 channels total):

**Features:**
- 4-column layout optimized for 16-channel display
  - Column 0: Timeline plots (all 16 channels stacked)
  - Column 1: Detail waveforms (last 10 captures overlaid per channel)
  - Column 2: Voltage distribution histograms (per scope)
  - Column 3: Stats panel (capture rate, coverage, errors)
- JSON configuration files for reproducible test setups
- Individual CSV logging per oscilloscope with UTC timestamps
- Real-time coverage calculation showing temporal sampling percentage
- Screenshot auto-save on exit

**Usage:**
```bash
cd oscilloscope/scripts
python live_16ch_multiscope_enhanced.py ../configs/LT_RAD_TESTCONFIG.json
```

**Configuration:**
See `configs/LT_RAD_TESTCONFIG.json` for example config with:
- Capture settings (points, timebase, display options)
- Per-scope trigger configuration
- Per-channel settings (scale, offset, probe attenuation, custom names)
- Output paths for CSV and screenshots

**Layout Preview:**
Test the visual layout without hardware:
```bash
python layout_preview.py
```

### Coverage Calculation Fix (2025-10-15)

**Problem:**
The coverage percentage was showing incorrect values (e.g., 45% when actual coverage was ~4%). Visual inspection of detail waveforms confirmed low actual coverage despite high reported values.

**Root Cause:**
The formula incorrectly used `timebase_seconds / 10` to calculate time per waveform:
```python
# INCORRECT
time_per_waveform = points_per_channel * (timebase_seconds / 10)
```

This is wrong because:
- `timebase_seconds` is the oscilloscope display setting (seconds per division)
- The actual sample interval is `x_increment` from the waveform preamble
- `x_increment` depends on the oscilloscope's actual sample rate, not the timebase setting

**Solution:**
Use the actual `x_increment` value from captured waveform data:
```python
# CORRECT
actual_time_increment = last_waveforms[scope_idx][-1]['time_increment']
time_per_waveform = points_per_channel * actual_time_increment
```

**Example Calculation:**
- Points per capture: 60,000
- x_increment: 0.2 µs (from oscilloscope preamble)
- Time per waveform: 60,000 × 0.2 µs = 12,000 µs = 12 ms
- Capture rate: 3.6 cap/s
- Coverage: (12 ms × 3.6) / 1000 ms = 4.3% ✓

**Files Modified:**
- `live_16ch_multiscope_enhanced.py` (lines 725-735, 814-823)

This fix ensures accurate coverage reporting for all multi-scope capture sessions.

## Known Issues

1. **Timeout errors**: Occur after 2-5 captures in continuous mode
   - Workaround: Increase delays between captures

2. **RAW mode not working**: Deep memory transfers timeout
   - May need NI-VISA drivers
   - Alternative: Use screen buffer captures

3. **Fast timebase issues**: Very fast timebases (< 200μs/div) cause more timeouts
   - Workaround: Use slower timebases

4. **Low temporal coverage in multi-scope capture**: Even with 60,000 points, coverage is typically 4-5%
   - Root cause: USB transfer time (~270ms per capture) limits capture rate to ~3.6 cap/s
   - Each 60k-point waveform only captures ~12ms of signal
   - This is a hardware limitation of USB transfer bandwidth
   - Workaround: Adjust timebase to match expected event frequency

## Troubleshooting - Hardware Connection Issues

### Problem: Oscilloscopes not detected by PyVISA (No VISA resources found)

**Symptoms:**
- Oscilloscopes appear in Windows Device Manager as "DS1000Z Series" devices
- Device Manager shows them under "Universal Serial Bus devices"
- PyVISA `list_resources()` returns empty or only shows serial ports (ASRL)
- Error: "No backend available" or "VI_ERROR_RSRC_NFOUND"

**Root Cause:**
Windows assigns a generic "USBDevice" driver instead of the USB Test and Measurement Class (USBTMC) driver that PyVISA needs. Without USBTMC drivers, VISA cannot see the oscilloscopes even though they're physically connected.

**Solution - Replug USB Connection:**

The simplest solution that often works:

1. **Unplug the USB cable** from your computer
2. **Wait 5 seconds**
3. **Plug it back in**
4. **Check Device Manager**: Look under "Universal Serial Bus devices" for "DS1000Z Series"
5. **Test detection**: Run `python detect_scopes.py` from the `scripts/` directory

**Why this works:**
- Forces Windows to re-enumerate the USB device
- Triggers driver re-initialization
- Clears any USB hub enumeration issues (especially with multiple scopes)

**For Multiple Oscilloscopes via USB Hub:**
- If connecting 4+ oscilloscopes through a USB hub, ensure the hub is powered
- Unplug/replug the hub connection to the computer (not individual scopes)
- Wait for all devices to enumerate before testing (check Device Manager)
- You should see 4x "DS1000Z Series" devices listed

**Verification Commands:**

Check if oscilloscopes are detected:
```bash
cd oscilloscope/scripts
python detect_scopes.py
```

Expected output when working:
```
USB Oscilloscopes found: 4
Scope 1: USB0::6833::1230::DS1ZA273M00260::0::INSTR
  Identity: RIGOL TECHNOLOGIES,DS1054Z,DS1ZA273M00260,00.04.05.SP2
  Status: OK - Connected successfully
...
```

Check via PyUSB (low-level USB access):
```bash
python -c "import usb.core; import usb.backend.libusb1; backend = usb.backend.libusb1.get_backend(find_library=lambda x: r'C:\Users\andre\Claude\oscilloscope\lib\libusb-1.0.dll'); devices = list(usb.core.find(find_all=True, idVendor=0x1AB1, backend=backend)); print(f'Found {len(devices)} Rigol devices')"
```

**Alternative Solutions (if replug doesn't work):**

1. **Install NI-VISA**: National Instruments VISA includes proper USBTMC drivers
   - Download from ni.com/visa
   - Installs system-wide USBTMC support
   - May require switching PyVISA backend

2. **Use Zadig** (for WinUSB/libusb drivers):
   - Download Zadig from zadig.akeo.ie
   - Select the DS1000Z device
   - Install WinUSB or libusb-win32 driver
   - **Warning**: This replaces the existing driver - may affect other software

3. **Check USB Hub Power**:
   - Each DS1054Z can draw significant USB power
   - Use a powered USB hub for multiple oscilloscopes
   - Try connecting scopes one at a time to isolate power issues

**Device Manager Indicators:**

Good (working):
- "DS1000Z Series" appears under "Universal Serial Bus devices"
- Status shows "OK" or "Unknown" (Unknown can still work)
- Device has a serial number in Instance ID (e.g., DS1ZA273M00260)

Bad (not working):
- Device shows as "Unknown Device" with exclamation mark
- Shows under "Other devices" instead of USB devices
- Missing or generic serial number

**Historical Note:**
This USB detection issue has occurred multiple times during development, especially when:
- Connecting multiple oscilloscopes via USB hub
- After system sleep/wake cycles
- When switching between different USB ports
- After Windows updates

The "unplug and replug" solution has consistently resolved the issue without requiring driver reinstallation or complex troubleshooting.

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
