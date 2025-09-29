import numpy as np
import pyvisa
import time
import os
import os, csv
import numpy as np
import matplotlib
matplotlib.use("Agg")  # safe even on headless machines; remove if you want a window
import matplotlib.pyplot as plt


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
    

    def system_reboot(self, save_and_restore_setup: bool = True,
                      reconnect_timeout_s: int = 120, probe_interval_s: float = 2.0):
        if not self.instrument:
            raise RuntimeError("Instrument not connected.")
        address = self.instrument.resource_name
        self.instrument.timeout = 10000

        setup_blob = None
        if save_and_restore_setup:
            try:
                setup_blob = bytes(self.instrument.query_binary_values(':SYSTem:SETup?', datatype='B',
                                                                       container=bytearray))
            except Exception as e:
                print(f"[reboot] Warning: could not save setup: {e}")

        try:
            self.instrument.write(':SYSTem:REBoot')
        except Exception as e:
            print(f"[reboot] Note: write error during reboot (likely expected): {e}")
        try:
            self.instrument.close()
        except Exception:
            pass
        self.instrument = None

        deadline = time.time() + reconnect_timeout_s
        last_err = None
        while time.time() < deadline:
            try:
                cand = self.rm.open_resource(address)
                cand.timeout = 10000
                idn = cand.query('*IDN?').strip()
                self.instrument = cand
                print(f"[reboot] Reconnected: {idn}")
                break
            except Exception as e:
                last_err = e
                time.sleep(probe_interval_s)

        if self.instrument is None:
            raise TimeoutError(f"Could not reconnect within {reconnect_timeout_s}s. Last error: {last_err}")

        if save_and_restore_setup and setup_blob:
            try:
                self.instrument.write_binary_values(':SYSTem:SETup ', list(setup_blob), datatype='B')
                time.sleep(0.5)
            except Exception as e:
                print(f"[reboot] Warning: failed to restore setup: {e}")

        return self.instrument.query('*IDN?').strip()
    

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
    



## CHECK

    def capture_window_on_demand(scope,
                                channel=1,
                                window_s=500e-6,
                                memory_depth=1200000,
                                fmt="BYTE",
                                timeout_s=8.0):
        """
        One-shot capture of the current window. Returns (time_s, volts, preamble_dict).

        - Forces AUTO sweep and HOLD=0 so the shot completes immediately (no real-edge wait).
        - Arms :SINGle, waits for STOP/TD, reads RAW data in chunks, returns arrays.
        """
        inst = scope.instrument
        if inst is None:
            raise RuntimeError("Instrument not connected.")
        if not (1 <= channel <= 4):
            raise ValueError("Channel must be 1..4.")

        # Ensure we're not running
        inst.write(":STOP")

        # Timebase for requested total window (screen = 12 divisions)
        inst.write(f":TIM:SCAL {window_s/12:g}")
        inst.write(":TIM:OFFS 0")

        # Memory depth
        if isinstance(memory_depth, str) and memory_depth.upper() == "AUTO":
            inst.write(":ACQ:MDEP AUTO")
        else:
            inst.write(f":ACQ:MDEP {int(memory_depth)}")

        # Make sure source channel is on
        inst.write(f":CHAN{channel}:DISP ON")

        # Force a single capture without waiting for an edge
        inst.write(":TRIG:SWEEP AUTO")
        inst.write(":TRIG:HOLD 0")

        # Arm single-shot and wait for completion
        inst.write(":SINGle")
        t0 = time.time()
        while True:
            stat = inst.query(":TRIG:STAT?").strip().upper()
            if "STOP" in stat or "TD" in stat:
                break
            if time.time() - t0 > timeout_s:
                raise TimeoutError(f"Single-shot did not complete in time (status={stat}).")
            time.sleep(0.02)

        # Read RAW waveform (full record)
        inst.write(f":WAV:SOUR CHAN{channel}")
        inst.write(":WAV:MODE RAW")
        inst.write(f":WAV:FORM {fmt}")    # BYTE fastest; WORD = 16-bit codes

        pre = inst.query(":WAV:PRE?").strip().split(",")
        npts = int(float(pre[2]))
        xinc, xorg, xref = float(pre[4]), float(pre[5]), float(pre[6])
        yinc, yorg, yref = float(pre[7]), float(pre[8]), float(pre[9])

        if npts <= 0:
            raise RuntimeError("Scope returned 0 points; try increasing memory_depth or check window.")

        max_per = 250000 if fmt.upper() == "BYTE" else 125000
        data = bytearray()
        start = 1
        while start <= npts:
            stop = min(start + max_per - 1, npts)
            inst.write(f":WAV:STAR {start}")
            inst.write(f":WAV:STOP {stop}")
            chunk = inst.query_binary_values(":WAV:DATA?", datatype='B', container=bytearray)
            data += chunk
            start = stop + 1

        # Convert to arrays
        if fmt.upper() == "BYTE":
            codes = np.frombuffer(bytes(data), dtype=np.uint8)
        else:
            codes = np.frombuffer(bytes(data), dtype=np.uint16)

        volts = (codes.astype(np.float64) - yorg - yref) * yinc
        time_s = xorg + (np.arange(npts, dtype=np.float64) - xref) * xinc

        preamble = {
            "points": npts, "xinc": xinc, "xorig": xorg, "xref": xref,
            "yinc": yinc, "yorig": yorg, "yref": yref
        }
        return time_s, volts, preamble


