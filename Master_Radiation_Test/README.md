# Master Radiation Test

Automated radiation testing system that coordinates thermal cameras, power supplies, and oscilloscopes for comprehensive device testing.

## Quick Start

### LTC Rad Test (Low Voltage)
```bash
python "C:\Users\Sunburn\Sunburn code\Master_Radiation_Test\scripts\launch_radiation_test.py" config/POWER_SUPPLY_ltc_rad_test_board_config.json config/SCOPE_LT_RAD_TESTCONFIG.json No
```

### GAN HV Test (High Voltage - 40% VDS)
```bash
python "C:\Users\Sunburn\Sunburn code\Master_Radiation_Test\scripts\launch_radiation_test.py" config/POWER_SUPPLY_GAN_40percentVDS_rad_test_board_config.json config/SCOPE_LT_RAD_GAN_rad_test_board_config.json No
```

## System Components

The launcher script orchestrates three subsystems:

1. **Thermal Camera** (optional) - UTI thermal imaging and recording
2. **Power Supply Monitor** - Rigol DP832A and NICE high-voltage supplies
3. **Oscilloscope** - 16-channel multi-scope data acquisition

## Output Structure

Each test run creates a timestamped folder:
```
Master_Radiation_Test/
  radiation_test_YYYYMMDD_HHMMSS/
    ├── thermal_YYYYMMDD_HHMMSS/          # Thermal camera data
    ├── power_supply_recording_YYYYMMDD_HHMMSS/  # Power data + manifest
    └── scope_capture_YYYYMMDD_HHMMSS/     # Oscilloscope data + manifest
```

## Configuration Files

### Power Supply Configs
- `POWER_SUPPLY_ltc_rad_test_board_config.json` - Low voltage test (Rigol only)
- `POWER_SUPPLY_GAN_40percentVDS_rad_test_board_config.json` - High voltage GAN test

### Oscilloscope Configs
- `SCOPE_LT_RAD_TESTCONFIG.json` - Low voltage scope settings
- `SCOPE_LT_RAD_GAN_rad_test_board_config.json` - High voltage GAN scope settings
- `SCOPE_LT_RAD_ltc_rad_test_board_config.json` - Alternative LTC config

## CRITICAL: NICE Power Supply Current Limit Issue

**IMPORTANT:** The NICE high-voltage power supplies (D2001, D6001, D8001) can get stuck at low output voltage (~1-2V) if their current limit is set too low when commanding high voltages.

### Symptoms
- Power supply commanded to high voltage (e.g., 320V) but only outputs 1-2V
- No error messages or warnings
- Supply appears to be working normally

### Root Cause
When the current limit is too restrictive (e.g., 0.1A) and a high voltage is commanded, the supply's internal protection limits the output voltage. This behavior is not documented in the manual.

### Solution
Set the current limit to at least **1.0A** for high voltage operations (>100V):

```json
"D8001": {
  "default_voltage": 320,
  "default_current": 1.0,    // Use 1.0A, not 0.1A!
  ...
}
```

### Safe Current Limits by Voltage Range
- **0-50V**: 0.1A minimum
- **50-200V**: 0.5A minimum
- **200-800V**: 1.0A minimum

**Note:** These are minimum current limits to prevent voltage sag. Actual load current will be determined by the DUT. The power supply will current-limit if the load tries to draw more than the configured value.

## Shutdown Behavior

Press **'Q'** in the launcher window to gracefully stop all systems:
- Each subsystem receives shutdown signal
- Systems save data and create manifests (30-60 seconds)
- Launcher waits up to 60 seconds for graceful shutdown
- After timeout, processes are forcefully terminated

**Note:** If processes end naturally (e.g., error or completion), the launcher auto-exits without the shutdown wait period.

## Thermal Camera

To skip the thermal camera (faster startup):
```bash
python launch_radiation_test.py <power_config> <scope_config> No
```

Valid skip arguments: `No`, `n`, `none`, `skip`

## COM Port Remapping

NICE power supplies may change COM ports after power cycles. Before testing:

1. Run port verification:
   ```bash
   cd "C:\Users\Sunburn\Sunburn code\Power_Supplies\scripts"
   python verify_and_remap_nice_power.py
   ```

2. Update COM ports in config files if needed

## Troubleshooting

### Power Supply Not Reaching Target Voltage
- Check current limit is adequate (see NICE Power Supply section above)
- Verify COM ports are correct
- Check power supply is powered on and not in fault mode

### Oscilloscope Not Triggering
- Verify trigger level matches expected signal range
- Check probe attenuation settings (typically 100x for high voltage)
- Ensure channels are enabled in config

### Launcher Crashes Subsystems
- Ensure all config files have valid JSON syntax
- Check file paths are absolute or relative to Master_Radiation_Test/
- Verify all required scripts exist in their respective directories

### JSON Syntax Errors
- Numbers must have leading zero: `0.5` not `.5`
- All strings must be quoted
- No trailing commas in arrays or objects

## Data Analysis

Each subsystem creates a manifest file documenting:
- Configuration used
- Test start/end times
- System information
- File locations

Look for:
- `power_supply_manifest.txt` - Power supply recording details
- `scope_manifest.txt` - Oscilloscope capture details
