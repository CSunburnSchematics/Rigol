import sys
from Rigol_DP832A import RigolPowerSupply

VOLTAGE_LIMIT = 5

if __name__ == "__main__":
    # Get address and voltage from command line (both required)
    psu_address = sys.argv[1]
    voltage = float(sys.argv[2])

    psu = RigolPowerSupply(psu_address)

    if not psu.instrument:
        print("No power supply found")
        sys.exit(1)

    # Set current limit to 0.001A (1mA)
    psu.set_current_limit(3, 0.1)

    # Safety check: voltage over limit
    if voltage > VOLTAGE_LIMIT:
        print(f"ERROR: Voltage {voltage}V exceeds {VOLTAGE_LIMIT}V limit!")
        psu.set_voltage(3, 0)
        psu.turn_channel_off(3)
        raise ValueError(f"Voltage {voltage}V exceeds {VOLTAGE_LIMIT}V safety limit")

    # If 0V, set to 0 and turn off
    if voltage == 0:
        psu.set_voltage(3, 0)
        psu.turn_channel_off(3)
        print("Power supply CH3 set to 0V and turned OFF")
    else:
        # Set voltage and turn on
        psu.set_voltage(3, voltage)
        psu.turn_channel_on(3)
        print(f"Power supply CH3 set to {voltage}V and turned ON")
