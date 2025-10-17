import datetime
import os
import time
from rigol_usb_locator import RigolUsbLocator

def _MeasureOutputVoltageCurrent():
    """
    Preforms a sweep of all the input voltages and currents,
    and populates lists of the output voltages and currents.
    """
    try:
        header_line = ",".join(headers_list)
        filename = os.path.join("Tests", f"{test_result_file_prefix}_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv")
        with open(filename, "x") as f:
            f.write(header_line)
            f.write("\n")

            for input_voltage in input_voltage_list:
                for output_current in output_current_list:
                    power_supply.configure_voltage_current(input_voltage, input_current_limit)
                    if output_current > 4: 
                        load.turn_off()
                        load.set_current_range(40)
                    else: 
                        load.turn_off()
                        load.set_current_range(4)
                    load.set_current(output_current)
                    time.sleep(dwell_time)

                    read_output_voltage = load.read_voltage()
                    read_output_current = load.read_current()
                    read_input_voltage = power_supply.measure_voltage(power_supply_channel)
                    read_input_current = power_supply.measure_current(power_supply_channel)

                    recorded_output_voltage.append(read_output_voltage)
                    recorded_output_current.append(read_output_current)
                    recorded_input_voltage.append(read_input_voltage)
                    recorded_input_current.append(read_input_current)
                    
                    load.set_current(0)
                    power_supply.configure_voltage_current(0, input_current_limit)

                    row_string = ",".join([
                        str(read_input_voltage), 
                        str(read_input_current), 
                        str(read_output_voltage), 
                        str(read_output_current),
                    ])
                    
                    f.write(row_string)
                    f.write("\n")

                    time.sleep(cooldown_time)
    finally:
        try:
            load.turn_off()
        except Exception:
            pass
        try:
            load.set_current_range(4)
        except Exception:
            pass
        try:
            power_supply.turn_off()
        except Exception:
            pass

if __name__ == "__main__":
    usb_locator = RigolUsbLocator()
    usb_locator.refresh()
    load = usb_locator.get_load()
    power_supply = usb_locator.get_power_supply()

    test_result_file_prefix = "vc_sweep"
    headers_list = ["Input Voltage", "Input Current", "Output Voltage", "Output Current"]

    load.reset()
    load.turn_on()
    power_supply.reset()
    power_supply.turn_on()

    recorded_input_voltage = []
    recorded_input_current = []
    recorded_output_voltage = []
    recorded_output_current = []

    input_voltage_list = [12, 18, 24]
    output_current_list = [1, 2, 3]
    input_current_limit = 3.2
    dwell_time = 2
    cooldown_time = 1
    power_supply_channel = 1

    _MeasureOutputVoltageCurrent()
