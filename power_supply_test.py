import pyvisa
from Korad_KA3305P import KoradPowerSupply
from Rigol_DP832A import RigolPowerSupply
def main():
    rm = pyvisa.ResourceManager()
    RIGOL_POWER_SUPPLY_ADDRESS = "USB0::0x1AB1::0x0E11::DP8B261601128::INSTR"


    power_supply = RigolPowerSupply(RIGOL_POWER_SUPPLY_ADDRESS)
    try:
       
        power_supply = RigolPowerSupply(RIGOL_POWER_SUPPLY_ADDRESS)
  

        if not power_supply.check_connection():
            raise ConnectionError(f"Power {power_supply} supply failed to connect.")
    except Exception as e:
            print(f"Error initializing power supply: {e}")
   

    # power_supply = KoradPowerSupply(port="COM6")

    # # Check if the power supply is connected and responsive
    # if power_supply.check_connection():
    #     print("Power supply is connected successfully.")

    #     # Example commands
    #     channel = 1  # Specify the channel you want to control
    #     voltage = 5.0  # Voltage in Volts
    #     current_limit = 1.0  # Current limit in Amperes

    #     # Turn on the channel
    #     power_supply.turn_channel_on(channel)

    #     # Set voltage and current limit
    #     power_supply.set_voltage(channel, voltage)
    #     power_supply.set_current_limit(channel, current_limit)

    #     # Measure voltage, current, and power
    #     measured_voltage = power_supply.measure_voltage(channel)
    #     measured_current = power_supply.measure_current(channel)
    #     measured_power = power_supply.measure_power(channel)

    #     print(f"Channel {channel} - Voltage: {measured_voltage} V, Current: {measured_current} A, Power: {measured_power} W")

    #     # Turn off the channel
    #     power_supply.turn_channel_off(channel)

    # else:
    #     print("Failed to connect to the power supply.")

    # # Close the connection
    # power_supply.close()


if __name__ == "__main__":
    main()