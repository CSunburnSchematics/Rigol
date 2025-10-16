import sys
from NICE_POWER_SPPS_D8001_232 import NicePowerSupply

VOLTAGE_LIMIT = 5

if __name__ == "__main__":
    # Get COM port and voltage from command line (both required)
    # Usage: python set_nice_power_supply.py COM5 1.5 [slave_addr]
    com_port = sys.argv[1]
    voltage = float(sys.argv[2])
    slave_addr = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    psu = NicePowerSupply(port=com_port, slave_addr=slave_addr, baudrate=9600, parity="N")

    if not psu.inst:
        print("No power supply found")
        sys.exit(1)

    # Set to remote mode
    psu.set_remote(True)

    # Set current limit to 0.1A (100mA)
    psu.set_current_limit(0.1)

    # Safety check: voltage over limit
    if voltage > VOLTAGE_LIMIT:
        print(f"ERROR: Voltage {voltage}V exceeds {VOLTAGE_LIMIT}V limit!")
        psu.set_voltage(0)
        psu.turn_off()
        psu.close()
        raise ValueError(f"Voltage {voltage}V exceeds {VOLTAGE_LIMIT}V safety limit")

    # If 0V, set to 0 and turn off
    if voltage == 0:
        psu.set_voltage(0)
        psu.turn_off()
        print(f"Nice Power supply on {com_port} (addr {slave_addr}) set to 0V and turned OFF")
    else:
        # Set voltage and turn on
        psu.set_voltage(voltage)
        psu.turn_on()
        print(f"Nice Power supply on {com_port} (addr {slave_addr}) set to {voltage}V and turned ON")

    psu.close()
