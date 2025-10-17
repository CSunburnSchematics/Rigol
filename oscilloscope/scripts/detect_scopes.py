"""
Detect all connected Rigol DS1054Z oscilloscopes via USB
"""

import os
import sys

def detect_oscilloscopes():
    """Detect all connected Rigol oscilloscopes"""

    # Setup libusb path
    dll_path = os.path.join(os.path.dirname(__file__), "..", "lib", "libusb-1.0.dll")
    os.environ['PATH'] = os.path.dirname(dll_path) + os.pathsep + os.environ.get('PATH', '')

    import pyvisa

    # Create resource manager with PyVISA-py backend
    rm = pyvisa.ResourceManager('@py')

    # List all resources
    resources = rm.list_resources()
    print(f"\n{'='*60}")
    print(f"Total VISA resources found: {len(resources)}")
    print(f"{'='*60}\n")

    if not resources:
        print("No VISA resources detected!")
        print("Make sure:")
        print("  1. Oscilloscopes are powered on")
        print("  2. USB cables are connected")
        print("  3. USB drivers are installed")
        return []

    # Print all resources
    print("All detected resources:")
    for i, resource in enumerate(resources, 1):
        print(f"  {i}. {resource}")

    # Filter for potential oscilloscopes (USB, TCPIP, or any Rigol device)
    potential_scopes = []

    # Check USB resources
    usb_scopes = [r for r in resources if 'USB' in r and ('1AB1' in r or '6833' in r)]
    potential_scopes.extend(usb_scopes)

    # Check TCPIP resources (network-connected scopes)
    tcpip_scopes = [r for r in resources if 'TCPIP' in r]
    potential_scopes.extend(tcpip_scopes)

    print(f"\n{'='*60}")
    print(f"USB Oscilloscopes: {len(usb_scopes)}")
    print(f"TCPIP Oscilloscopes: {len(tcpip_scopes)}")
    print(f"Total potential scopes: {len(potential_scopes)}")
    print(f"{'='*60}\n")

    # If no USB scopes found, try querying ALL resources to see if any are Rigol
    if not potential_scopes:
        print("No obvious oscilloscope resources found.")
        print("Attempting to query ALL resources (this may take a moment)...\n")
        potential_scopes = resources

    # Query each potential scope
    scope_info = []
    for i, resource_name in enumerate(potential_scopes, 1):
        # Skip serial ports when scanning all resources (they timeout)
        if 'ASRL' in resource_name and len(potential_scopes) > 2:
            print(f"Skipping {resource_name} (serial port)\n")
            continue

        try:
            print(f"Testing {i}: {resource_name}")
            scope = rm.open_resource(resource_name)
            scope.timeout = 2000  # 2 second timeout

            # Query identification
            idn = scope.query('*IDN?').strip()
            print(f"  Identity: {idn}")

            # Parse IDN response (format: MANUFACTURER,MODEL,SERIAL,VERSION)
            idn_parts = idn.split(',')
            if len(idn_parts) >= 3:
                manufacturer = idn_parts[0]
                model = idn_parts[1]
                serial = idn_parts[2]
                print(f"  Manufacturer: {manufacturer}")
                print(f"  Model: {model}")
                print(f"  Serial: {serial}")

            scope_info.append({
                'resource': resource_name,
                'idn': idn,
                'index': i
            })

            scope.close()
            print(f"  Status: OK - Connected successfully\n")

        except Exception as e:
            print(f"  Status: ERROR - {type(e).__name__}\n")

    return scope_info

if __name__ == '__main__':
    print("\nRigol DS1054Z Oscilloscope Detection")
    print("=" * 60)

    scopes = detect_oscilloscopes()

    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(scopes)} oscilloscope(s) ready for use")
    print(f"{'='*60}\n")

    if scopes:
        print("You can now test each scope individually:")
        print("Example:")
        for scope in scopes:
            print(f"  # Test scope {scope['index']}")
            print(f"  # Resource: {scope['resource']}\n")
