#!/usr/bin/env python3
"""
Continuous data capture from DS1054Z oscilloscope
Benchmarks transfer times and captures maximum data over specified duration
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta
import pandas as pd
import time

def connect_scope():
    """Connect to the oscilloscope"""
    dll_path = os.path.join(os.getcwd(), "libusb-1.0.dll")
    os.environ['PATH'] = os.getcwd() + os.pathsep + os.environ.get('PATH', '')

    import pyvisa

    print("Connecting to oscilloscope...")
    rm = pyvisa.ResourceManager('@py')

    resources = rm.list_resources()
    usb_resources = [r for r in resources if 'USB' in r and ('1AB1' in r.upper() or '6833' in r)]

    if not usb_resources:
        print("[ERROR] Oscilloscope not found")
        return None

    resource_str = usb_resources[0]
    scope = rm.open_resource(resource_str)
    scope.timeout = 30000  # 30 second timeout for large transfers

    print(f"[OK] Connected to: {resource_str}")
    idn = scope.query('*IDN?').strip()
    print(f"     {idn}")

    return scope

def get_memory_depth_info(scope):
    """Query oscilloscope memory depth settings"""
    print("\nQuerying memory depth settings...")

    try:
        # Check acquisition mode
        acq_type = scope.query(':ACQuire:TYPE?').strip()
        acq_mode = scope.query(':ACQuire:MODE?').strip()

        print(f"  Acquisition type: {acq_type}")
        print(f"  Acquisition mode: {acq_mode}")

        # Get memory depth (this might vary by model)
        try:
            mem_depth = scope.query(':ACQuire:MDEPth?').strip()
            print(f"  Memory depth: {mem_depth}")
        except:
            print(f"  Memory depth: (query not supported)")

        # Get sample rate
        try:
            sample_rate = float(scope.query(':ACQuire:SRATe?').strip())
            print(f"  Sample rate: {sample_rate/1e6:.2f} MSa/s")
        except:
            print(f"  Sample rate: (query not supported)")

    except Exception as e:
        print(f"  Error querying acquisition info: {e}")

def set_maximum_memory_depth(scope):
    """Set oscilloscope to maximum memory depth"""
    print("\nSetting maximum memory depth...")

    try:
        # Stop acquisition first
        scope.write(':STOP')
        time.sleep(0.1)

        # Try to set maximum memory depth
        # For DS1000Z series, options are typically: AUTO, 12000, 120000, 1200000, 12000000, 24000000
        scope.write(':ACQuire:MDEPth 24000000')  # Try 24M points
        time.sleep(0.1)

        # Verify
        mem_depth = scope.query(':ACQuire:MDEPth?').strip()
        print(f"  Memory depth set to: {mem_depth}")

        # Set to single trigger mode for full memory capture
        scope.write(':SINGle')

        return mem_depth

    except Exception as e:
        print(f"  Warning: Could not set memory depth - {e}")
        return None

def benchmark_transfer(scope, channel=1, num_points_list=[1200, 12000, 120000, 600000]):
    """Benchmark data transfer time for different memory depths"""

    print("\n" + "="*60)
    print("BENCHMARKING DATA TRANSFER RATES")
    print("="*60)

    results = []

    for num_points in num_points_list:
        try:
            print(f"\nTesting {num_points:,} points...")

            # Stop acquisition
            scope.write(':STOP')
            time.sleep(0.1)

            # Set memory depth if possible
            try:
                scope.write(f':ACQuire:MDEPth {num_points}')
                time.sleep(0.1)
            except:
                pass

            # Single trigger
            scope.write(':SINGle')
            time.sleep(0.5)  # Wait for trigger

            # Set waveform source
            scope.write(f':WAVeform:SOURce CHANnel{channel}')
            scope.write(':WAVeform:MODE NORMal')
            scope.write(':WAVeform:FORMat BYTE')

            # Get preamble
            preamble = scope.query(':WAVeform:PREamble?')
            preamble_values = [float(x) for x in preamble.split(',')]
            actual_points = int(preamble_values[2])

            print(f"  Actual points: {actual_points:,}")

            # Time the data transfer
            start_time = time.time()

            scope.write(':WAVeform:DATA?')
            raw_data = scope.read_raw()

            end_time = time.time()
            transfer_time = end_time - start_time

            # Calculate statistics
            data_size = len(raw_data)
            throughput_mbps = (data_size * 8) / transfer_time / 1e6
            points_per_sec = actual_points / transfer_time

            print(f"  Transfer time: {transfer_time:.3f} seconds")
            print(f"  Data size: {data_size:,} bytes ({data_size/1024:.1f} KB)")
            print(f"  Throughput: {throughput_mbps:.2f} Mbps")
            print(f"  Rate: {points_per_sec:,.0f} points/sec")

            results.append({
                'requested_points': num_points,
                'actual_points': actual_points,
                'data_size_bytes': data_size,
                'transfer_time_sec': transfer_time,
                'throughput_mbps': throughput_mbps,
                'points_per_sec': points_per_sec
            })

        except Exception as e:
            print(f"  Error: {e}")
            continue

    # Print summary
    print("\n" + "="*60)
    print("TRANSFER BENCHMARK SUMMARY")
    print("="*60)
    print(f"{'Points':<15} {'Time (s)':<12} {'Throughput':<15} {'Rate':<15}")
    print("-"*60)
    for r in results:
        print(f"{r['actual_points']:<15,} {r['transfer_time_sec']:<12.3f} "
              f"{r['throughput_mbps']:<15.2f} {r['points_per_sec']:<15,.0f}")

    return results

def continuous_capture(scope, duration_seconds=60, channel=1):
    """Capture data continuously for specified duration"""

    print("\n" + "="*60)
    print(f"CONTINUOUS CAPTURE - {duration_seconds} seconds")
    print("="*60)

    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(seconds=duration_seconds)

    all_data = []
    capture_count = 0
    total_points = 0

    print(f"\nStart time: {start_time.isoformat()}")
    print(f"End time:   {end_time.isoformat()}")
    print(f"Channel:    {channel}")
    print("\nStarting capture...")

    # Set up for continuous acquisition
    scope.write(f':WAVeform:SOURce CHANnel{channel}')
    scope.write(':WAVeform:MODE NORMal')
    scope.write(':WAVeform:FORMat BYTE')

    while datetime.now(timezone.utc) < end_time:
        try:
            capture_start = time.time()
            timestamp = datetime.now(timezone.utc)

            # Trigger single capture
            scope.write(':SINGle')
            time.sleep(0.05)  # Brief wait for trigger

            # Get preamble
            preamble = scope.query(':WAVeform:PREamble?')
            preamble_values = [float(x) for x in preamble.split(',')]

            points = int(preamble_values[2])
            x_increment = preamble_values[4]
            y_increment = preamble_values[7]
            y_origin = preamble_values[8]
            y_reference = preamble_values[9]

            # Get waveform data
            scope.write(':WAVeform:DATA?')
            raw_data = scope.read_raw()

            # Parse data
            header_len = 2 + int(chr(raw_data[1]))
            data = raw_data[header_len:-1]
            waveform_data = np.frombuffer(data, dtype=np.uint8)

            # Convert to voltages
            voltages = ((waveform_data - y_reference) * y_increment) + y_origin

            capture_end = time.time()
            capture_duration = capture_end - capture_start

            # Store capture info
            all_data.append({
                'capture_num': capture_count,
                'timestamp': timestamp,
                'unix_time': timestamp.timestamp(),
                'num_points': len(voltages),
                'capture_duration': capture_duration,
                'voltages': voltages,
                'time_increment': x_increment,
                'v_max': np.max(voltages),
                'v_min': np.min(voltages),
                'v_avg': np.mean(voltages)
            })

            capture_count += 1
            total_points += len(voltages)

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            remaining = duration_seconds - elapsed

            print(f"[{elapsed:5.1f}s] Capture #{capture_count}: {len(voltages):,} points "
                  f"in {capture_duration:.3f}s | Total: {total_points:,} | "
                  f"Remaining: {remaining:.1f}s")

            # Check if we should continue
            if datetime.now(timezone.utc) >= end_time:
                break

        except Exception as e:
            print(f"Error during capture: {e}")
            continue

    print(f"\n[COMPLETE] Captured {capture_count} waveforms, {total_points:,} total points")

    return all_data, start_time

def analyze_captures(all_data, start_time):
    """Analyze captured data for gaps and statistics"""

    print("\n" + "="*60)
    print("CAPTURE ANALYSIS")
    print("="*60)

    if len(all_data) == 0:
        print("No data captured!")
        return

    # Calculate time gaps between captures
    print(f"\nTotal captures: {len(all_data)}")
    print(f"Total points:   {sum(d['num_points'] for d in all_data):,}")

    # Check for missing data / gaps
    print("\nCapture timing:")
    for i in range(len(all_data)):
        if i > 0:
            time_gap = (all_data[i]['unix_time'] - all_data[i-1]['unix_time'])
            print(f"  Capture {i}: {time_gap:.3f}s gap from previous")

    # Overall statistics
    total_duration = all_data[-1]['unix_time'] - all_data[0]['unix_time']
    avg_capture_time = np.mean([d['capture_duration'] for d in all_data])
    total_points = sum(d['num_points'] for d in all_data)

    print(f"\nStatistics:")
    print(f"  Total duration:     {total_duration:.2f} seconds")
    print(f"  Avg capture time:   {avg_capture_time:.3f} seconds")
    print(f"  Captures per sec:   {len(all_data)/total_duration:.2f}")
    print(f"  Avg points/capture: {total_points/len(all_data):,.0f}")
    print(f"  Effective rate:     {total_points/total_duration:,.0f} points/sec")

def save_continuous_data(all_data, start_time, filename='continuous_capture.csv'):
    """Save all captured data to CSV with timestamps"""

    print(f"\nSaving data to {filename}...")

    rows = []

    for capture in all_data:
        capture_time = capture['timestamp']
        time_increment = capture['time_increment']

        for i, voltage in enumerate(capture['voltages']):
            sample_time = capture_time + timedelta(seconds=i * time_increment)

            rows.append({
                'UTC_Timestamp': sample_time.isoformat(),
                'Unix_Timestamp': sample_time.timestamp(),
                'Capture_Num': capture['capture_num'],
                'Sample_Index': i,
                'Voltage_V': voltage
            })

    df = pd.DataFrame(rows)
    df.to_csv(filename, index=False)

    print(f"[OK] Saved {len(rows):,} samples to {filename}")
    print(f"     File size: {os.path.getsize(filename)/1024/1024:.2f} MB")

    return filename

def plot_continuous_data(all_data, start_time):
    """Create visualization of continuous capture"""

    print("\nGenerating plots...")

    fig, axes = plt.subplots(3, 1, figsize=(14, 10))

    # Plot 1: All voltage data over time
    ax1 = axes[0]
    for capture in all_data:
        offset = (capture['timestamp'] - start_time).total_seconds()
        times = np.arange(len(capture['voltages'])) * capture['time_increment'] + offset
        ax1.plot(times, capture['voltages'], linewidth=0.3, alpha=0.7)

    ax1.set_xlabel('Time (seconds from start)')
    ax1.set_ylabel('Voltage (V)')
    ax1.set_title('Continuous Waveform Capture')
    ax1.grid(True, alpha=0.3)

    # Plot 2: Capture timing (gaps visualization)
    ax2 = axes[1]
    capture_times = [(d['timestamp'] - start_time).total_seconds() for d in all_data]
    capture_durations = [d['capture_duration'] for d in all_data]

    ax2.scatter(capture_times, capture_durations, s=20, alpha=0.6)
    ax2.set_xlabel('Time (seconds from start)')
    ax2.set_ylabel('Capture Duration (s)')
    ax2.set_title('Capture Timing (detecting gaps)')
    ax2.grid(True, alpha=0.3)

    # Plot 3: Voltage statistics over time
    ax3 = axes[2]
    v_max = [d['v_max'] for d in all_data]
    v_min = [d['v_min'] for d in all_data]
    v_avg = [d['v_avg'] for d in all_data]

    ax3.plot(capture_times, v_max, 'r-', label='Max', linewidth=1.5)
    ax3.plot(capture_times, v_min, 'b-', label='Min', linewidth=1.5)
    ax3.plot(capture_times, v_avg, 'g-', label='Avg', linewidth=1.5)
    ax3.set_xlabel('Time (seconds from start)')
    ax3.set_ylabel('Voltage (V)')
    ax3.set_title('Voltage Statistics Over Time')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()

    filename = 'continuous_capture_plot.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"[OK] Plot saved to: {filename}")

    plt.close()

def main():
    print("="*60)
    print("DS1054Z CONTINUOUS DATA CAPTURE & BENCHMARK")
    print("="*60)

    # Connect
    scope = connect_scope()
    if not scope:
        return 1

    try:
        # Get memory info
        get_memory_depth_info(scope)

        # Benchmark transfer rates
        print("\nRunning transfer benchmarks...")
        benchmark_results = benchmark_transfer(scope, channel=1)

        # Run continuous capture for 60 seconds
        print("\nStarting 60-second continuous capture in 3 seconds...")
        time.sleep(3)

        all_data, start_time = continuous_capture(scope, duration_seconds=60, channel=1)

        # Analyze
        analyze_captures(all_data, start_time)

        # Save data
        csv_file = save_continuous_data(all_data, start_time)

        # Plot
        plot_continuous_data(all_data, start_time)

        print("\n" + "="*60)
        print("[SUCCESS] Continuous capture complete!")
        print("="*60)

    except KeyboardInterrupt:
        print("\n\nCapture interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        scope.close()
        print("\nConnection closed.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
