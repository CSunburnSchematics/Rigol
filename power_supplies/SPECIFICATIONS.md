# Power Supply Specifications

## Rigol DP832A Triple-Output Power Supply

**Connection:** USB via PyVISA (auto-detected by serial number: DP8B261601128)

**Channel Specifications:**
- **CH1**: 0-32V @ 0-3.2A
- **CH2**: 0-32V @ 0-3.2A
- **CH3**: 0-5.3V @ 0-3.2A

**Settling Time:** ~1 second after voltage change

## NICE Power Supplies

**Connection:** RS-232 serial via CP210x USB-to-serial adapter

**All models use the same D2001 custom ASCII protocol** (not modbus)

### Model Specifications:

| Model | Voltage Range | Current Range | COM Port (current) |
|-------|---------------|---------------|---------------------|
| D2001 (SPPS_D2001_232) | 0-200V | 0-1.1A | COM15 |
| D6001 (SPPS_D6001_232) | 0-600V | 0-1.1A | COM10 |
| D8001 (SPPS_D8001_232) | 0-800V | 0-1.1A | COM7 |

**Settling Time:** ~1 second after voltage change

**Important:** COM port assignments change after:
- Device power cycles
- USB cable reconnections
- System reboots
- Windows updates
- Adding/removing other USB devices

Always verify COM ports using `Rigol/identify_devices_manual.py` before use.

## Controller Script Settings

The power supply controller automatically implements:
- **1.0 second settling delay** after setting voltage (both Rigol and NICE)
- Voltage limit enforcement for NICE supplies
- Automatic power-off on script exit
- Status readback verification after configuration

## Configuration File Format

See `Master_Radiation_Test/config/` for example configs.

Each config includes:
- Rigol channel settings (voltage, current, enabled/disabled)
- NICE supply default voltages and currents
- Specifications section for reference
- Notes and COM port remapping instructions
