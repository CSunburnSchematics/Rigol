#!/usr/bin/env python3
"""
Capture waveform data from DS1054Z oscilloscope channel 1
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

def connect_scope():
    """Connect to the oscilloscope"""
    # Set up libusb backend path
    dll_path = os.path.join(os.getcwd(), "libusb-1.0.dll")
    os.environ['PATH'] = os.getcwd() + os.pathsep + os.environ.get('PATH', '')

    import pyvisa

    print("Connecting to oscilloscope...")
    rm = pyvisa.ResourceManager('@py')

    # Find USB resource
    resources = rm.list_resources()
    usb_resources = [r for r in resources if 'USB' in r and ('1AB1' in r.upper() or '6833' in r)]

    if not usb_resources:
        print("[ERROR] Oscilloscope not found")
        return None

    resource_str = usb_resources[0]
    scope = rm.open_resource(resource_str)
    scope.timeout = 10000  # 10 second timeout

    print(f"[OK] Connected to: {resource_str}")
    print(f"     {scope.query('*IDN?').strip()}")

    return scope

def capture_waveform(scope, channel=1):
    """Capture waveform data from specified channel"""

    print(f"\nCapturing waveform from Channel {channel}...")

    # Set waveform source to channel 1
    scope.write(f':WAVeform:SOURce CHANnel{channel}')

    # Set waveform mode to NORMAL (for most accurate data)
    scope.write(':WAVeform:MODE NORMal')

    # Set waveform format to BYTE (faster) or ASCii
    scope.write(':WAVeform:FORMat BYTE')

    # Get waveform preamble (contains scaling information)
    print("Reading waveform parameters...")
    preamble = scope.query(':WAVeform:PREamble?')
    preamble_values = [float(x) for x in preamble.split(',')]

    # Preamble format:
    # 0: format, 1: type, 2: points, 3: count, 4: xincrement, 5: xorigin,
    # 6: xreference, 7: yincrement, 8: yorigin, 9: yreference

    points = int(preamble_values[2])
    x_increment = preamble_values[4]
    x_origin = preamble_values[5]
    x_reference = preamble_values[6]
    y_increment = preamble_values[7]
    y_origin = preamble_values[8]
    y_reference = preamble_values[9]

    print(f"  Sample points: {points}")
    print(f"  Time increment: {x_increment} s")
    print(f"  Voltage increment: {y_increment} V")

    # Get the waveform data
    print("Reading waveform data...")
    scope.write(':WAVeform:DATA?')

    # Read raw data
    raw_data = scope.read_raw()

    # Parse the IEEE 488.2 format
    # First character is '#', second is number of digits, then the length
    header_len = 2 + int(chr(raw_data[1]))
    data = raw_data[header_len:-1]  # Remove header and trailing newline

    # Convert bytes to numpy array
    waveform_data = np.frombuffer(data, dtype=np.uint8)

    print(f"  Captured {len(waveform_data)} data points")

    # Convert to voltage values
    # Formula: voltage = ((data - yreference) * yincrement) + yorigin
    voltages = ((waveform_data - y_reference) * y_increment) + y_origin

    # Create time array
    # Formula: time = ((point - xreference) * xincrement) + xorigin
    times = np.arange(len(waveform_data)) * x_increment + x_origin

    # Get additional channel info
    try:
        ch_scale = float(scope.query(f':CHANnel{channel}:SCALe?'))
        ch_offset = float(scope.query(f':CHANnel{channel}:OFFSet?'))
        timebase = float(scope.query(':TIMebase:SCALe?'))

        print(f"\nChannel Settings:")
        print(f"  Vertical scale: {ch_scale} V/div")
        print(f"  Vertical offset: {ch_offset} V")
        print(f"  Timebase: {timebase} s/div")
    except:
        pass

    return times, voltages

def plot_waveform(times, voltages, channel=1):
    """Plot the captured waveform"""

    print("\nGenerating plot...")

    plt.figure(figsize=(12, 6))
    plt.plot(times * 1e6, voltages, linewidth=0.5)  # Convert to microseconds
    plt.xlabel('Time (μs)')
    plt.ylabel('Voltage (V)')
    plt.title(f'DS1054Z Channel {channel} Waveform')
    plt.grid(True, alpha=0.3)

    # Add statistics
    v_max = np.max(voltages)
    v_min = np.min(voltages)
    v_pp = v_max - v_min
    v_avg = np.mean(voltages)

    stats_text = f'Vmax: {v_max:.3f}V\nVmin: {v_min:.3f}V\nVpp: {v_pp:.3f}V\nVavg: {v_avg:.3f}V'
    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()

    # Save to file
    filename = f'waveform_ch{channel}.png'
    plt.savefig(filename, dpi=150)
    print(f"[OK] Plot saved to: {filename}")

    # Don't show plot interactively (causes timeout in CLI)
    plt.close()

def save_data(times, voltages, channel=1):
    """Save waveform data to CSV file"""

    filename = f'waveform_ch{channel}.csv'

    print(f"Saving data to: {filename}")

    # Combine times and voltages
    data = np.column_stack((times, voltages))

    # Save with header
    header = 'Time (s),Voltage (V)'
    np.savetxt(filename, data, delimiter=',', header=header, comments='')

    print(f"[OK] Data saved to: {filename}")

def main():
    # Connect to scope
    scope = connect_scope()

    if not scope:
        return 1

    try:
        # Check if channel 1 is enabled
        ch1_display = scope.query(':CHANnel1:DISPlay?').strip()

        if ch1_display == '0':
            print("\n[WARNING] Channel 1 is currently OFF")
            print("Enabling Channel 1...")
            scope.write(':CHANnel1:DISPlay ON')

        # Capture waveform
        times, voltages = capture_waveform(scope, channel=1)

        # Print statistics
        print(f"\nWaveform Statistics:")
        print(f"  Max voltage:  {np.max(voltages):.4f} V")
        print(f"  Min voltage:  {np.min(voltages):.4f} V")
        print(f"  Peak-to-peak: {np.max(voltages) - np.min(voltages):.4f} V")
        print(f"  Average:      {np.mean(voltages):.4f} V")
        print(f"  RMS:          {np.sqrt(np.mean(voltages**2)):.4f} V")

        # Save data to CSV
        save_data(times, voltages, channel=1)

        # Plot waveform
        plot_waveform(times, voltages, channel=1)

        print("\n[SUCCESS] Waveform capture complete!")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        scope.close()
        print("Connection closed.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
