import pyvisa
import time
import os

class RigolOscilloscope:
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
            print("Oscilloscope connection closed.")
        else:
            print("instrument is not initialized")

    def check_connection(self )-> bool:
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
    
    def get_vmax(self, channel: int) -> float:
        """
        Query the Vmax for a specified channel.
        :param channel: The channel number (1 to 4).
        :return: The Vmax value as a float, or 0.0 if the instrument reports an invalid value.
        """
        if not (1 <= channel <= 4):
            raise ValueError("Invalid channel number. Must be between 1 and 4.")
        
        command = f"MEASure:VMAX? CHAN{channel}"
        invalid_threshold = 9.9e+37  # Center of invalid range
        margin_of_error = 1e+34  # Allowable margin around the invalid value
        
        try:
            vmax_response = self.instrument.query(command).strip()
            
            # Check for empty, null, or invalid responses
            if not vmax_response or vmax_response.lower() in ['null', 'nan', '']:
                print(f"Null or invalid Vmax response for CHAN{channel}: {vmax_response}")
                return 0.0
            
            # Convert response to float
            vmax_value = float(vmax_response)
            
            # Check if value is within the invalid range (margin of error)
            if abs(vmax_value - invalid_threshold) <= margin_of_error:
                print(f"Invalid measurement (within range of {invalid_threshold} ± {margin_of_error}) for CHAN{channel}")
                return 0.0
            
            return vmax_value
        except ValueError:
            print(f"Invalid float value for Vmax response from CHAN{channel}: {vmax_response}")
            return 0.0
        except Exception as e:
            print(f"Error querying Vmax for CHAN{channel}: {e}")
            raise


    def get_vmin(self, channel: int) -> float:
        """
        Query the Vmin for a specified channel.
        :param channel: The channel number (1 to 4).
        :return: The Vmin value as a float, or 0.0 if the instrument reports an invalid value.
        """
        if not (1 <= channel <= 4):
            raise ValueError("Invalid channel number. Must be between 1 and 4.")
        
        command = f"MEASure:VMIN? CHAN{channel}"
        invalid_threshold = 9.9e+37  # Center of invalid range
        margin_of_error = 1e+34  # Allowable margin around the invalid value
        
        try:
            vmin_response = self.instrument.query(command).strip()
            
            # Check for empty, null, or invalid responses
            if not vmin_response or vmin_response.lower() in ['null', 'nan', '']:
                print(f"Null or invalid Vmin response for CHAN{channel}: {vmin_response}")
                return 0.0
            
            # Convert response to float
            vmin_value = float(vmin_response)
            
            # Check if value is within the invalid range (margin of error)
            if abs(vmin_value - invalid_threshold) <= margin_of_error:
                print(f"Invalid measurement (within range of {invalid_threshold} ± {margin_of_error}) for CHAN{channel}")
                return 0.0
            
            return vmin_value
        except ValueError:
            print(f"Invalid float value for Vmin response from CHAN{channel}: {vmin_response}")
            return 0.0
        except Exception as e:
            print(f"Error querying Vmin for CHAN{channel}: {e}")
            raise



    def capture_screenshot(self, filename, format="PNG"):
        try:
            # Send the screenshot command to the oscilloscope
            self.instrument.write(f":DISP:DATA? ON,OFF,{format}")
            raw_data = self.instrument.read_raw()

            # Parse the TMC block header
            header_length = int(raw_data[1:2])  # The second character indicates the header length
            image_data = raw_data[2 + header_length:]  # Remove the header

            # Ensure the directory exists, if specified
            directory = os.path.dirname(filename)
            if directory:  # Only create directories if the path contains them
                os.makedirs(directory, exist_ok=True)

            # Save the image
            with open(filename, "wb") as file:
                file.write(image_data)
            print(f"Screenshot saved as {filename}")

        except Exception as e:
            print(f"Error capturing screenshot: {e}")

        finally:
            # Keep the connection open
            pass


    def trigger_run(self):
        self.instrument.write(":RUN")
        

   


    def trigger_single(self, max_retries=3, delay_between_retries=.1):
        """
        Trigger oscilloscope for a single acquisition and retry if waveform data is not available.
        :param max_retries: Maximum number of retries for the trigger operation.
        :param delay_between_retries: Delay (in seconds) between retries.
        :return: True if waveform data is available, False otherwise.
        """
        for attempt in range(1, max_retries + 1):
            print(f"Attempt {attempt} of {max_retries}: Sending :SINGle command.")
            try:
                self.instrument.write(":SINGle")
                print("Sent :SINGle command. Checking for waveform data...")

                # Check if waveform data is available
                try:
                    points = int(self.instrument.query(":WAV:POIN?").strip())
                    if points > 0:
                        print(f"Waveform data available: {points} points.")
                        return True
                    else:
                        print("No waveform data available. Retrying...")
                except Exception as e:
                    print(f"Error querying waveform data: {e}")

            except Exception as e:
                print(f"Error during :SINGle trigger on attempt {attempt}: {e}")

            # Optional delay between retries
            if attempt < max_retries:
                time.sleep(delay_between_retries)

        print(f"Failed to capture waveform after {max_retries} attempts.")
        return False

