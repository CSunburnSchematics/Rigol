import sys
from Rigol_DP832A import RigolPowerSupply

VOLTAGE_LIMIT = 5

if __name__ == "__main__":
    # Get address and voltage from command line (both required)
    psu_address = sys.argv[1]
    voltage = float(sys.argv[2])

    psu = RigolPowerSupply(psu_address)

    if not psu:
        print("No power supply found")
        sys.exit(1)

    i = psu.instrument
    i.write(":INST:SEL CH3")

    # Set current limit to 0.001A (1mA)
    i.write(":SOUR3:CURR 0.001")

    # Safety check: voltage over 10V
    if voltage > VOLTAGE_LIMIT:
        print(f"ERROR: Voltage {voltage}V exceeds 10V limit!")
        i.write(":SOUR3:VOLT 0")
        i.write(":OUTP OFF")
        raise ValueError(f"Voltage {voltage}V exceeds 10V safety limit")

    # If 0V, set to 0 and turn off
    if voltage == 0:
        i.write(":SOUR3:VOLT 0")
        i.write(":OUTP OFF")
        print("Power supply CH3 set to 0V and turned OFF")
    else:
        # Set voltage and turn on
        i.write(f":SOUR3:VOLT {voltage}")
        i.write(":OUTP ON")
        print(f"Power supply CH3 set to {voltage}V and turned ON")
