import shutil
import pyvisa
import datetime
import time
import csv
import os
import argparse
import subprocess



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
def set_power_supply_voltage_current(power_supply, voltage, current):
    try:
        print(f"Setting power supply voltage to {voltage:.2f} V and current to {current:.2f} A")
        power_supply.write(f":SOUR:VOLT {voltage:.2f}")  # Set voltage
        power_supply.write(f":SOUR:CURR {current:.2f}")  # Set current
    except Exception as e:
        print(f"Failed to set power supply: {e}")

# Function to read voltage, current, and power from the power supply
def read_power_supply_voltage_current_power(power_supply):
    try:
        voltage = float(power_supply.query(":MEAS?"))
        current = float(power_supply.query(":MEAS:CURR?"))
        power = float(power_supply.query(":MEAS:POWE?"))
        return voltage, current, power
    except Exception as e:
        print(f"Failed to read power supply measurements: {e}")
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
    min_current, max_current, step_size, dwell_time, input_voltage, input_current_limit, test_folder):
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
            writer.writerow(["Current (A)", "Voltage (V)", "Power (W)", "Resistance (Ohms)",
                             "Input Voltage (V)", "Input Current (A)", "Input Power (W)", "Efficiency (%)"])

            # Loop through current steps
            current = min_current
            while current <= max_current:
                print(f"Setting load current to {current:.3f} A")
                load.write(f":CURR {current:.3f}")  # Set the current
                load.write(":INPUT ON")  # Turn on the load
                time.sleep(dwell_time)  # Wait for the dwell time

                # Read measurements from the load
                load_voltage = float(load.query(":MEAS:VOLT?"))
                load_power = float(load.query(":MEAS:POW?"))
                load_resistance = float(load.query(":MEAS:RES?"))

                # Read settings from the power supply
                ps_voltage, ps_current, ps_power = read_power_supply_voltage_current_power(power_supply)

                # Calculate power efficiency
                power_efficiency = (load_power / ps_power) if ps_power > 0 else 0.0

                # Capture screenshot of oscilloscope
                screenshot_filename = os.path.join(test_folder, f"oscilloscope_reading_at_{current:.3f}A_load.png")
                capture_screenshot_oscilloscope(screenshot_filename, "PNG")

               

                # Log data to CSV
                writer.writerow([current, load_voltage, load_power, load_resistance,
                                 ps_voltage, ps_current, ps_power, power_efficiency])

                # Increment current
                current += step_size

        # Turn off the load and power supply after the test
        load.write(":INPUT OFF")
        power_supply.write(":OUTP OFF")  # Turn off the power supply output

    except Exception as e:
        print(f"Error: {e}")

    finally:
        oscilloscope.close()
        load.close()
        power_supply.close()

    # Copy screenshots to assets folder
    copy_screenshots_to_assets(test_folder)


# Main script logic
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Oscilloscope Test Script")
    parser.add_argument("--min_current", type=float, required=True, help="Minimum current (A)")
    parser.add_argument("--max_current", type=float, required=True, help="Maximum current (A)")
    parser.add_argument("--step_size", type=float, required=True, help="Step size (A)")
    parser.add_argument("--dwell_time", type=int, required=True, help="Dwell time at each step (s)")
    parser.add_argument("--input_voltage", type=float, required=True, help="Input voltage (V)")
    parser.add_argument("--input_current_limit", type=float, required=True, help="Input current limit (A)")
    parser.add_argument("--test_folder", type=str, required=True, help="Folder to save test results")
    args = parser.parse_args()

    oscilloscope_connected = check_connection(OSCILLOSCOPE_ADDRESS)
    load_connected = check_connection(LOAD_ADDRESS)
    power_supply_connected = check_connection(POWER_SUPPLY_ADDRESS)

    if oscilloscope_connected and load_connected and power_supply_connected:
        print("Ready to perform test")
        ramp_current_and_capture_with_power_supply(args.min_current, args.max_current, args.step_size,
                                                   args.dwell_time, args.input_voltage, args.input_current_limit,
                                                   args.test_folder)
    else:
        print("One or more instruments failed to connect")
