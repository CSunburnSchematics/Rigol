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
    
    def capture_screenshot(self, filename, format = "PNG"):
        try:
            self.instrument.write(f":DISP:DATA? ON,OFF,{format}")
            raw_data = self.instrument.read_raw()

            # Parse the TMC block header
            header_length = int(raw_data[1:2])  # The second character indicates the header length
            image_data = raw_data[2 + header_length:]  # Remove the header

            # Save the image
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, "wb") as file:
                file.write(image_data)
            print(f"Screenshot saved as {filename}")


        except Exception as e:
            print(f"Error capturing screenshot: {e}")

        finally:

            #in original function the instrument is closed
            #self.instrument.close()
            pass

    def trigger_run(self):
        self.instrument.write(":RUN")
        

    def trigger_single(self):
        self.instrument.write(":SINGle")
        

    