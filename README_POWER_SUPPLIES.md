# Power Supply Control and Logging

This repository contains scripts for controlling and logging data from Rigol and Nice Power supplies.

## Supported Power Supplies

### Rigol Power Supplies
- **DP832A** (3 channels, USB control via PyVISA)
  - Example: DP8B261601128

### Nice Power Supplies
Two types with different communication protocols:

1. **SPPS-D2001-232** (Custom ASCII protocol over RS232)
   - Single channel
   - Custom protocol: `<FFDDDDDDAAA>` format
   - More reliable, simpler protocol

2. **SPPS-D6001-232 / SPPS-D8001-232** (Modbus RTU over RS232)
   - Single channel
   - Modbus protocol with float registers
   - **Requires special handling** for reliable operation

## Quick Start

### Setting Power Supply Voltages

```bash
# Using default config (12V, 5V, 2.5V on Rigol; 13V on Nice D2001)
python launch_all.py default_config.json

# Using custom config
python launch_all.py your_config.json
```

### Logging Power Supply Data

```bash
# Set voltages and log measurements
python power_supply_logger.py default_config.json
```

This will:
1. Connect to all power supplies
2. Set voltages/currents from config
3. Log measurements to JSON and CSV files in `power_supply_logs/`

## Configuration Files

Power supply configs are in the `Configs/` directory. Example structure:

```json
{
  "power_supplies": {
    "rigol": {
      "DP8B261601128": {
        "channels": {
          "1": { "vout": 12.0, "iout_max": 0.1 },
          "2": { "vout": 5.0, "iout_max": 0.1 },
          "3": { "vout": 2.5, "iout_max": 0.1 }
        }
      }
    },
    "nice_power": {
      "SPPS_D2001_232": {
        "baudrate": 9600,
        "vout": 13.0,
        "iout_max": 0.1
      },
      "SPPS_D6001_232": {
        "com_port": "COM13",
        "baudrate": 9600,
        "vout": 4.0,
        "iout_max": 0.1
      },
      "SPPS_D8001_232": {
        "com_port": "COM14",
        "baudrate": 9600,
        "vout": 7.0,
        "iout_max": 0.1
      }
    }
  }
}
```

## Reliable Operation of Modbus Nice Power Supplies

### The Problem

SPPS-D6001 and SPPS-D8001 supplies use Modbus RTU protocol, which can be **unreliable** over USB-to-serial adapters:
- Commands may not execute properly
- Set values may not match requested values
- Communication timeouts can occur

### The Solution

Claire implemented a robust `configure_voltage_current()` method with:

1. **Verification**: Reads back SET registers (not measured values) to confirm
2. **Retry Logic**: Up to 3 attempts with automatic retries
3. **Tolerance Checking**: Accepts values within 0.2V/0.2A tolerance
4. **Proper Delays**: 20ms delays between operations

### Example Usage

```python
from NICE_POWER_SPPS_D8001_232 import NicePowerSupply

# Connect to Modbus power supply
psu = NicePowerSupply(port="COM14", slave_addr=1, baudrate=9600)

# Reliable configuration with verification
psu.configure_voltage_current(
    voltage=7.0,
    current=0.5,
    verify=True,      # Enable verification
    max_retries=3,    # Retry up to 3 times
    tol=0.2           # Accept ±0.2V/A tolerance
)

# Read measurements
v_meas = psu.measure_voltage()
i_meas = psu.measure_current()
print(f"Measured: {v_meas:.3f}V, {i_meas:.3f}A")

psu.close()
```

### Best Practices

**For SPPS-D6001 / SPPS-D8001 (Modbus):**
1. **Always use** `configure_voltage_current()` instead of individual set commands
2. Enable verification (`verify=True`)
3. Allow retries (`max_retries=3`)
4. Wait 1 second after setting before reading measurements
5. Use tolerance checking to handle small communication errors

**For SPPS-D2001 (ASCII):**
1. Standard `set_voltage()` and `set_current_limit()` work reliably
2. Custom ASCII protocol is more robust
3. Still recommended to wait 0.5-1s after setting

### Scripts Using Reliable Method

Both `launch_all.py` and `power_supply_logger.py` automatically detect Modbus supplies and use the reliable configuration method:

```python
if device_type == "modbus" and hasattr(psu, 'configure_voltage_current'):
    # Use robust configure method with retry logic
    psu.configure_voltage_current(voltage, current, verify=True, max_retries=3, tol=0.2)
else:
    # Fallback for D2001 or older supplies
    psu.set_remote(True)
    psu.set_current_limit(current)
    psu.set_voltage(voltage)
    psu.turn_on()
```

## Troubleshooting

### "Connection check failed: No communication with the instrument"

This is normal for some COM ports that aren't actually power supplies. The scripts automatically skip these.

### Modbus supply shows wrong voltage after setting

1. Check that you're using `configure_voltage_current()` with `verify=True`
2. Increase `max_retries` to 5
3. Check USB cable connection
4. Try closing and reopening the connection

### D2001 supply not detected

1. Verify COM port in Device Manager
2. Ensure baudrate is 9600
3. Check that device address is 0 (default for D2001)

## Log Files

Power supply logger creates two files in `power_supply_logs/`:

1. **JSON log**: Complete timestamped data
   - `power_supply_log_YYYYMMDD_HHMMSS_UTC.json`
   - All measurements with metadata

2. **CSV summary**: Easy to import into Excel/Python
   - `power_supply_summary_YYYYMMDD_HHMMSS_UTC.csv`
   - Columns: timestamp, supply_type, supply_id, channel, voltage_set, current_set, voltage_meas, current_meas, power_meas

## Dependencies

```bash
pip install pyvisa pyvisa-py pyserial minimalmodbus
```

- **pyvisa**: Rigol oscilloscopes and power supplies (USB)
- **pyserial**: Serial communication for Nice Power supplies
- **minimalmodbus**: Modbus RTU protocol for SPPS-D6001/D8001

## See Also

- `README_TESTING.md` - Radiation testing workflow
- `NICE_POWER_SPPS_D2001_232.py` - ASCII protocol implementation
- `NICE_POWER_SPPS_D8001_232.py` - Modbus protocol implementation with robust retry logic
