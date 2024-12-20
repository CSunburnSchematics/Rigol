import shutil
import pyvisa
import datetime
import time
import csv
import os
import argparse





# Initialize PyVISA Resource Manager
rm = pyvisa.ResourceManager()

# Instrument addresses
OSCILLOSCOPE_ADDRESS = "USB0::0x1AB1::0x04CE::DS1ZA269M00375::INSTR"
LOAD_ADDRESS = "USB0::0x1AB1::0x0E11::DL3B262800287::INSTR"
POWER_SUPPLY_ADDRESS = "USB0::0x1AB1::0x0E11::DP8B261601128::INSTR"

# Function to create a unique folder for each test
def create_test_folder(min_current, max_current, step_size):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"test_min_{min_current}_max_{max_current}_step_{step_size}_{timestamp}"
    os.makedirs(folder_name, exist_ok=True)
    return folder_name

# Check connection function
def check_connection(address): 
    """Check if the instrument is connected and responding."""
    try:
        instrument = rm.open_resource(address)
        instrument.query("*IDN?")  # Send an identification query
        print(f"Connected to: {instrument.query('*IDN?').strip()}")
        instrument.close()
        return True
    except Exception as e:
        print(f"Connection failed for {address}: {e}")
        return False


# Function to set voltage and current on the power supply
def set_power_supply_voltage_current(power_supply, voltage, current, max_retries=3):
    try:
        # Check if the voltage is above the limit
        if voltage > 60:
            print("Error: Setting voltage above 60V is not supported. Program will terminate.")
            return  # Stop the execution of the function

        def verify_and_retry(channel, expected_voltage):
            for attempt in range(max_retries):
                # Select channel

                power_supply.write(f":INSTrument:SELect CH{channel}")
                time.sleep(1)

                # Read back settings
                actual_voltage = float(power_supply.query(":MEAS:VOLT?"))
                

                if abs(actual_voltage - expected_voltage) < 0.1:
                    print(f"Channel {channel} settings verified: Voltage={actual_voltage:.2f} V")
                    return True
                else:
                    print(f"Retry {attempt + 1}: Adjusting settings for Channel {channel}")
                    power_supply.write(f":SOUR:VOLT {expected_voltage:.2f}")
                    time.sleep(1)
                   

            print(f"Failed to set Channel {channel} settings after {max_retries} attempts.")
            return False

        # Voltage between 30 and 60 (split across channels)
        if 30 < voltage <= 60:
            voltage_1 = 30
            voltage_2 = voltage - 30

            power_supply.write(f":INSTrument:SELect CH1")
            time.sleep(1)
            power_supply.write(":OUTPut ON")
            time.sleep
            power_supply.write(f":SOUR:VOLT {voltage_1:.2f}")
            time.sleep(1)
            power_supply.write(f":SOUR:CURR {current:.2f}")
            time.sleep(1)
            power_supply.write(f":INSTrument:SELect CH2")
            time.sleep(1)
            power_supply.write(":OUTPut ON")
            time.sleep(1)
            power_supply.write(f":SOUR:VOLT {voltage_2:.2f}")
            time.sleep(1)
            power_supply.write(f":SOUR:CURR {current:.2f}")

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

            power_supply.write(f":INSTrument:SELect CH1")
            time.sleep(1)
            power_supply.write(f":SOUR:VOLT {voltage:.2f}")
            time.sleep(1)
            power_supply.write(f":SOUR:CURR {current:.2f}")
            time.sleep(1)
            power_supply.write(":OUTP CH2,OFF") #verify channel 2 is off!

            if not verify_and_retry(1, voltage):
                raise ValueError("Failed to properly set Channel 1.")

    except Exception as e:
        print(f"Failed to set power supply: {e}")
        raise


# Function to read voltage, current, and power from the power supply
def read_power_supply_channel(power_supply, channel):
    try:
        power_supply.write(f":INSTrument:SELect CH{channel}")
        voltage = float(power_supply.query(":MEAS:VOLT?"))
        current = float(power_supply.query(":MEAS:CURR?"))
        power = float(power_supply.query(":MEAS:POWE?"))
        return voltage, current, power
    except Exception as e:
        print(f"Failed to read power supply measurements for CH{channel}: {e}")
        return None, None, None

# Function to capture oscilloscope screenshot
def capture_screenshot_oscilloscope(filename, format="PNG"):
    try:
        oscilloscope = rm.open_resource(OSCILLOSCOPE_ADDRESS)
        oscilloscope.timeout = 15000  # Set a long timeout for large binary data transfer
        time.sleep(1)
        print(f"Capturing screenshot in {format} format...")
        oscilloscope.write(f":DISP:DATA? ON,OFF,{format}")
        raw_data = oscilloscope.read_raw()  # Read the raw binary data

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
        oscilloscope.close()

# Function to copy screenshots to the assets folder
def copy_screenshots_to_assets(test_folder):
    assets_folder = os.path.join(os.getcwd(), "assets")
    os.makedirs(assets_folder, exist_ok=True)
    
    for file in os.listdir(test_folder):
        if file.endswith(".png") or file.endswith(".jpg"):
            shutil.copy(os.path.join(test_folder, file), os.path.join(assets_folder, file))
    print(f"Screenshots copied to assets folder.")

# Main test function
def ramp_current_and_capture_with_power_supply(
    current_list, dwell_time, input_voltage, input_current_limit, test_folder):
    try:
        oscilloscope = rm.open_resource(OSCILLOSCOPE_ADDRESS)
        load = rm.open_resource(LOAD_ADDRESS)
        power_supply = rm.open_resource(POWER_SUPPLY_ADDRESS)

        # Configure the DL3021A electronic load
        load.write(":FUNC CURR")  # Set to current mode

        # Turn on the power supply
        print("Turning on the power supply output...")
        power_supply.write(":OUTP ON")  # Enable output

        # Configure the DP800 power supply
        set_power_supply_voltage_current(power_supply, input_voltage, input_current_limit)

        # Prepare CSV file
        csv_filename = os.path.join(test_folder, "test_results.csv")
        with open(csv_filename, mode="w", newline="") as csv_file:
            writer = csv.writer(csv_file)

            # Determine the header based on channel usage
            if input_voltage <= 30:
                writer.writerow([
                    "Current (A)", "Load Voltage (V)", "Load Power (W)", "Load Resistance (Ohms)",
                    "Input Voltage (V)", "Input Current (A)", "Input Power (W)", "Efficiency (%)"
                ])
            else:
                writer.writerow([
                    "Current (A)", "Load Voltage (V)", "Load Power (W)", "Load Resistance (Ohms)",
                    "CH1 Voltage (V)", "CH1 Current (A)", "CH1 Power (W)",
                    "CH2 Voltage (V)", "CH2 Current (A)", "CH2 Power (W)", "Total Input Power (W)", "Efficiency (%)"
                ])

            # Iterate through the current list
            for current in current_list:
                print(f"Setting load current to {current:.3f} A")
                
                # Set the current on the load
                load.write(f":CURR {current:.3f}")  # Set the current
                load.write(":INPUT ON")  # Turn on the load
                time.sleep(dwell_time)  # Wait for the dwell time

                # Read measurements from the load
                load_voltage = float(load.query(":MEAS:VOLT?"))
                load_power = float(load.query(":MEAS:POW?"))
                load_resistance = float(load.query(":MEAS:RES?"))

                if input_voltage <= 30:
                    # Single-channel setup
                    ps_voltage, ps_current, ps_power = read_power_supply_channel(power_supply, 1)

                    # Calculate efficiency
                    power_efficiency = (load_power / ps_power) if ps_power > 0 else 0.0

                    # Log data to CSV
                    writer.writerow([
                        f"{current:.2f}", f"{load_voltage:.2f}", f"{load_power:.2f}", f"{load_resistance:.2f}",
                        f"{ps_voltage:.2f}", f"{ps_current:.2f}", f"{ps_power:.2f}", f"{power_efficiency:.2f}"
                    ])
                else:
                    # Dual-channel setup
                    ch1_voltage, ch1_current, ch1_power = read_power_supply_channel(power_supply, 1)
                    ch2_voltage, ch2_current, ch2_power = read_power_supply_channel(power_supply, 2)

                    # Calculate total input power and efficiency
                    total_input_power = ch1_power + ch2_power
                    power_efficiency = (load_power / total_input_power) if total_input_power > 0 else 0.0

                    # Log data to CSV
                    writer.writerow([
                        f"{current:.2f}", f"{load_voltage:.2f}", f"{load_power:.2f}", f"{load_resistance:.2f}",
                        f"{ch1_voltage:.2f}", f"{ch1_current:.2f}", f"{ch1_power:.2f}",
                        f"{ch2_voltage:.2f}", f"{ch2_current:.2f}", f"{ch2_power:.2f}",
                        f"{total_input_power:.2f}", f"{power_efficiency:.2f}"
                    ])

                # Capture oscilloscope screenshot
                screenshot_filename = os.path.join(test_folder, f"oscilloscope_reading_{current:.2f}A_load.png")
                capture_screenshot_oscilloscope(screenshot_filename, format="PNG")

        # Turn off the load and power supply after the test
        load.write(":INPUT OFF")
        power_supply.write(":OUTP CH1,OFF")  # Turn off the power supply output
        print("Turn off power supply channel 1")
        if input_voltage > 30:
            power_supply.write(":OUTP CH2,OFF")
            print("Turn off power supply channel 2")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        oscilloscope.close()
        load.close()
        power_supply.close()

    # Copy screenshots to assets folder
    copy_screenshots_to_assets(test_folder)




def parse_float_list(value):
    """
    Parses a comma-separated string into a list of floats.
    Example: "1.0,2.5,3.3" -> [1.0, 2.5, 3.3]
    """
    try:
        # Remove brackets if passed, e.g., "[1.0,2.5,3.3]"
        value = value.strip("[]")
        return [float(x.strip()) for x in value.split(',')]
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid format for --current_list. Provide a comma-separated list of floats.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Oscilloscope Test Script")
    parser.add_argument(
        "--current_list", 
        type=parse_float_list, 
        required=True, 
        help="List of current values to test (comma-separated, e.g., '1.0,2.5,3.3')"
    )
    parser.add_argument("--step_size", type=float, required=True, help="Step size (A)")
    parser.add_argument("--input_voltage", type=float, required=True, help="Input voltage (V)")
    parser.add_argument("--dwell_time", type=float, required=True, help="Time between current changes (s)")
    parser.add_argument("--input_current_limit", type=float, required=True, help="Input current limit (A)")
    parser.add_argument("--test_folder", type=str, required=True, help="Folder to save test results")
    args = parser.parse_args()

    # Debugging: Print the parsed current_list
    print(f"Parsed current_list: {args.current_list}")

    oscilloscope_connected = check_connection(OSCILLOSCOPE_ADDRESS)
    load_connected = check_connection(LOAD_ADDRESS)
    power_supply_connected = check_connection(POWER_SUPPLY_ADDRESS)

    if oscilloscope_connected and load_connected and power_supply_connected:
        print("Ready to perform test")
        ramp_current_and_capture_with_power_supply(
            args.current_list, 
            args.dwell_time, 
            args.input_voltage, 
            args.input_current_limit,
            args.test_folder
        )
    else:
        print("One or more instruments failed to connect")
