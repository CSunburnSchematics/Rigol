import subprocess, sys
from rigol_usb_locator import RigolUsbLocator
from nice_power_usb_locator import NicePowerLocator

# Get script name from command line, default to high_res_test
test_script = sys.argv[1] if len(sys.argv) > 1 else "oscilloscope_high_res_test.py"
print(f"Using script: {test_script}")

# Initialize locators
rigol_loc = RigolUsbLocator(verbose=False)
nice_loc = NicePowerLocator(verbose=False)
nice_loc.refresh()

# Find Rigol power supplies
psu_addrs = [addr for addr in rigol_loc._list_usb_resources()
             if rigol_loc._classify(rigol_loc._query_idn(addr)) == "power_supply"]
print(f"Found {len(psu_addrs)} Rigol power supply(s)")

# Launch Rigol power supply scripts
for addr in psu_addrs:
    print(f"Setting up Rigol power supply: {addr}")
    subprocess.Popen([sys.executable, "set_rigol_power_supply.py", addr, "1"])

# Get Nice power supplies
nice_psu_list = nice_loc.get_power_supplies()
print(f"Found {len(nice_psu_list)} Nice Power supply(s)")

# Launch Nice power supply scripts
for com_port, slave_addr, psu_instance in nice_psu_list:
    print(f"Setting up Nice Power supply: {com_port} (slave {slave_addr})")
    subprocess.Popen([sys.executable, "set_nice_power_supply.py", com_port, "1", str(slave_addr)])

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