#!/usr/bin/env python3
"""
Identify D6001 vs D8001 by testing maximum voltage capability
D6001: Max 60V
D8001: Max 80V
"""

import sys
import os
import time

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from NICE_POWER_SPPS_D8001_232 import NicePowerSupply

def identify_supply(com_port):
    """
    Identify supply by attempting to set high voltage
    Returns: "D6001" or "D8001" or "Unknown"
    """
    print(f"\nTesting {com_port}...")

    try:
        psu = NicePowerSupply(port=com_port, slave_addr=1, baudrate=9600)

        # Make sure output is OFF for safety
        psu.set_remote(True)
        psu.turn_off()
        time.sleep(0.2)

        # Read current voltage
        current_v = psu.measure_voltage()
        print(f"  Current voltage: {current_v:.2f}V")

        # Try to set 70V (D8001 should accept, D6001 should reject or cap at 60V)
        print(f"  Attempting to set 70V...")
        psu.set_voltage(70.0)
        time.sleep(0.2)

        # Read back the SET voltage (not measured, since output is off)
        set_v = psu.read_set_voltage()
        print(f"  Set voltage readback: {set_v:.2f}V")

        # Reset to safe value
        psu.set_voltage(0.0)
        psu.set_remote(False)
        psu.close()

        # Determine model based on accepted setpoint
        if set_v >= 69.0:  # Allow 1V tolerance
            return "D8001"
        elif set_v >= 59.0 and set_v < 61.0:  # Capped at 60V
            return "D6001"
        else:
            return f"Unknown (set {set_v:.1f}V)"

    except Exception as e:
        print(f"  Error: {e}")
        return "Error"

def main():
    print("="*70)
    print("NICE POWER MODBUS SUPPLY IDENTIFIER")
    print("="*70)
    print("This will identify D6001 vs D8001 by testing voltage limits")
    print("Output will remain OFF during testing for safety")
    print("="*70)

    # Test the two Modbus supplies we detected
    supplies = [
        ("COM4", None),
        ("COM12", None)
    ]

    results = {}

    for com_port, _ in supplies:
        model = identify_supply(com_port)
        results[com_port] = model

    print("\n" + "="*70)
    print("IDENTIFICATION RESULTS")
    print("="*70)
    for com_port, model in results.items():
        print(f"{com_port}: {model}")
    print("="*70)

    # Suggest config updates
    print("\nSuggested configuration:")
    if results.get("COM4") == "D6001" and results.get("COM12") == "D8001":
        print("  ✓ Current config is CORRECT")
        print("  - COM4: D6001 (60V)")
        print("  - COM12: D8001 (80V)")
    elif results.get("COM4") == "D8001" and results.get("COM12") == "D6001":
        print("  ✗ Current config is SWAPPED - needs update:")
        print("  - COM4: D8001 (80V) <- currently labeled as D6001")
        print("  - COM12: D6001 (60V) <- currently labeled as D8001")
    else:
        print("  ? Could not determine - check results above")

    return 0

if __name__ == "__main__":
    sys.exit(main())
