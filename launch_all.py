import subprocess, sys, json, os
import time
from rigol_usb_locator import RigolUsbLocator
from nice_power_usb_locator import NicePowerLocator

# Get config filename from command line or use default
config_file = sys.argv[1] if len(sys.argv) > 1 else "default_config.json"
config_path = os.path.join("Configs", config_file)

# Load config (will crash if file doesn't exist - as intended)
with open(config_path, 'r') as f:
    config = json.load(f)

print(f"Using config: {config_file}")

# Initialize locators
rigol_loc = RigolUsbLocator(verbose=False)
nice_loc = NicePowerLocator(verbose=False)
nice_loc.refresh()
rigol_loc.refresh()

# Find Rigol power supply
rigol_psu = rigol_loc.get_power_supply()
if rigol_psu:
    try:
        print(f"Configuring Rigol Power supply")
        for ch in [1, 2, 3]:
            psu_config = config["power_supplies"]["rigol"]["DP8B261601128"]["channels"][str(ch)]
            voltage = psu_config["vout"]
            current = psu_config["iout_max"]
            rigol_psu.turn_channel_on(ch)
            rigol_psu.set_voltage(ch, voltage)
            rigol_psu.set_current_limit(ch, current)

            # Wait for voltage to rise and stabilize (at least 1 second)
            time.sleep(2)

            rigol_ch_read = rigol_psu.read_power_supply_channel(ch)
            

        print(f"  [OK] Set to {voltage}V, {current}A, read is {rigol_ch_read}")
    except Exception as e:
        print(f"  [FAIL] Failed to configure: {e}")
else:
    print("No Rigol Power supply found")

# Configure Nice power supplies from config
nice_psu_list = nice_loc.get_power_supplies()
print(nice_psu_list)
print(f"Found {len(nice_psu_list)} Nice Power supply(s)")

for com_port, device_type, addr, psu in nice_psu_list:
    try:
        print(f"Configuring Nice Power supply ({device_type}): {com_port} (addr {addr})")

        # Get config: D2001 by type, Modbus by COM port
        psu_config = None
        if device_type == "d2001":
            psu_config = config["power_supplies"]["nice_power"]["SPPS_D2001_232"]
        else:  # modbus - match by COM port
            for psu_id, psu_cfg in config["power_supplies"]["nice_power"].items():
                if psu_cfg.get("com_port") == com_port:
                    psu_config = psu_cfg
                    break

        if not psu_config:
            print(f"  [WARN] No config found, skipping")
            continue

        voltage = psu_config["vout"]
        current = psu_config["iout_max"]

        # Set values using reliable configure method with verification
        # This is especially important for Modbus supplies (SPPS_D8001/D6001)
        # which can have communication issues
        if device_type == "modbus" and hasattr(psu, 'configure_voltage_current'):
            # Use Claire's robust configure method with retry logic
            psu.configure_voltage_current(voltage, current, verify=True, max_retries=3, tol=0.2)
        else:
            # Fallback for D2001 or older supplies
            psu.set_remote(True)
            psu.set_current_limit(current)
            psu.set_voltage(voltage)
            if voltage > 0:
                psu.turn_on()

        # Wait for voltage to rise and stabilize (at least 1 second)
        time.sleep(2)

        v_out = psu.measure_voltage()    

        

        print(f"  [OK] Set to {voltage}V, {current}A, voltage read is: {v_out}V")
    except Exception as e:
        print(f"  [FAIL] Failed to configure: {e}")

# Find all oscilloscopes
osc_addrs = [addr for addr in rigol_loc._list_usb_resources()
             if rigol_loc._classify(rigol_loc._query_idn(addr)) == "oscilloscope"]
print(f"Found {len(osc_addrs)} oscilloscope(s)")

# Get oscilloscope script from config
osc_script = config["test_settings"]["oscilloscope_script"]

# Launch oscilloscope test scripts with config file
for idx, addr in enumerate(osc_addrs):
    print(f"Launching: {addr}")
    subprocess.Popen(f'start "Oscilloscope {idx}" cmd /k python {osc_script} {addr} {config_file}',
                     shell=True)

print("All launched!")