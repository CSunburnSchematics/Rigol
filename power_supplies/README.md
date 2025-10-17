# NICE Power Supply Controller

Centralized control system for NICE Power supplies (D2001, D6001, D8001) used in radiation testing.

## Directory Structure

```
Power_Supplies/
├── scripts/
│   └── nice_power_controller.py    # Main controller script
└── README.md                        # This file

Master_Radiation_Test/
└── config/
    └── nice_power_config.json       # Power supply configuration
```

## Quick Start

### Basic Usage

```python
from nice_power_controller import NICEPowerController

# Create controller (auto-loads config)
controller = NICEPowerController()

# Connect to all supplies
controller.connect_all()

# Get status
controller.get_all_status()

# Set voltage on specific supply
controller.set_voltage('D6001', 50.0, current=0.2)

# Turn off all
controller.turn_off_all()

# Close connections
controller.close_all()
```

### Run from Command Line

```bash
cd "C:\Users\Sunburn\Sunburn code\Power_Supplies\scripts"
python nice_power_controller.py
```

## Configuration

Edit `Master_Radiation_Test/config/nice_power_config.json` to update:
- COM port assignments
- Default voltages
- Current limits
- Device descriptions

**Example config:**
```json
{
  "power_supplies": {
    "D6001": {
      "com_port": "COM10",
      "model": "SPPS_D6001_232",
      "max_voltage": 600,
      "default_voltage": 6.0,
      "default_current": 0.1,
      "baudrate": 9600,
      "device_addr": 0,
      "description": "600V NICE Power Supply"
    }
  }
}
```

## Important Notes

### Critical Discovery (2025-10-16)

**All NICE Power models (D2001, D6001, D8001) use the same D2001 custom ASCII protocol**, even though some advertise modbus capability. The controller automatically uses the correct protocol for all models.

### COM Port Changes

**WARNING**: COM port assignments are NOT stable and will change after:
- Device power cycles
- USB cable reconnections
- System reboots
- Windows updates
- Adding/removing other USB devices

**Always verify COM ports before use:**
1. Run `Rigol/identify_devices_manual.py` to re-identify devices
2. Update `Master_Radiation_Test/config/nice_power_config.json` with current ports

### Current Device Map (Last Verified: 2025-10-16)

| Device | COM Port | Max Voltage | Model |
|--------|----------|-------------|-------|
| D2001  | COM15    | 200V        | SPPS_D2001_232 |
| D6001  | COM10    | 600V        | SPPS_D6001_232 |
| D8001  | COM7     | 800V        | SPPS_D8001_232 |

## API Reference

### NICEPowerController Class

#### Methods

**`__init__(config_path=None)`**
- Initialize controller with config file
- Default config: `Master_Radiation_Test/config/nice_power_config.json`

**`connect_all()`**
- Connect to all power supplies in config
- Returns: `True` if all connected successfully

**`set_voltage(supply_name, voltage, current=None)`**
- Set voltage and optional current for specific supply
- Args:
  - `supply_name`: 'D2001', 'D6001', or 'D8001'
  - `voltage`: Voltage in volts
  - `current`: Current limit in amps (uses default if None)
- Returns: `(actual_voltage, actual_current)` tuple

**`get_status(supply_name)`**
- Get current voltage and current
- Returns: `(voltage, current)` tuple

**`get_all_status()`**
- Print status of all supplies to console

**`turn_off_all()`**
- Turn off all connected supplies (set voltage to 0)

**`close_all()`**
- Close all serial connections

## Example Scripts

### Set All to Default Voltages

```python
controller = NICEPowerController()
controller.connect_all()

for name in controller.supplies.keys():
    settings = controller.supplies[name]['settings']
    if controller.supplies[name]['connected']:
        controller.set_voltage(name, settings['default_voltage'])

controller.get_all_status()
controller.close_all()
```

### Safe Power-Up Sequence

```python
controller = NICEPowerController()

try:
    controller.connect_all()

    # Ramp up slowly
    for v in [5, 10, 20, 50]:
        controller.set_voltage('D6001', v)
        time.sleep(2)

    controller.get_all_status()

except Exception as e:
    print(f"Error: {e}")
finally:
    controller.turn_off_all()
    controller.close_all()
```

## Dependencies

- Python 3.x
- pyserial
- NICE_POWER_SPPS_D2001_232.py (from Rigol folder)

## Troubleshooting

### "FileNotFoundError: Config file not found"
- Ensure `Master_Radiation_Test/config/nice_power_config.json` exists
- Or specify custom config path: `NICEPowerController(config_path='path/to/config.json')`

### "No response from device"
1. Check USB connections
2. Verify COM port in Device Manager
3. Run `Rigol/identify_devices_manual.py` to remap
4. Update config file with correct ports

### "Connection uncertain - no voltage reading"
- Device may be in error state
- Try power cycling the device
- Check serial cable connections

### "Voltage exceeds max"
- Check that voltage is within device limits:
  - D2001: 0-200V
  - D6001: 0-600V
  - D8001: 0-800V

## Related Files

- `Rigol/NICE_POWER_SPPS_D2001_232.py` - Core driver class
- `Rigol/nice_power_device_map.txt` - Current COM port mapping
- `Rigol/identify_devices_manual.py` - Device identification utility
- `Rigol/CLAUDE.md` - Technical documentation
