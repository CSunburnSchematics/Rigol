import subprocess, sys
from rigol_usb_locator import RigolUsbLocator
from nice_power_usb_locator import NicePowerLocator

# Parse args: voltage (number) and test script (.py file), any order
args = sys.argv[1:]
VOLTAGE = next((float(a) for a in args if a.replace('.', '').replace('-', '').isdigit()), 1.0)
test_script = next((a for a in args if a.endswith('.py')), "oscilloscope_high_res_test.py")
print(f"Using voltage: {VOLTAGE}V, script: {test_script}")

# Initialize locators
rigol_loc = RigolUsbLocator(verbose=False)
nice_loc = NicePowerLocator(verbose=False)
nice_loc.refresh()

# # Find Rigol power supplies
# psu_addrs = [addr for addr in rigol_loc._list_usb_resources()
#              if rigol_loc._classify(rigol_loc._query_idn(addr)) == "power_supply"]
# print(f"Found {len(psu_addrs)} Rigol power supply(s)")

# # Launch Rigol power supply scripts
# for addr in psu_addrs:
#     print(f"Setting up Rigol power supply: {addr}")
#     subprocess.Popen([sys.executable, "set_rigol_power_supply.py", addr, "1"])

# Configure Nice power supplies
nice_psu_list = nice_loc.get_power_supplies()
print(f"Found {len(nice_psu_list)} Nice Power supply(s)")

CURRENT = 0.1

for com_port, device_type, addr, psu in nice_psu_list:
    try:
        print(f"Configuring Nice Power supply ({device_type}): {com_port} (addr {addr})")

        psu.set_remote(True)
        psu.set_current_limit(CURRENT)
        psu.set_voltage(VOLTAGE)
        if VOLTAGE > 0:
            psu.turn_on()

        print(f"  ✓ Set to {VOLTAGE}V, {CURRENT}A")
    except Exception as e:
        print(f"  ✗ Failed to configure: {e}")

# Skip oscilloscope tests if voltage is 0
if VOLTAGE == 0:
    print("\nVoltage is 0V - skipping oscilloscope tests")
    sys.exit(0)

# Find all oscilloscopes
osc_addrs = [addr for addr in rigol_loc._list_usb_resources()
             if rigol_loc._classify(rigol_loc._query_idn(addr)) == "oscilloscope"]
print(f"Found {len(osc_addrs)} oscilloscope(s)")

# Launch oscilloscope test scripts
for idx, addr in enumerate(osc_addrs):
    print(f"Launching: {addr}")
    subprocess.Popen(f'start "Oscilloscope {idx}" cmd /k python {test_script} {addr}',
                     shell=True)

print("All launched!")