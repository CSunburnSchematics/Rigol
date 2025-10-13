import sys
from NICE_POWER_SPPS_D2001_232 import NicePowerSupply

VOLTAGE_LIMIT = 5

if __name__ == "__main__":
    # Get COM port and voltage from command line (both required)
    # Usage: python set_nice_power_supply_d2001.py COM6 1.5 [device_addr]
    com_port = sys.argv[1]
    voltage = float(sys.argv[2])
    device_addr = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    psu = NicePowerSupply(port=com_port, device_addr=device_addr, baudrate=9600, timeout=1)

    if not psu.serial:
        print("No power supply found")
        sys.exit(1)

    # Set to remote mode
    psu.set_remote(True)

    # Set current limit to 0.1A (100mA)
    psu.set_current_limit(0.1)

    # Safety check: voltage over limit
    if voltage > VOLTAGE_LIMIT:
        psu.set_voltage(0)  # This also disables remote and turns off
        psu.close()
        raise ValueError(f"Voltage {voltage}V exceeds {VOLTAGE_LIMIT}V safety limit")

    # If 0V, set to 0 (automatically turns off and disables remote)
    if voltage == 0:
        psu.set_voltage(0)
        print(f"Nice Power supply (D2001) on {com_port} (addr {device_addr}) set to 0V and turned OFF")
    else:
        # Set voltage and turn on
        psu.set_voltage(voltage)
        psu.turn_on()
        print(f"Nice Power supply (D2001) on {com_port} (addr {device_addr}) set to {voltage}V and turned ON")

    psu.close()
