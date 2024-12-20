import pyvisa
import time

#RIGOL DL3021A
class RigolLoad:
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
            print("Load connection closed.")
        else:
            print("load instrument is not initialized")

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
    
    def turn_on(self):
        if self.instrument:
            self.instrument.write(":INPUT ON")
        else:
            print("load instrument not initialized")

    def turn_off(self):
        if self.instrument:
            print("Turining load input off")
            self.instrument.write(":INPUT OFF")
        else:
            print("load instrument not initialized")

    def set_current_mode(self):
        if self.instrument:
            self.instrument.write(":FUNC CURR")
        else:
            print("load instrument not initialized")

    def set_current(self, current: float):
        if self.instrument:
            self.instrument.write(f":CURR {current:.3f}")
            print(f"Set load current to {current:.3f}")
        else:
            print("load instrument not initialized")

    def set_current_range(self, current_range: float):
        if self.instrument:
            self.instrument.write(":INPUT OFF")
            self.instrument.write(f":CURR:RANG {current_range}")
            print(f"current range set to {current_range} A")
            self.instrument.write("INPUT ON")
        else:
            print("load instrument not initialized")

    
    def read_voltage(self) -> float:
        if self.instrument:
            print("reading voltage on load")
            voltage = float(self.instrument.query(":MEAS:VOLT?"))
            return voltage
        else:
            print("load instrument not initialized")

        
    def read_power(self)-> float:
        if self.instrument:
            print("reading power on load")
            power = float(self.instrument.query(":MEAS:POW?"))
            return power
        else:
            print("load instrument not initialized")

    def read_resistance(self)-> float:
        if self.instrument:
            print("reading resistance on load")
            resistance = float(self.instrument.query(":MEAS:RES?"))
            return resistance
        else:
            print("load instrument not initialized")

    def read_current(self)-> float:
        if self.instrument:
            print("reading current on load")
            current = float(self.instrument.query(":MEAS:CURR?"))
            return current
        else:
            print("load instrument not initialized")

    def reset(self):
        if self.instrument:
            print("Resetting Rigol DL302A current to zero")
            self.set_current_mode()
            self.set_current(0)
        else:
            print("load instrument not initialized")
