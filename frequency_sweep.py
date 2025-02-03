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

from Rigol_DP832A import RigolPowerSupply
from Rigol_DL3021A import RigolLoad
from Rigol_DG1022z import RigolFunctionGenerator

rm = pyvisa.ResourceManager()

LOAD_ADDRESS = "USB0::0x1AB1::0x0E11::DL3B262800287::INSTR"
RIGOL_POWER_SUPPLY_ADDRESS = "USB0::0x1AB1::0x0E11::DP8B261601128::INSTR"
GENERATOR_ADDRESS = "USB0::0x1AB1::0x0642::DG1ZA262302791::INSTR"

# Function to create a unique folder for each test
def create_test_folder(test_setup_name):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"test_{test_setup_name}_{timestamp}"
    os.makedirs(folder_name, exist_ok=True)
    return folder_name

def copy_screenshots_to_assets(test_folder):
    assets_folder = os.path.join(os.getcwd(), "assets")
    os.makedirs(assets_folder, exist_ok=True)
    
    for file in os.listdir(test_folder):
        if file.endswith(".png") or file.endswith(".jpg"):
            shutil.copy(os.path.join(test_folder, file), os.path.join(assets_folder, file))
    print(f"Screenshots copied to assets folder.")

# Function to read voltage, current, and power from the power supply
def read_power_supply_channel(power_supply: RigolPowerSupply, channel):
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



def frequency_sweep_test(
    frequency_list,
    voltage_list,
    waveform,
    amplitude,
    dcoffset,
    phase, 
    dwell_time, 
    input_current_limit,
    test_folder,
    current,
    power_supply: RigolPowerSupply,
    load: RigolLoad,
    generator: RigolFunctionGenerator):
                                                                                                  
                                                                                                  
    try:
   
        #set current mode and set to zero before turning on
        load.reset()
        load.turn_on()

        # Turn on the power supply
        print("Turning on the power supply output...")

        power_supply.reset()
        power_supply.turn_on()


        if current > 4:
            load.turn_off()

            load.set_current_range(40)
            print("Set current range to 40 A")
        else:
            load.turn_off()
            load.set_current_range(40)

            print("Set current range to 4 A")

        print(f"Setting load current to {current:.3f} A")

        load.set_current(current)

        generator.set_up_sweep(waveform, amplitude, dcoffset, phase, 1)


        load.turn_on

    

        for voltage in voltage_list:
            print(f"Starting tests for voltage: {voltage:.2f} V")



            # Create a new CSV file for this voltage
            csv_filename = os.path.join(test_folder, f"test_results_{voltage:.2f}V.csv")
            with open(csv_filename, mode="w", newline="") as csv_file:
                writer = csv.writer(csv_file)

                # Write the CSV header based on voltage
                if voltage <= 30:
                    table_headers = ["Frequency (kHz)","Input Voltage (V)", "Input Current (A)", "Input Power (W)","Load Voltage (V)",
                        "Load Current (A)","Load Power (W)","Efficiency (%)"]
                    
                    all_headers = table_headers
                    writer.writerow(all_headers)
                else:
                    table_headers = [
                        
                    "Frequency (kHz)","CH1 Voltage (V)", "CH1 Current (A)", "CH1 Power (W)",
                        "CH2 Voltage (V)", "CH2 Current (A)", "CH2 Power (W)",
                        "Total Input Power (W)","Load Voltage (V)", "Load Current (A)",
                        "Load Power (W)", "Efficiency (%)"
                    ]
                    all_headers = table_headers
                    writer.writerow(all_headers)


                
                    power_supply.configure_voltage_current(voltage, input_current_limit)
                    for frequency in frequency_list:
                        frequency = frequency*1000 #convert Hz to kHz
                        generator.set_frequency(1, frequency)
                        generator.enable_output(1)
                        time.sleep(dwell_time)

                        
                        load_voltage = load.read_voltage()

                        load_measured_current = load.read_current()
                        load_power = load.read_power()

                        if voltage <= 30:
                            # Single-channel setup
                            ps_voltage, ps_current, ps_power = read_power_supply_channel(power_supply, 1)



                            # Calculate efficiency
                            efficiency = (load_power / ps_power)*100 if ps_power > 0 else 0.0
                            standard_measurements = [
                                
                                f"{frequency/1000}", f"{ps_voltage:.3f}", f"{ps_current:.3f}", f"{ps_power:.3f}",f"{load_voltage:.3f}",
                                f"{load_measured_current:.3f}",  f"{load_power:.3f}", f"{efficiency:.3f}"
                            ]
                            value_list = standard_measurements 
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
                                
                                f"{frequency/1000}", f"{ch1_voltage:.3f}", f"{ch1_current:.3f}", f"{ch1_power:.3f}",
                                f"{ch2_voltage:.3f}", f"{ch2_current:.3f}", f"{ch2_power:.3f}",
                                f"{total_input_power:.3f}", f"{load_voltage:.3f}",f"{load_measured_current:.3f}", f"{load_power:.3f}", 
                                f"{efficiency:.3f}"
                            ]
                            value_list = standard_measurements 
                            writer.writerow(value_list)
                    
                    
                    generator.disable_output(1)


                
            
            


        # Turn off load and power supply after the tests
        load.turn_off()
        load.set_current_range(4)
        #set current to zero before finishing test
        load.set_current(0)
        # Reset to default current range
        power_supply.turn_off()
        generator.disable_output(1)

        print("Tests completed. Power supply turned off.")

    except Exception as e:
        print(f"Error during tests: {e}")
    finally:
 
        load.close()
        power_supply.close()
        generator.close()

    copy_screenshots_to_assets(test_folder)

  









def parse_float_list(value):
    """
    Parses a comma-separated string into a list of floats.
    Example: "1.0,2.5,3.3" -> [1.0, 2.5, 3.3]
    """
    try:

        return [float(x.strip()) for x in value.split(',')]
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid format for list. Provide a comma-separated list of floats.")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Frequency Sweep script")
    parser.add_argument(    
        "--frequency_list", 
        type=parse_float_list, 
        required=True, 
        help="List of frequency values to test (comma-separated, e.g., '100, 200, 300')"
    )
    parser.add_argument(    
        "--voltage_list", 
        type=parse_float_list, 
        required=True, 
        help="List of voltage values to test (comma-separated, e.g., '35, 50.5, 64')"
    )
    parser.add_argument(
        "--waveform",
        type=str,
        choices=["sine", "square", "ramp", "pulse", "noise"],
        required=True,
        help="Waveform type to use for the sweep (e.g., 'sine')."
    )

    parser.add_argument(
        "--amplitude",
        type=float,
        required=True,
        help="Amplitude of the waveform in volts."
    )

    parser.add_argument(
        "--dcoffset",
        type=float,
        required=True,
        help="DC offset of the waveform in volts."
    )

    parser.add_argument(
        "--phase",
        type=float,
        required=True,
        help="Phase of the waveform in degrees."
    )

    parser.add_argument(
        "--dwell_time",
        type=float,
        required=True,
        help="Dwell time for each frequency step in seconds."
    )

    parser.add_argument(
        "--input_current_limit",
        type=float,
        required=True,
        help="Current limit for the test in amps."
    )

    parser.add_argument(
        "--current",
        type=float,
        required=True,
        help="Current in amps."
    )

    parser.add_argument(
        "--test_folder",
        type=str,
        required=True,
        help="Path to the folder where test results will be saved."
    )

    args = parser.parse_args()
 

    load = RigolLoad(LOAD_ADDRESS)

    power_supply = RigolPowerSupply(RIGOL_POWER_SUPPLY_ADDRESS)

    generator = RigolFunctionGenerator(GENERATOR_ADDRESS)
   


    if  load.check_connection() and power_supply.check_connection() and generator.check_connection():
        print("Ready to perform test")
        frequency_sweep_test(
            args.frequency_list,
            args.voltage_list,
            args.waveform,
            args.amplitude,
            args.dcoffset,
            args.phase, 
            args.dwell_time, 
            args.input_current_limit,
            args.test_folder,
            args.current,
            power_supply,
            load,
            generator
            
        )
    else:
        print("One or more instruments failed to connect")
