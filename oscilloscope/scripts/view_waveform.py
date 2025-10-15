#!/usr/bin/env python3
"""
View waveform data from CSV file with interactive plotting
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone
import pandas as pd

def view_csv_waveform(csv_file='waveform_ch1.csv'):
    """Load and plot waveform data from CSV"""

    print(f"Loading waveform data from: {csv_file}")

    # Load CSV data
    data = np.loadtxt(csv_file, delimiter=',', skiprows=1)
    times = data[:, 0]
    voltages = data[:, 1]

    print(f"Loaded {len(times)} data points")

    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

    # Plot 1: Time vs Voltage
    ax1.plot(times * 1e6, voltages, linewidth=0.8, color='blue')
    ax1.set_xlabel('Time (μs)', fontsize=11)
    ax1.set_ylabel('Voltage (V)', fontsize=11)
    ax1.set_title('Oscilloscope Waveform - Channel 1', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3, linestyle='--')

    # Add statistics box
    v_max = np.max(voltages)
    v_min = np.min(voltages)
    v_pp = v_max - v_min
    v_avg = np.mean(voltages)
    v_rms = np.sqrt(np.mean(voltages**2))

    stats_text = f'Statistics:\n'
    stats_text += f'Vmax: {v_max:.4f} V\n'
    stats_text += f'Vmin: {v_min:.4f} V\n'
    stats_text += f'Vpp:  {v_pp:.4f} V\n'
    stats_text += f'Vavg: {v_avg:.4f} V\n'
    stats_text += f'Vrms: {v_rms:.4f} V'

    ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes,
             verticalalignment='top', fontsize=9,
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    # Plot 2: Voltage histogram
    ax2.hist(voltages, bins=50, color='green', alpha=0.7, edgecolor='black')
    ax2.set_xlabel('Voltage (V)', fontsize=11)
    ax2.set_ylabel('Count', fontsize=11)
    ax2.set_title('Voltage Distribution', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, linestyle='--', axis='y')

    plt.tight_layout()

    # Save the plot
    output_file = csv_file.replace('.csv', '_plot.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {output_file}")

    # Close instead of showing (for CLI use)
    plt.close()

def add_timestamps_to_csv(csv_file='waveform_ch1.csv', output_file='waveform_ch1_timestamped.csv'):
    """Add UTC timestamps to waveform CSV"""

    print(f"\nAdding UTC timestamps to: {csv_file}")

    # Get current UTC time as the capture time
    capture_time = datetime.now(timezone.utc)
    print(f"Using capture time: {capture_time.isoformat()}")

    # Load existing CSV data
    data = np.loadtxt(csv_file, delimiter=',', skiprows=1)
    times = data[:, 0]
    voltages = data[:, 1]

    # Create timestamps for each sample
    # Each sample is offset from the capture time by its time value
    timestamps = []
    iso_timestamps = []

    for t in times:
        # Create timestamp by adding the time offset to capture time
        from datetime import timedelta
        sample_time = capture_time + timedelta(seconds=float(t))
        timestamps.append(sample_time.timestamp())  # Unix timestamp
        iso_timestamps.append(sample_time.isoformat())  # ISO 8601 format

    # Create DataFrame for easy CSV writing
    df = pd.DataFrame({
        'UTC_Timestamp': iso_timestamps,
        'Unix_Timestamp': timestamps,
        'Time_Offset_s': times,
        'Voltage_V': voltages
    })

    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"Timestamped data saved to: {output_file}")
    print(f"  Format: UTC_Timestamp, Unix_Timestamp, Time_Offset_s, Voltage_V")
    print(f"  Rows: {len(df)}")

    # Show first few rows
    print("\nFirst 5 rows:")
    print(df.head())

    return output_file

def plot_timestamped_waveform(csv_file='waveform_ch1_timestamped.csv'):
    """Plot waveform with real timestamps on x-axis"""

    print(f"\nPlotting timestamped waveform from: {csv_file}")

    # Load timestamped CSV
    df = pd.read_csv(csv_file)

    # Convert UTC timestamps to datetime objects
    df['DateTime'] = pd.to_datetime(df['UTC_Timestamp'])

    # Create plot
    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(df['DateTime'], df['Voltage_V'], linewidth=0.8, color='purple')
    ax.set_xlabel('UTC Time', fontsize=11)
    ax.set_ylabel('Voltage (V)', fontsize=11)
    ax.set_title('Oscilloscope Waveform with UTC Timestamps', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45, ha='right')

    plt.tight_layout()

    # Save plot
    output_file = csv_file.replace('.csv', '_plot.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Timestamped plot saved to: {output_file}")

    # Close instead of showing (for CLI use)
    plt.close()

def main():
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        csv_file = 'waveform_ch1.csv'

    print("Waveform Viewer and Timestamp Tool")
    print("=" * 60)

    # Check if file exists
    import os
    if not os.path.exists(csv_file):
        print(f"[ERROR] File not found: {csv_file}")
        return 1

    # View the original waveform
    print("\n[1/3] Viewing original waveform...")
    view_csv_waveform(csv_file)

    # Add timestamps
    print("\n[2/3] Adding timestamps...")
    timestamped_file = add_timestamps_to_csv(csv_file)

    # Plot timestamped version
    print("\n[3/3] Creating timestamped plot...")
    plot_timestamped_waveform(timestamped_file)

    print("\n" + "=" * 60)
    print("[SUCCESS] Complete!")
    print(f"\nGenerated files:")
    print(f"  - {csv_file.replace('.csv', '_plot.png')}")
    print(f"  - {timestamped_file}")
    print(f"  - {timestamped_file.replace('.csv', '_plot.png')}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
