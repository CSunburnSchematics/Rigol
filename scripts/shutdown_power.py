from nice_power_usb_locator import NicePowerLocator
from rigol_usb_locator import RigolUsbLocator

nice_loc = NicePowerLocator(verbose=False)
nice_loc.refresh()
rigol_loc = RigolUsbLocator(verbose=False)
rigol_loc.refresh()

rigol_psu = rigol_loc.get_power_supply()
if rigol_psu:
    print(f"Found Rigol Power supply")
    try:
        for ch in [1, 2, 3]:
            rigol_psu.turn_channel_off(ch)
            rigol_psu.set_voltage(ch, 0)
            rigol_psu.set_current_limit(ch, 0)
        rigol_psu.close()
        print(f"Shut down Rigol PS (all channels off, 0V, 0A)")
    except Exception as e:
        print(f"Failed Rigol shutdown: {e}")
else:
    print("No Rigol Power supply found")

nice_psu_list = nice_loc.get_power_supplies()
print(f"Found {len(nice_psu_list)} Nice Power supply(s)")

for com_port, device_type, addr, psu in nice_psu_list:
    try:
        psu.set_current_limit(0)
        psu.set_voltage(0)
        psu.close()
        print(f"Shut down {device_type} on {com_port}")
    except Exception as e:
        print(f"Failed shutdown: {e}")