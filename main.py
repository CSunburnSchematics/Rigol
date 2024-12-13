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
OSCILLOSCOPE_1_ADDRESS = "USB0::0x1AB1::0x04CE::DS1ZA269M00375::INSTR"
OSCILLOSCOPE_2_ADDRESS = "USB0::0x1AB1::0x04CE::DS1ZA172215665::INSTR"
LOAD_ADDRESS = "USB0::0x1AB1::0x0E11::DL3B262800287::INSTR"
POWER_SUPPLY_ADDRESS = "USB0::0x1AB1::0x0E11::DP8B261601128::INSTR"

# Function to create a unique folder for each test
def create_test_folder(test_setup_name):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"test_{test_setup_name}_{timestamp}"
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

def oscilloscope_trigger_single(oscilloscope_address):
    oscilloscope = rm.open_resource(oscilloscope_address)
    oscilloscope.write(":SINGle")

def oscilloscope_trigger_run(oscilloscope_address):
    oscilloscope = rm.open_resource(oscilloscope_address)
    oscilloscope.write(":RUN")

# Function to capture oscilloscope screenshot
def capture_screenshot_oscilloscope(oscilloscope_adress, filename, format="PNG"):
    try:
        oscilloscope = rm.open_resource(oscilloscope_adress)
        oscilloscope.timeout = 2000  # Set a long timeout for large binary data transfer
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
    voltage_list, current_list, dwell_time, input_current_limit, test_folder
):
    try:
        oscilloscope_1 = rm.open_resource(OSCILLOSCOPE_1_ADDRESS)
        oscilloscope_2 = rm.open_resource(OSCILLOSCOPE_2_ADDRESS)
        load = rm.open_resource(LOAD_ADDRESS)
        power_supply = rm.open_resource(POWER_SUPPLY_ADDRESS)

        # Configure the DL3021A electronic load
        load.write(":INPUT ON")
        load.write(":FUNC CURR")  # Set to current mode

        # Turn on the power supply
        print("Turning on the power supply output...")
        power_supply.write(":OUTP ON")  # Enable output

        for voltage in voltage_list:
            print(f"Starting tests for voltage: {voltage:.2f} V")
            
            # Set power supply to the specified voltage
            set_power_supply_voltage_current(power_supply, voltage, input_current_limit)



            # Create a new CSV file for this voltage
            csv_filename = os.path.join(test_folder, f"test_results_{voltage:.2f}V.csv")
            with open(csv_filename, mode="w", newline="") as csv_file:
                writer = csv.writer(csv_file)

                # Write the CSV header based on voltage
                if voltage <= 30:
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
                    # Adjust current range on the load
                    if current > 4:
                        load.write(":INPUT OFF")
                        load.write(":CURR:RANG 40")
                        print("Set current range to 40 A")
                    else:
                        load.write(":INPUT OFF")
                        load.write(":CURR:RANG 4")
                        print("Set current range to 4 A")

                    print(f"Setting load current to {current:.3f} A")
                    load.write(f":CURR {current:.3f}")
                    load.write(":INPUT ON")
                    time.sleep(dwell_time/2)
                    #trigger oscilloscope "single"
                    oscilloscope_trigger_single(OSCILLOSCOPE_1_ADDRESS)
                    print("switching oscilloscope 1 to single")
                    oscilloscope_trigger_single(OSCILLOSCOPE_2_ADDRESS)
                    print("switching oscilloscope 2 to single")
                    time.sleep(dwell_time/2)
                    # Read measurements from the load
                    load_voltage = float(load.query(":MEAS:VOLT?"))
                    load_power = float(load.query(":MEAS:POW?"))
                    load_resistance = float(load.query(":MEAS:RES?"))
                    load_measured_current = float(load.query(":MEAS:CURR?"))

                    if voltage <= 30:
                        # Single-channel setup
                        ps_voltage, ps_current, ps_power = read_power_supply_channel(power_supply, 1)

                        # Calculate efficiency
                        efficiency = (load_power / ps_power) if ps_power > 0 else 0.0

                        # Write the data to the CSV
                        writer.writerow([
                            f"{load_measured_current:.3f}", f"{load_voltage:.3f}", f"{load_power:.3f}", f"{load_resistance:.3f}",
                            f"{ps_voltage:.3f}", f"{ps_current:.3f}", f"{ps_power:.3f}", f"{efficiency:.3f}"
                        ])
                    else:
                        # Dual-channel setup
                        ch1_voltage, ch1_current, ch1_power = read_power_supply_channel(power_supply, 1)
                        ch2_voltage, ch2_current, ch2_power = read_power_supply_channel(power_supply, 2)

                        # Calculate total input power and efficiency
                        total_input_power = ch1_power + ch2_power
                        efficiency = (load_power / total_input_power) if total_input_power > 0 else 0.0

                        # Write the data to the CSV
                        writer.writerow([
                            f"{load_measured_current:.3f}", f"{load_voltage:.3f}", f"{load_power:.3f}", f"{load_resistance:.3f}",
                            f"{ch1_voltage:.3f}", f"{ch1_current:.3f}", f"{ch1_power:.3f}",
                            f"{ch2_voltage:.3f}", f"{ch2_current:.3f}", f"{ch2_power:.3f}",
                            f"{total_input_power:.3f}", f"{efficiency:.3f}"
                        ])

                    # Capture oscilloscope screenshots
                    osc1_filename = os.path.join(
                        test_folder, f"oscilloscope1_{voltage:.2f}V_{current:.2f}A.png"
                    )
                    osc2_filename = os.path.join(
                        test_folder, f"oscilloscope2_{voltage:.2f}V_{current:.2f}.png"
                    )
                    capture_screenshot_oscilloscope(OSCILLOSCOPE_1_ADDRESS, osc1_filename)
                    capture_screenshot_oscilloscope(OSCILLOSCOPE_2_ADDRESS, osc2_filename)
                    oscilloscope_trigger_run(OSCILLOSCOPE_1_ADDRESS)
                    print("Switching osciloscope 1 to run mode")
                    oscilloscope_trigger_run(OSCILLOSCOPE_2_ADDRESS)
                    print("Switching osciloscope 2 to run mode")

        # Turn off load and power supply after the tests
        load.write(":INPUT OFF")
        load.write(":CURR:RANG 4")  # Reset to default current range
        power_supply.write(":OUTP CH1,OFF")
        power_supply.write(":OUTP CH2,OFF")
        print("Tests completed. Power supply turned off.")

    except Exception as e:
        print(f"Error during tests: {e}")
    finally:
        oscilloscope_1.close()
        oscilloscope_2.close()
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
    parser.add_argument("--test_setup_name", type=str, required=True, help = "Test set up name")
    parser.add_argument(
        "--voltage_list",
        type=parse_float_list, 
        required=True, 
        help="Input voltage list (V)")
    parser.add_argument("--dwell_time", type=float, required=True, help="Time between current changes (s)")
    parser.add_argument("--input_current_limit", type=float, required=True, help="Input current limit (A)")
    parser.add_argument("--test_folder", type=str, required=True, help="Folder to save test results")
    args = parser.parse_args()

    # Debugging: Print the parsed current_list
    print(f"Parsed current_list: {args.current_list}")

    oscilloscope_1_connected = check_connection(OSCILLOSCOPE_1_ADDRESS)
    oscilloscope_2_connected = check_connection(OSCILLOSCOPE_2_ADDRESS)
    load_connected = check_connection(LOAD_ADDRESS)
    power_supply_connected = check_connection(POWER_SUPPLY_ADDRESS)

    if oscilloscope_1_connected and load_connected and power_supply_connected and oscilloscope_2_connected:
        print("Ready to perform test")
        ramp_current_and_capture_with_power_supply(
            args.voltage_list,
            args.current_list, 
            args.dwell_time, 
            args.input_current_limit,
            args.test_folder
        )
    else:
        print("One or more instruments failed to connect")
