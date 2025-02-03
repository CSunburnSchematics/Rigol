import pyvisa
#test
class RigolFunctionGenerator:
    def __init__(self, address):
        """Initialize the connection to the Rigol DG1022Z."""
        self.rm = pyvisa.ResourceManager()
        try:
            self.instrument = self.rm.open_resource(address)
            print(f"Connected to: {self.instrument.query('*IDN?').strip()}")
        except Exception as e:
            print(f"Failed to connect to function generator at {address}: {e}")
            self.instrument = None

    def close(self):
        """Close the connection to the instrument."""
        if self.instrument:
            self.instrument.close()
            print("Function generator connection closed.")

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

    def set_waveform(self, channel: int, waveform: str):
        """
        Set the waveform type on the specified channel.

        :param channel: Channel number (1 or 2).
        :param waveform: Waveform type (e.g., "sine", "square", "ramp", "pulse", "noise").
        """
        # Define a mapping of user-friendly names to Rigol waveform types
        waveform_mapping = {
            "sine": "SINE",
            "square": "SQUARE",
            "ramp": "RAMP",
            "pulse": "PULSE",
            "noise": "NOISE",
            "dc": "DC",
            "user": "USER",
        }

        # Validate the channel
        if channel not in [1, 2]:
            raise ValueError(f"Invalid channel: {channel}. Must be 1 or 2.")

        # Translate waveform to Rigol command
        waveform = waveform.lower()  # Normalize input to lowercase
        if waveform not in waveform_mapping:
            raise ValueError(f"Unsupported waveform type: {waveform}. Supported types are: {list(waveform_mapping.keys())}")

        rigol_waveform = waveform_mapping[waveform]

        # Send command to the instrument
        self.instrument.write(f":SOUR{channel}:FUNC {rigol_waveform}")
        print(f"Set Channel {channel} to {waveform} waveform.")


    def set_frequency(self, channel, frequency):
        """Set the frequency on a specific channel."""
        if self.instrument:
            self.instrument.write(f"SOUR{channel}:FREQ {frequency}")
            print(f"Channel {channel} frequency set to {frequency} Hz.")
        else:
            print("Instrument not initialized.")

    def set_amplitude(self, channel, amplitude):
        """Set the amplitude on a specific channel."""
        if self.instrument:
            self.instrument.write(f"SOUR{channel}:VOLT {amplitude}")
            print(f"Channel {channel} amplitude set to {amplitude} V.")
        else:
            print("Instrument not initialized.")

    def set_offset(self, channel, offset):
        """Set the DC offset on a specific channel."""
        if self.instrument:
            self.instrument.write(f"SOUR{channel}:VOLT:OFFS {offset}")
            print(f"Channel {channel} offset set to {offset} V.")
        else:
            print("Instrument not initialized.")

    def enable_output(self, channel):
        """Enable output on a specific channel."""
        if self.instrument:
            self.instrument.write(f"OUTP{channel} ON")
            print(f"Channel {channel} output turned ON.")
        else:
            print("Instrument not initialized.")

    def disable_output(self, channel):
        """Disable output on a specific channel."""
        if self.instrument:
            self.instrument.write(f"OUTP{channel} OFF")
            print(f"Channel {channel} output turned OFF.")
        else:
            print("Instrument not initialized.")


    def configure_sweep(self, start_freq, stop_freq, time, channel=1, sweep_type="LIN"):
        """Configure a frequency sweep on a specific channel."""
        if self.instrument:
            self.instrument.write(f"SOUR{channel}:FREQ:STAR {start_freq}")
            self.instrument.write(f"SOUR{channel}:FREQ:STOP {stop_freq}")
            self.instrument.write(f"SOUR{channel}:SWE:TIME {time}")
            self.instrument.write(f"SOUR{channel}:SWE:SPAC {sweep_type}")
            self.instrument.write(f"SOUR{channel}:SWE:STAT ON")
            print(f"Channel {channel} sweep configured from {start_freq} Hz to {stop_freq} Hz in {time} s with {sweep_type} spacing.")
        else:
            print("Instrument not initialized.")

    def trigger_sweep(self, channel=1):
        """Trigger the frequency sweep."""
        if self.instrument:
            self.instrument.write(f"SOUR{channel}:SWE:TRIG")
            print(f"Channel {channel} sweep triggered.")
        else:
            print("Instrument not initialized.")

    def reset(self):
        """Reset the function generator."""
        if self.instrument:
            self.instrument.write("*RST")
            print("Function generator reset to default settings.")
        else:
            print("Instrument not initialized.")

    def set_dc_offset(self, channel: int, offset: float):
        """
        Set the DC offset for the specified channel.

        :param channel: Channel number (1 or 2).
        :param offset: DC offset in volts.
        """
        # Validate the channel
        if channel not in [1, 2]:
            raise ValueError(f"Invalid channel: {channel}. Must be 1 or 2.")

        # Send the command to set DC offset
        self.instrument.write(f":SOUR{channel}:VOLT:OFFS {offset}")
        print(f"Set Channel {channel} DC Offset to {offset} V.")

    def set_phase(self, channel: int, phase: float):
        """
        Set the phase for the specified channel.

        :param channel: Channel number (1 or 2).
        :param phase: Phase in degrees (0 to 360).
        """
        # Validate the channel
        if channel not in [1, 2]:
            raise ValueError(f"Invalid channel: {channel}. Must be 1 or 2.")

        # Validate the phase range
        if not (0 <= phase <= 360):
            raise ValueError(f"Invalid phase: {phase}. Must be between 0 and 360 degrees.")

        # Send the command to set phase
        self.instrument.write(f":SOUR{channel}:PHAS {phase}")
        print(f"Set Channel {channel} Phase to {phase} degrees.")

    def set_up_sweep(self, waveform, amplitude, offset, phase, channel):
        self.set_waveform(channel, waveform)
        self.set_amplitude(channel, amplitude)
        self.set_offset(channel, offset)
        self.set_phase(channel, phase)
        print("Sweep parameters set up")
    


# # Example usage
# if __name__ == "__main__":
#     rigol = RigolFunctionGenerator("USB0::0x1AB1::0x0643::DG1022Z::INSTR")
#     if rigol.check_connection():
#         rigol.set_waveform(1, "SIN")
#         rigol.set_frequency(1, 1000)
#         rigol.set_amplitude(1, 1.0)
#         rigol.set_offset(1, 0.0)
#         rigol.configure_sweep(1000, 2000, 5, channel=1)
#         rigol.trigger_sweep(1)
#         rigol.enable_output(1, True)
#     rigol.close()
