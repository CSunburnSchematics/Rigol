import json
import shutil
import sys
from typing import Union
import pyvisa
import datetime
import time
import csv
import os
import argparse
from Korad_KA3305P import KoradPowerSupply
from Rigol_DP832A import RigolPowerSupply
from Rigol_DS1054z import RigolOscilloscope
from Rigol_DL3021A import RigolLoad


# Initialize PyVISA Resource Manager
rm = pyvisa.ResourceManager()

# Instrument addresses
OSCILLOSCOPE_1_ADDRESS = "USB0::0x1AB1::0x04CE::DS1ZA269M00375::INSTR"
OSCILLOSCOPE_2_ADDRESS = "USB0::0x1AB1::0x04CE::DS1ZA172215665::INSTR"
OSCILLOSCOPE_3_ADDRESS = "USB0::0x1AB1::0x04CE::DS1ZA192006991::INSTR"
LOAD_ADDRESS = "USB0::0x1AB1::0x0E11::DL3B262800287::INSTR"
RIGOL_POWER_SUPPLY_ADDRESS = "USB0::0x1AB1::0x0E11::DP8B261601128::INSTR"
KORAD_POWER_SUPPLY_COM = "COM6"

# Function to create a unique folder for each test
def create_test_folder(test_setup_name):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"test_{test_setup_name}_{timestamp}"
    os.makedirs(folder_name, exist_ok=True)
    return folder_name


# Function to read voltage, current, and power from the power supply
def read_power_supply_channel(power_supply: Union[RigolPowerSupply, KoradPowerSupply], channel):
    try:

        voltage = power_supply.measure_voltage(channel)
        time.sleep(0.1)
        current = power_supply.measure_current(channel)
        time.sleep(0.1)
        power = voltage*current

   
        return voltage, current, power
    except Exception as e:
        print(f"Failed to read power supply measurements for CH{channel}: {e}")
        return None, None, None



# Function to copy screenshots to the assets folder
def copy_screenshots_to_assets(test_folder):
    assets_folder = os.path.join(os.getcwd(), "assets")
    os.makedirs(assets_folder, exist_ok=True)
    
    for file in os.listdir(test_folder):
        if file.endswith(".png") or file.endswith(".jpg"):
            shutil.copy(os.path.join(test_folder, file), os.path.join(assets_folder, file))
    print(f"Screenshots copied to assets folder.")

def read_oscilloscope_measurements(oscilloscope_1, oscilloscope_2, oscilloscope_3, measurements_list):
    """
    Reads measurements from the oscilloscopes based on the measurement list.
    If "negative" is in the header (case-insensitive), the measurement value is negated.

    :param oscilloscope_1: Oscilloscope 1 instance
    :param oscilloscope_2: Oscilloscope 2 instance
    :param oscilloscope_3: Oscilloscope 3 instance
    :param measurements_list: List of measurement strings (e.g., ["Osc1 CH1 negative Vmax", "Osc2 CH3 Vmin"])
    :return: List of measurement values in the same order as the measurements_list
    """
    results = []

    for measurement in measurements_list:
        # Parse the measurement string
        parts = measurement.split()
        if len(parts) < 3:  # Minimum expected format: "Osc# CH# [negative] MeasurementType"
            results.append(None)
            continue

        # Extract oscilloscope, channel, and measurement type
        osc = parts[0]
        channel = parts[1]
        measurement_type = parts[-1]  # Last part is the measurement type
        is_negative = "negative" in map(str.lower, parts)  # Check if "negative" is in the header

        # Determine which oscilloscope to use
        if osc == "Osc1":
            oscilloscope = oscilloscope_1
        elif osc == "Osc2":
            oscilloscope = oscilloscope_2
        elif osc == "Osc3":
            oscilloscope = oscilloscope_3
        else:
            results.append(None)  # Invalid oscilloscope
            continue

        # Parse channel number
        try:
            channel_num = int(channel.replace("CH_", "").replace("CH", ""))
        except ValueError:
            results.append(None)  # Invalid channel number
            continue

        # Read the measurement based on type
        try:
            if measurement_type == "VMax":
                value = oscilloscope.get_vmax(channel_num)
            elif measurement_type == "VMin":
                value = oscilloscope.get_vmin(channel_num)
            else:
                results.append(None)  # Unsupported measurement type
                continue

            # Apply negation if necessary
            if is_negative:
                value = -value

            results.append(value)
        except Exception as e:
            print(f"Error reading {measurement} on {osc}: {e}")
            results.append(None)  # Handle errors gracefully

    return results


def generate_measurement_strings(osc_1_measurements, osc_2_measurements, osc_3_measurements):
    """
    Generate a list of formatted measurement strings based on oscilloscope channel measurements.
    If 'make_negative' is True, prepend "negative" to the measurement string.

    :param osc_1_measurements: Dictionary of measurements for oscilloscope 1.
    :param osc_2_measurements: Dictionary of measurements for oscilloscope 2.
    :param osc_3_measurements: Dictionary of measurements for oscilloscope 3.
    :return: List of formatted strings for valid measurements.
    """
    measurement_strings = []

    # Helper function to process one oscilloscope
    def process_osc_measurements(osc_measurements, osc_number):
        for channel, measurement_data in osc_measurements.items():
            measurement = measurement_data["measurement"]
            make_negative = measurement_data["make_negative"]

            if measurement != "None":
                # Add "negative" if make_negative is True
                if make_negative:
                    measurement = f"negative {measurement}"

                measurement_strings.append(f"Osc{osc_number} {channel.upper()} {measurement}")

    # Process each oscilloscope
    process_osc_measurements(osc_1_measurements, 1)
    process_osc_measurements(osc_2_measurements, 2)
    process_osc_measurements(osc_3_measurements, 3)

    return measurement_strings


# Main test function
def ramp_current_and_capture_with_power_supply(
    voltage_list, current_list, dwell_time, input_current_limit, test_folder, power_supply: Union[RigolPowerSupply, KoradPowerSupply],
                                                                                                  load: RigolLoad, 
                                                                                                  oscilloscope_1: RigolOscilloscope,
                                                                                                  oscilloscope_2: RigolOscilloscope,
                                                                                                  oscilloscope_3: RigolOscilloscope,
                                                                                                  osc_1_measurements, 
                                                                                                  osc_2_measurements, 
                                                                                                  osc_3_measurements
                                                                                                  
):
    try:
   
        #set current mode and set to zero before turning on
        load.reset()
        load.turn_on()

        # Turn on the power supply
        print("Turning on the power supply output...")

        power_supply.reset()
        power_supply.turn_on()


        
        osc_measurement_headers = generate_measurement_strings(osc_1_measurements, osc_2_measurements, osc_3_measurements)

        for voltage in voltage_list:
            print(f"Starting tests for voltage: {voltage:.2f} V")

            

            # Create a new CSV file for this voltage
            csv_filename = os.path.join(test_folder, f"test_results_{voltage:.2f}V.csv")
            with open(csv_filename, mode="w", newline="") as csv_file:
                writer = csv.writer(csv_file)

                # Write the CSV header based on voltage
                if voltage <= 30:
                    table_headers = ["Input Voltage (V)", "Input Current (A)", "Input Power (W)","Load Voltage (V)",
                        "Load Current (A)","Load Power (W)","Efficiency (%)"]
                    
                    all_headers = table_headers + osc_measurement_headers
                    writer.writerow(all_headers)
                else:
                    table_headers = [
                        
                        "CH1 Voltage (V)", "CH1 Current (A)", "CH1 Power (W)",
                        "CH2 Voltage (V)", "CH2 Current (A)", "CH2 Power (W)",
                        "Total Input Power (W)","Load Voltage (V)", "Load Current (A)",
                        "Load Power (W)", "Efficiency (%)"
                    ]
                    all_headers = table_headers + osc_measurement_headers
                    writer.writerow(all_headers)


            # with open(csv_filename, mode="w", newline="") as csv_file:
            #     writer = csv.writer(csv_file)

            #     # Determine the header based on the voltage range
            #     if voltage <= 30:
            #         # Single-channel setup
            #         writer.writerow([
            #             "Input Voltage (V)", "Input Current (A)", "Input Power (W)",
            #             "Load Voltage (V)", "Load Current (A)", "Load Power (W)", "Efficiency (%)", "Load Power (W)", "Efficiency (%)", "CH 1 VMax", "CH 2 VMax",
                        # "CH 3 VMax", "CH 4 VMax"
            #         ])
            #     elif 30 < voltage <= 64:
            #         # Dual-channel setup
            #         writer.writerow([
            #             "CH1 Voltage (V)", "CH1 Current (A)", "CH1 Power (W)",
            #             "CH2 Voltage (V)", "CH2 Current (A)", "CH2 Power (W)",
            #             "Total Input Power (W)", "Load Voltage (V)", "Load Current (A)",
            #             "Load Power (W)", "Efficiency (%)", "Load Power (W)", "Efficiency (%)", "CH 1 VMax", "CH 2 VMax",
                        # "CH 3 VMax", "CH 4 VMax"
            #         ])
            #     else:
            #         # Tri-channel setup
            #         writer.writerow([
            #             "CH1 Voltage (V)", "CH1 Current (A)", "CH1 Power (W)",
            #             "CH2 Voltage (V)", "CH2 Current (A)", "CH2 Power (W)",
            #             "CH3 Voltage (V)", "CH3 Current (A)", "CH3 Power (W)",
            #             "Total Input Power (W)", "Load Voltage (V)", "Load Current (A)",
            #             "Load Power (W)", "Efficiency (%)", "CH 1 VMax", "CH 2 VMax",
                        # "CH 3 VMax", "CH 4 VMax"
            #         ])


                

                # Iterate through the current list
                for current in current_list:
                    #set voltage
                    power_supply.configure_voltage_current(voltage, input_current_limit)

                    # Adjust current range on the load

                    if current > 4:
                        load.turn_off()

                        load.set_current_range(40)
                        print("Set current range to 40 A")
                    else:
                        load.turn_off()
                        load.set_current_range(4)
 
                        print("Set current range to 4 A")

                    print(f"Setting load current to {current:.3f} A")

                    load.set_current(current)
                    load.turn_on
                    time.sleep(dwell_time/2)
                    #freezes oscilloscope screen to take screen shot
                    oscilloscope_1.trigger_single()
                    print("switching oscilloscope 1 to single")

                    oscilloscope_2.trigger_single()
                    print("switching oscilloscope 2 to single")

                    oscilloscope_3.trigger_single()
                    print("switching oscilloscope 3 to single")
                    time.sleep(dwell_time/2)

                    osc_measurement_values = read_oscilloscope_measurements(oscilloscope_1, oscilloscope_2, oscilloscope_3, osc_measurement_headers)

                    load_voltage = load.read_voltage()

                    load_measured_current = load.read_current()
                    load_power = load.read_power()

                    if voltage <= 30:
                        # Single-channel setup
                        ps_voltage, ps_current, ps_power = read_power_supply_channel(power_supply, 1)

                        # Calculate efficiency
                        efficiency = (load_power / ps_power)*100 if ps_power > 0 else 0.0
                        standard_measurements = [
                             
                            f"{ps_voltage:.3f}", f"{ps_current:.3f}", f"{ps_power:.3f}",f"{load_voltage:.3f}",
                            f"{load_measured_current:.3f}",  f"{load_power:.3f}", f"{efficiency:.3f}"
                        ]
                        value_list = standard_measurements + osc_measurement_values
                        # Write the data to the CSV
                        writer.writerow(value_list)
                    else:
                        # Dual-channel setup
                        ch1_voltage, ch1_current, ch1_power = read_power_supply_channel(power_supply, 1)
                        ch2_voltage, ch2_current, ch2_power = read_power_supply_channel(power_supply, 2)

                        # Calculate total input power and efficiency
                        total_input_power = ch1_power + ch2_power
                        efficiency = (load_power / total_input_power)*100 if total_input_power > 0 else 0.0

                        # Write the data to the CSV
                        standard_measurements =[
                            
                            f"{ch1_voltage:.3f}", f"{ch1_current:.3f}", f"{ch1_power:.3f}",
                            f"{ch2_voltage:.3f}", f"{ch2_current:.3f}", f"{ch2_power:.3f}",
                            f"{total_input_power:.3f}", f"{load_voltage:.3f}",f"{load_measured_current:.3f}", f"{load_power:.3f}", 
                            f"{efficiency:.3f}"
                        ]
                        value_list = standard_measurements + osc_measurement_values
                        writer.writerow(value_list)

                        # if voltage <= 30:
                        #     # Single-channel setup
                        #     ps_voltage, ps_current, ps_power = read_power_supply_channel(power_supply, 1)

                        #     # Calculate efficiency
                        #     efficiency = (load_power / ps_power) if ps_power > 0 else 0.0

                        #     # Write the data to the CSV
                        #     writer.writerow([
                        #         f"{ps_voltage:.3f}", f"{ps_current:.3f}", f"{ps_power:.3f}",
                        #         f"{load_voltage:.3f}", f"{load_measured_current:.3f}", f"{load_power:.3f}", f"{efficiency:.3f}",f"{vmax_ch1:.3f}", f"{vmax_ch2:.3f}", f"{vmax_ch3:.3f}", f"{vmax_ch4:.3f}"
                        #     ])
                        # elif 30 < voltage <= 64:
                        #     # Dual-channel setup
                        #     ch1_voltage, ch1_current, ch1_power = read_power_supply_channel(power_supply, 1)
                        #     ch2_voltage, ch2_current, ch2_power = read_power_supply_channel(power_supply, 2)

                        #     # Calculate total input power and efficiency
                        #     total_input_power = ch1_power + ch2_power
                        #     efficiency = (load_power / total_input_power) if total_input_power > 0 else 0.0

                        #     # Write the data to the CSV
                        #     writer.writerow([
                        #         f"{ch1_voltage:.3f}", f"{ch1_current:.3f}", f"{ch1_power:.3f}",
                        #         f"{ch2_voltage:.3f}", f"{ch2_current:.3f}", f"{ch2_power:.3f}",
                        #         f"{total_input_power:.3f}", f"{load_voltage:.3f}", f"{load_measured_current:.3f}", 
                        #         f"{load_power:.3f}", f"{efficiency:.3f}", f"{vmax_ch1:.3f}", f"{vmax_ch2:.3f}",
                        #         f"{vmax_ch3:.3f}", f"{vmax_ch4:.3f}"
                        #     ])
                        # else:
                        #     # Tri-channel setup for voltage > 64
                        #     ch1_voltage, ch1_current, ch1_power = read_power_supply_channel(power_supply, 1)
                        #     ch2_voltage, ch2_current, ch2_power = read_power_supply_channel(power_supply, 2)
                        #     ch3_voltage, ch3_current, ch3_power = read_power_supply_channel(power_supply, 3)

                        #     # Calculate total input power and efficiency
                        #     total_input_power = ch1_power + ch2_power + ch3_power
                        #     efficiency = (load_power / total_input_power) if total_input_power > 0 else 0.0

                        #     # Write the data to the CSV
                        #     writer.writerow([
                        #         f"{ch1_voltage:.3f}", f"{ch1_current:.3f}", f"{ch1_power:.3f}",
                        #         f"{ch2_voltage:.3f}", f"{ch2_current:.3f}", f"{ch2_power:.3f}",
                        #         f"{ch3_voltage:.3f}", f"{ch3_current:.3f}", f"{ch3_power:.3f}",
                        #         f"{total_input_power:.3f}", f"{load_voltage:.3f}", f"{load_measured_current:.3f}",
                        #         f"{load_power:.3f}", f"{efficiency:.3f}", f"{vmax_ch1:.3f}", f"{vmax_ch2:.3f}", f"{vmax_ch3:.3f}", f"{vmax_ch4:.3f}"
                        #     ])

                    # Capture oscilloscope screenshots
                    osc1_filename = os.path.join(
                        test_folder, f"oscilloscope1_{voltage:.2f}V_{current:.2f}A.png"
                    )
                    osc2_filename = os.path.join(
                        test_folder, f"oscilloscope2_{voltage:.2f}V_{current:.2f}A.png"
                    )
                    osc3_filename = os.path.join(
                        test_folder, f"oscilloscope3_{voltage:.2f}V_{current:.2f}A.png"
                    )

                    oscilloscope_1.capture_screenshot(osc1_filename)
                    oscilloscope_2.capture_screenshot(osc2_filename)
                    oscilloscope_3.capture_screenshot(osc3_filename)
                    time.sleep(1)
                    oscilloscope_1.trigger_run()

                    print("Switching osciloscope 1 to run mode")
                    oscilloscope_2.trigger_run()

                    print("Switching osciloscope 2 to run mode")
                    oscilloscope_3.trigger_run()
                    print("Switching oscilloscope 3 to run mode")
                                #set load current and supply voltage to zero, 30 second cool down before next run
                    load.set_current(0)
                    print("setting power supply voltage to zero")
                    power_supply.configure_voltage_current(0, input_current_limit)
                    print("sleep 15 seconds")
                    time.sleep(15)
            



        # Turn off load and power supply after the tests
        load.turn_off()
        load.set_current_range(4)
        # Reset to default current range
        power_supply.turn_off()

        print("Tests completed. Power supply turned off.")

    except Exception as e:
        print(f"Error during tests: {e}")
    finally:
        oscilloscope_1.close()
        oscilloscope_2.close()
        oscilloscope_3.close()
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
    parser.add_argument("--power_supply", type=str, required=True, help = "Power supply type rigol or korad")
    parser.add_argument("--osc_measurements", type=str, required=True)  # JSON string
    parser.add_argument("--test_folder", type=str, required=True, help="Folder to save test results")
    args = parser.parse_args()

    # Debugging: Print the parsed current_list
    print(f"Parsed current_list: {args.current_list}")

        # Deserialize osc_measurements
    try:
        osc_measurements = json.loads(args.osc_measurements)
    except json.JSONDecodeError as e:
        print(f"Error decoding osc_measurements JSON: {e}")
        sys.exit(1)

    # Debugging: Print the deserialized osc_measurements
    print(f"Deserialized osc_measurements: {json.dumps(osc_measurements, indent=2)}")

    # Access specific settings for each oscilloscope
    osc_1_measurements = osc_measurements.get("osc_1", {})
    osc_2_measurements = osc_measurements.get("osc_2", {})
    osc_3_measurements = osc_measurements.get("osc_3", {})


    oscilloscope_1 = RigolOscilloscope(OSCILLOSCOPE_1_ADDRESS)
    oscilloscope_2 = RigolOscilloscope(OSCILLOSCOPE_2_ADDRESS)
    oscilloscope_3 = RigolOscilloscope(OSCILLOSCOPE_3_ADDRESS)
    load = RigolLoad(LOAD_ADDRESS)

    power_supply = None
    try:
        if args.power_supply.lower() == "rigol":
            power_supply = RigolPowerSupply(RIGOL_POWER_SUPPLY_ADDRESS)
        elif args.power_supply.lower() == "korad":
            power_supply = KoradPowerSupply(port=KORAD_POWER_SUPPLY_COM)
        else:
            raise ValueError(f"Unknown power supply type: {args.power_supply}")

        if not power_supply.check_connection():
            raise ConnectionError(f"Power {args.power_supply} supply failed to connect.")
    except Exception as e:
        print(f"Error initializing power supply: {e}")
        sys.exit(1)


    if oscilloscope_1.check_connection and oscilloscope_3.check_connection() and load.check_connection() and power_supply.check_connection() and oscilloscope_2.check_connection():
        print("Ready to perform test")
        ramp_current_and_capture_with_power_supply(
            args.voltage_list,
            args.current_list, 
            args.dwell_time, 
            args.input_current_limit,
            args.test_folder,
            power_supply,
            load,
            oscilloscope_1,
            oscilloscope_2,
            oscilloscope_3,
            osc_1_measurements,
            osc_2_measurements,
            osc_3_measurements
        )
    else:
        print("One or more instruments failed to connect")
