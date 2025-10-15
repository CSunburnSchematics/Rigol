#!/usr/bin/env python3
"""
Deep memory capture from DS1054Z using RAW mode
Can capture up to 24M points from memory buffer
Based on official Rigol programming guide
"""

import sys
import os
import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

def connect_scope():
    """Connect to oscilloscope"""
    dll_path = os.path.join(os.getcwd(), "libusb-1.0.dll")
    os.environ['PATH'] = os.getcwd() + os.pathsep + os.environ.get('PATH', '')

    import pyvisa
    rm = pyvisa.ResourceManager('@py')
    resources = rm.list_resources()
    usb_resources = [r for r in resources if 'USB' in r and ('1AB1' in r.upper() or '6833' in r)]

    if not usb_resources:
        return None

    scope = rm.open_resource(usb_resources[0])
    scope.timeout = 120000  # 120s timeout for large transfers
    scope.chunk_size = 20480  # Set chunk size for VISA reads
    return scope

def query_memory_depth(scope):
    """Query current memory depth setting"""
    print("Querying oscilloscope settings...")

    # Get current memory depth
    mdepth = scope.query(':ACQuire:MDEPth?').strip()
    print(f"  Current memory depth: {mdepth}")

    # Get sample rate
    try:
        srate = float(scope.query(':ACQuire:SRATe?').strip())
        print(f"  Sample rate: {srate/1e6:.2f} MSa/s")
    except:
        srate = None

    return mdepth, srate

def set_memory_depth(scope, depth='AUTO'):
    """
    Set memory depth
    Options: AUTO, 12000, 120000, 1200000, 12000000, 24000000
    """
    print(f"\nSetting memory depth to: {depth}")
    scope.write(f':ACQuire:MDEPth {depth}')
    time.sleep(0.2)

    actual = scope.query(':ACQuire:MDEPth?').strip()
    print(f"  Memory depth set to: {actual}")

    return actual

def capture_deep_memory(scope, channel=1, max_points=None):
    """
    Capture deep memory using RAW mode
    Reads in chunks if data exceeds 250K points (BYTE format limit)
    """

    print(f"\n{'='*70}")
    print("DEEP MEMORY CAPTURE")
    print('='*70)

    # MUST stop acquisition for RAW mode
    print("\nStopping acquisition...")
    scope.write(':STOP')
    time.sleep(0.5)

    # Configure waveform settings
    print(f"Configuring waveform source: Channel {channel}")
    scope.write(f':WAVeform:SOURce CHANnel{channel}')
    scope.write(':WAVeform:MODE RAW')  # Deep memory mode
    scope.write(':WAVeform:FORMat BYTE')  # 1 byte per point

    # Get preamble to find total points available
    print("Reading waveform preamble...")
    preamble = scope.query(':WAVeform:PREamble?')
    preamble_values = [float(x) for x in preamble.split(',')]

    # Preamble: format, type, points, count, xinc, xorig, xref, yinc, yorig, yref
    total_points = int(preamble_values[2])
    x_increment = preamble_values[4]
    x_origin = preamble_values[5]
    y_increment = preamble_values[7]
    y_origin = preamble_values[8]
    y_reference = preamble_values[9]

    print(f"\nMemory buffer info:")
    print(f"  Total points available: {total_points:,}")
    print(f"  Time increment: {x_increment} s ({1/x_increment/1e6:.2f} MSa/s)")
    print(f"  Voltage increment: {y_increment} V")

    # Limit points if requested
    if max_points and max_points < total_points:
        total_points = max_points
        print(f"  Limiting capture to: {total_points:,} points")

    # Chunk size (BYTE format max: 250,000)
    # Start with smaller chunks to test transfer speed
    CHUNK_SIZE = 50000  # 50K points per chunk

    num_chunks = (total_points + CHUNK_SIZE - 1) // CHUNK_SIZE

    print(f"\nTransfer plan:")
    print(f"  Total points to capture: {total_points:,}")
    print(f"  Chunk size: {CHUNK_SIZE:,}")
    print(f"  Number of chunks: {num_chunks}")
    print(f"  Estimated size: {total_points / 1024 / 1024:.2f} MB")

    # Capture start timestamp
    capture_timestamp = datetime.now(timezone.utc)
    print(f"\nCapture timestamp: {capture_timestamp.isoformat()}")

    # Read data in chunks
    all_data = []

    print(f"\nTransferring data...")
    total_start = time.time()

    for chunk_num in range(num_chunks):
        chunk_start = chunk_num * CHUNK_SIZE + 1  # 1-indexed
        chunk_end = min((chunk_num + 1) * CHUNK_SIZE, total_points)
        chunk_points = chunk_end - chunk_start + 1

        print(f"  Chunk {chunk_num + 1}/{num_chunks}: "
              f"points {chunk_start:,} to {chunk_end:,} ({chunk_points:,} points)...",
              end='', flush=True)

        # Set start and stop points
        scope.write(f':WAVeform:STARt {chunk_start}')
        scope.write(f':WAVeform:STOP {chunk_end}')

        # Time the transfer
        chunk_transfer_start = time.time()

        # Request data
        scope.write(':WAVeform:DATA?')
        raw_data = scope.read_raw()

        chunk_transfer_time = time.time() - chunk_transfer_start

        # Parse TMC header: #N + N digits for length
        header_len = 2 + int(chr(raw_data[1]))
        data = raw_data[header_len:-1]  # Remove header and trailing \n

        # Convert to numpy array
        chunk_data = np.frombuffer(data, dtype=np.uint8)

        all_data.append(chunk_data)

        throughput = len(raw_data) / 1024 / chunk_transfer_time
        print(f" {chunk_transfer_time:.2f}s ({throughput:.1f} KB/s)", flush=True)

    total_time = time.time() - total_start

    # Concatenate all chunks
    waveform_data = np.concatenate(all_data)

    print(f"\nTransfer complete!")
    print(f"  Total time: {total_time:.2f} seconds")
    print(f"  Total points: {len(waveform_data):,}")
    print(f"  Average rate: {len(waveform_data) / total_time:,.0f} points/sec")

    # Convert to voltages
    print("\nConverting to voltage values...")
    voltages = ((waveform_data - y_reference) * y_increment) + y_origin

    # Create time array
    times = np.arange(len(waveform_data)) * x_increment + x_origin

    # Statistics
    print(f"\nWaveform statistics:")
    print(f"  Duration: {times[-1] - times[0]:.6f} seconds")
    print(f"  V max: {np.max(voltages):.4f} V")
    print(f"  V min: {np.min(voltages):.4f} V")
    print(f"  V p-p: {np.max(voltages) - np.min(voltages):.4f} V")
    print(f"  V avg: {np.mean(voltages):.4f} V")
    print(f"  V rms: {np.sqrt(np.mean(voltages**2)):.4f} V")

    return {
        'timestamp': capture_timestamp,
        'times': times,
        'voltages': voltages,
        'time_increment': x_increment,
        'total_points': len(voltages),
        'transfer_time': total_time
    }

def save_deep_memory_data(data, filename='deep_memory_capture.csv'):
    """Save captured deep memory data with timestamps"""

    print(f"\nSaving data to {filename}...")

    # Create timestamped samples
    rows = []
    base_time = data['timestamp']
    dt = data['time_increment']

    # For very large datasets, we'll save every Nth point for the CSV
    # and save the full data to a binary format
    total_points = len(data['voltages'])

    if total_points > 1000000:  # > 1M points
        print(f"  Large dataset ({total_points:,} points)")
        print(f"  Saving full binary data...")

        # Save full data as numpy binary
        np.savez_compressed(filename.replace('.csv', '.npz'),
                           times=data['times'],
                           voltages=data['voltages'],
                           timestamp=data['timestamp'].isoformat(),
                           time_increment=data['time_increment'])

        print(f"  Saved to: {filename.replace('.csv', '.npz')}")

        # Save decimated CSV for easier viewing
        decimation = total_points // 100000  # Target ~100K points for CSV
        print(f"  Saving decimated CSV (every {decimation}th point)...")

        for i in range(0, total_points, decimation):
            sample_time = base_time + timedelta(seconds=float(data['times'][i] - data['times'][0]))
            rows.append({
                'UTC_Timestamp': sample_time.isoformat(),
                'Time_Offset_s': data['times'][i],
                'Voltage_V': data['voltages'][i]
            })
    else:
        # Save all points
        print(f"  Saving all {total_points:,} points...")
        for i in range(total_points):
            sample_time = base_time + timedelta(seconds=float(data['times'][i] - data['times'][0]))
            rows.append({
                'UTC_Timestamp': sample_time.isoformat(),
                'Time_Offset_s': data['times'][i],
                'Voltage_V': data['voltages'][i]
            })

    df = pd.DataFrame(rows)
    df.to_csv(filename, index=False)

    file_size_mb = os.path.getsize(filename) / 1024 / 1024
    print(f"  CSV saved: {len(rows):,} rows ({file_size_mb:.2f} MB)")

def main():
    print("DS1054Z Deep Memory Capture Tool")
    print("="*70)

    scope = connect_scope()
    if not scope:
        print("ERROR: Could not connect to oscilloscope")
        return 1

    idn = scope.query('*IDN?').strip()
    print(f"Connected: {idn}\n")

    try:
        # Query current settings
        mdepth, srate = query_memory_depth(scope)

        # Set to maximum memory depth for this test
        # Options: 12000, 120000, 1200000, 12000000, 24000000
        set_memory_depth(scope, '120000')  # Start with 120K for faster testing

        # Capture deep memory (limit to 100K for initial test)
        data = capture_deep_memory(scope, channel=1, max_points=100000)

        # Save data
        save_deep_memory_data(data)

        print("\n" + "="*70)
        print("SUCCESS!")
        print("="*70)
        print(f"\nCaptured {data['total_points']:,} points in {data['transfer_time']:.1f}s")
        print(f"Effective rate: {data['total_points']/data['transfer_time']:,.0f} points/sec")

    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Restart acquisition
        scope.write(':RUN')
        scope.close()
        print("\nOscilloscope restarted, connection closed.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
