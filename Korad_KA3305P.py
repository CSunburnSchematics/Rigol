import serial
import time


class KoradPowerSupply:
    def __init__(self, port, baudrate=9600, timeout=0.5):
        """
        Initialize the power supply communication via COM port.
        
        :param port: The COM port (e.g., 'COM6').
        :param baudrate: The baud rate for communication (default: 9600).
        :param timeout: Timeout for serial communication (default: 1 second).
        """
        try:
            self.connection = serial.Serial(port, baudrate=baudrate, timeout=timeout)
            time.sleep(2)  # Allow the connection to stabilize
            print(f"Connected to Korad Power Supply on {port}.")
        except Exception as e:
            print(f"Failed to connect to power supply on {port}: {e}")
            self.connection = None

    def close(self):
        """Close the communication with the power supply."""
        if self.connection and self.connection.is_open:
            self.connection.close()
            print("Connection closed.")

    def send_command(self, command):
        """
        Send a command to the power supply.

        :param command: The command string to send.
        """
        if self.connection and self.connection.is_open:
            full_command = command + "\r\n"  # Add newline as per protocol
            self.connection.write(full_command.encode())
            print(f"Sent command: {command}")
        else:
            print("Connection is not open. Cannot send command.")

    def read_response(self):
        """
        Read a response from the power supply.

        :return: The response string.
        """
        if self.connection and self.connection.is_open:
            response = self.connection.readline() #.decode().strip()
            # print(f"Raw response: {response}")  # Print raw bytes
            decoded_response = response.decode(errors="ignore").strip()
            print(f"Decoded response: {decoded_response}")
            return decoded_response
            #print(f"Received response: {response}")
            #return response
        print("Connection is not open. Cannot read response.")
        return None

    def check_connection(self):
        """Check if the power supply is responding."""
        self.send_command("*IDN?")
        response = self.read_response()
        if response:
            print(f"Power supply identity: {response}")
            return True
        return False

    def turn_on(self):
        """Turn on all outputs."""
        self.send_command(f"OUT1")

    def turn_off(self):
        """Turn off all outputs."""
        self.set_voltage(1, 0)
        self.set_voltage(2, 0)
        self.send_command(f"OUT0")

    def turn_channel_on(self, channel):
        """Turn a specific channel on."""
        self.send_command(f"OUT{channel}:ON")

    def turn_channel_off(self, channel):
        """Turn a specific channel off."""
        self.set_voltage(channel, 0)
        self.send_command(f"OUT{channel}:OFF")

    def set_voltage(self, channel, voltage):
        """Set the voltage for a specific channel."""
        self.send_command(f"VSET{channel}:{voltage:.2f}")

    def set_current_limit(self, channel, current):
        """Set the current limit for a specific channel."""
        self.send_command(f"ISET{channel}:{current:.2f}")

    def measure_voltage(self, channel):
        retries = 3
        delay = 0.1
        for attempt in range(1, retries + 1):
                try:
                    print(f"Attempt {attempt}: Measuring voltage on Channel {channel}...")
                    self.send_command(f"VOUT{channel}?")
                    response = self.read_response()
                    if response:  # Ensure response is not None or empty
                        voltage = float(response)
                        print(f"Voltage on Channel {channel}: {voltage} V")
                        return voltage
                    else:
                        print(f"Attempt {attempt}: No valid response for voltage.")
                except Exception as e:
                    print(f"Error on attempt {attempt} to measure voltage: {e}")
                time.sleep(delay)  # Wait before retrying
        print(f"Failed to measure voltage on Channel {channel} after {retries} attempts.")
        return None

    def reset(self):
        print("Resetting Korad KA3305P voltage to zero on channel 1 and 2")
        self.set_voltage(1,0)
        self.set_voltage(2,0)

    def measure_current(self, channel):
            retries = 3
            delay = 0.1
 
            for attempt in range(1, retries + 1):
                try:
                    print(f"Attempt {attempt}: Measuring current on Channel {channel}...")
                    self.send_command(f"IOUT{channel}?")
                    response = self.read_response()
                    if response:  # Ensure response is not None or empty
                        current = float(response)
                        print(f"Current on Channel {channel}: {current} A")
                        return current
                    else:
                        print(f"Attempt {attempt}: No valid response for current.")
                except Exception as e:
                    print(f"Error on attempt {attempt} to measure current: {e}")
                time.sleep(delay)  # Wait before retrying
            print(f"Failed to measure current on Channel {channel} after {retries} attempts.")
            return None

    def measure_power(self, channel):
        """Measure the power on a specific channel."""
        voltage = self.measure_voltage(channel)
        current = self.measure_current(channel)
        power = voltage * current
        print(f"Measured power on Channel {channel}: {power:.2f}W")
        return power
    
    # Function to set voltage and current on the power supply
    def configure_voltage_current(self, voltage, current, max_retries=3):
        try:
            # Check if the voltage is above the limit
            if voltage > 60:
                print("Error: Setting voltage above 60V is not supported. Program will terminate.")
                return  # Stop the execution of the function

            def verify_and_retry(channel, expected_voltage):
                for attempt in range(max_retries):
                    # Select channel
                    
                    time.sleep(1)

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

            # Voltage between 30 and 60 (split across channels)
            if 30 < voltage <= 60:
                voltage_1 = 30
                voltage_2 = voltage - 30

                self.turn_on
                time.sleep(1)
                self.set_voltage(1, voltage_1)
                time.sleep(1)
                self.set_current_limit(1, current)
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
                self.set_voltage(1, voltage)
                time.sleep(1)
                self.set_current_limit(1, current)
                time.sleep(1)
                self.set_voltage(2, 0.0)



                if not verify_and_retry(1, voltage):
                    raise ValueError("Failed to properly set Channel 1.")

        except Exception as e:
            print(f"Failed to set power supply: {e}")
            raise



