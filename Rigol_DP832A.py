import pyvisa
import time

#RIGOL DP832A
class RigolPowerSupply:
    def __init__(self, address):
        """Initialize the power supply connection."""
        self.rm = pyvisa.ResourceManager()
        try:
            self.instrument = self.rm.open_resource(address)
            print(f"Connected to: {self.instrument.query('*IDN?').strip()}")
        except Exception as e:
            print(f"Failed to connect to power supply at {address}: {e}")
            self.instrument = None

    def close(self):
        """Close the connection to the instrument."""
        if self.instrument:
            self.instrument.close()
            print("Power Supply connection closed.")

    def check_connection(self):
        """Check if the instrument is still connected and responding."""
        if self.instrument:
            try:
                response = self.instrument.query("*IDN?")
                print(f"Connection active: {response.strip()}")
                return True
            except Exception as e:
                print(f"Connection check failed: {e}")
                return False
        return False

    def turn_on(self):
        """Turn on all outputs."""
        if self.instrument:
            self.instrument.write(":OUTP CH1,ON")
            self.instrument.write(":OUTP CH2,ON")
        else:
            print("Instrument not initialized")

    def turn_off(self):
        """Turn off all outputs."""
        if self.instrument:
            self.instrument.write(":OUTP CH1,OFF")
            self.instrument.write(":OUTP CH2,OFF")
        else:
            print("Instrument not initialized")

    def select_channel(self, channel: int):
        """Select a specific channel."""
        if self.instrument:
            self.instrument.write(f":INSTrument:SELect CH{channel}")
            print(f"Channel {channel} selected.")
        else:
            print("Instrument not initialized.")

    def turn_channel_on(self, channel: int):
        """Turn a specific channel on."""
        if self.instrument:
            self.select_channel(channel)
            self.instrument.write(":OUTPut ON")
            print(f"Channel {channel} is now ON and selected.")
        else:
            print("Instrument not initialized.")

    def turn_channel_off(self, channel: int):
        """Turn a specific channel off."""
        if self.instrument:
            self.select_channel(channel)
            self.instrument.write(":OUTPut OFF")
            print(f"Channel {channel} is now OFF.")
        else:
            print("Instrument not initialized.")

    def set_voltage(self, channel: int, voltage: float):
        """Set the voltage for a specific channel."""
        if self.instrument:
            self.select_channel(channel)
            self.instrument.write(f":SOUR:VOLT {voltage:.2f}")
            print(f"Voltage set to {voltage:.2f}V on Channel {channel}.")
        else:
            print("Instrument not initialized.")

    def set_current_limit(self, channel: int, current: float):
        """Set the current limit for a specific channel."""
        if self.instrument:
            self.select_channel(channel)
            self.instrument.write(f":SOUR:CURR {current:.2f}")
            print(f"Current limit set to {current:.2f}A on Channel {channel}.")
        else:
            print("Instrument not initialized.")

    def measure_voltage(self, channel: int) -> float:
        """Measure the voltage on a specific channel."""
        if self.instrument:
            self.select_channel(channel)
            voltage = float(self.instrument.query(":MEAS:VOLT?"))
            print(f"Measured voltage on Channel {channel}: {voltage}V")
            return voltage
        else:
            print("Instrument not initialized.")
        return None

    def measure_current(self, channel: int) -> float:
        """Measure the current on a specific channel."""
        if self.instrument:
            self.select_channel(channel)
            current = float(self.instrument.query(":MEAS:CURR?"))
            print(f"Measured current on Channel {channel}: {current}A")
            return current
        else:
            print("Instrument not initialized.")
        return None

    def measure_power(self, channel: int) -> float:
        """Measure the power on a specific channel."""
        if self.instrument:
            self.select_channel(channel)
            power = float(self.instrument.query(":MEAS:POWE?"))
            print(f"Measured power on Channel {channel}: {power}W")
            return power
        else:
            print("Instrument not initialized.")
        return None

    def reset(self):
        if self.instrument:
            self.set_voltage(1, 0)
            self.set_voltage(2, 0)
            self.set_voltage(3, 0)
            print("Resetting Riol DP832A voltage to zero on channel 1, 2, and 3")
        else:
            print("Instrument not initialized.")
    # Function to set voltage and current on the power supply
    def configure_voltage_current(self, voltage, current, max_retries=3):
        try:
            # Check if the voltage is above the limit
            if voltage > 64:
                print("Error: Setting voltage above 64V is not supported. Program will terminate.")
                return  # Stop the execution of the function

            def verify_and_retry(channel, expected_voltage):
                for attempt in range(max_retries):

                    # Read back settings
                    actual_voltage = float(self.measure_voltage(channel))

                    if abs(actual_voltage - expected_voltage) < 0.1:
                        print(f"Channel {channel} settings verified: Voltage={actual_voltage:.2f} V")
                        return True
                    else:
                        print(f"Retry {attempt + 1}: Adjusting settings for Channel {channel}")
                        self.set_voltage(channel, expected_voltage)
                        time.sleep(1)
                    

                print(f"Failed to set Channel {channel} settings after {max_retries} attempts.")
                return False
            
            if 64 < voltage <= 90:
                voltage_1 = 30
                voltage_2 = 30
                voltage_3 = voltage - 60

                self.turn_channel_on(1)
                time.sleep(1)
                self.set_voltage(1, voltage_1)
                time.sleep(1)
                self.set_current_limit(1, current)
                time.sleep(1)
                self.turn_channel_on(2)
                time.sleep(1)
                self.set_voltage(2, voltage_2)
                time.sleep(1)
                self.set_current_limit(2, current)
                time.sleep(1)
                self.turn_channel_on(3)
                time.sleep(1)
                self.set_voltage(3, voltage_3)
                time.sleep(1)
                self.set_current_limit(3, current)
                print(f"Setting power supply voltage to {voltage:.2f} V (split: {voltage_1:.2f} V on CH1, {voltage_2:.2f} V on CH2, {voltage_3:.2f} V on CH3) and current to {current:.2f} A")

                # Set and verify CH1
                if not verify_and_retry(1, voltage_1):
                    raise ValueError("Failed to properly set Channel 1.")

                # Set and verify CH2
                if not verify_and_retry(2, voltage_2):
                    raise ValueError("Failed to properly set Channel 2.")
                
                # Set and verify CH3
                if not verify_and_retry(3, voltage_3):
                    raise ValueError("Failed to properly set Channel 3.")


            # Voltage between 30 and 64 (split across channels)
            elif 30 < voltage <= 64:
                voltage_1 = 32
                voltage_2 = voltage - 32

                self.turn_channel_on(1)
                time.sleep(1)
                self.set_voltage(1, voltage_1)
                time.sleep(1)
                self.set_current_limit(1, current)
                time.sleep(1)
                self.turn_channel_on(2)
                time.sleep(1)
                self.set_voltage(2, voltage_2)
                time.sleep(1)
                self.set_current_limit(2, current)

                print(f"Setting power supply voltage to {voltage:.2f} V (split: {voltage_1:.2f} V on CH1, {voltage_2:.2f} V on CH2) and current to {current:.2f} A")

                # Set and verify CH1
                if not verify_and_retry(1, voltage_1):
                    raise ValueError("Failed to properly set Channel 1.")

                # Set and verify CH2
                if not verify_and_retry(2, voltage_2):
                    raise ValueError("Failed to properly set Channel 2.")

            # Voltage up to 30 (single channel)
            elif voltage <= 30:

                print(f"Setting power supply voltage to {voltage:.2f} V and current to {current:.2f} A on CH1")

                self.turn_on()
                time.sleep(1)
                self.turn_channel_on(1)
                time.sleep(1)
                self.set_voltage(1, voltage)
                time.sleep(1)
                self.set_current_limit(1, current)
                time.sleep(1)
                self.set_voltage(2, 0.0)

                self.turn_channel_off(2) #verify channel 2 is off
                self.turn_channel_off(3) #verify channel 3 is off

                if not verify_and_retry(1, voltage):
                    raise ValueError("Failed to properly set Channel 1.")

        except Exception as e:
            print(f"Failed to set power supply: {e}")
            raise

    # Function to read voltage, current, and power from the power supply
    def read_power_supply_channel(self, channel):
        try:

            voltage = self.measure_voltage(channel)
            time.sleep(0.1)
            current = self.measure_current(channel)
            time.sleep(0.1)
            power = self.measure_power(channel)

            return voltage, current, power
        except Exception as e:
            print(f"Failed to read power supply measurements for CH{channel}: {e}")
            return None, None, None