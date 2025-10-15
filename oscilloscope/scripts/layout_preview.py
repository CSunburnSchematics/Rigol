#!/usr/bin/env python3
"""
Layout Preview - Shows the 16-channel display layout without hardware
"""

import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

def main():
    print("Showing layout preview...")

    # Set background color
    plt.rcParams['figure.facecolor'] = '#f5f3ef'
    plt.rcParams['axes.facecolor'] = '#f5f3ef'
    plt.rcParams['text.color'] = 'black'
    plt.rcParams['axes.labelcolor'] = 'black'
    plt.rcParams['xtick.color'] = 'black'
    plt.rcParams['ytick.color'] = 'black'

    fig = plt.figure(figsize=(28, 20))
    fig.canvas.manager.set_window_title('16-Channel Multi-Scope Capture - Layout Preview')

    # Layout matching the actual script
    gs = GridSpec(16, 4, figure=fig, hspace=0.8, wspace=0.25,
                  width_ratios=[3.5, 3.0, 1.0, 0.4])

    # Simulate 4 scopes
    num_scopes = 4

    # Mock channel names
    mock_channel_names = [
        {1: '21_DRVB', 2: '21_DRVA', 3: '23_DRVB', 4: '23_DRVA'},
        {1: 'AMC1311', 2: 'ADUM4195', 3: 'LT4430', 4: 'LT1431'},
        {1: '22_OUTD', 2: '22_OUTC', 3: '22_OUTB', 4: '22_OUTA'},
        {1: '23_SDRA', 2: '23_SDRB', 3: '22_OUTF', 4: '22_OUTE'}
    ]

    colors = ['blue', 'orange', 'green', 'red']

    # Create axes lists
    main_axes = []
    detail_axes = []
    hist_axes = []
    stats_axes = []

    # Main timeline plots - Column 0, all 16 channels stacked
    for ch_idx in range(16):
        ax = fig.add_subplot(gs[ch_idx, 0])
        main_axes.append(ax)

    # Detail waveform plots - Column 1, all 16 channels stacked
    for scope_idx in range(num_scopes):
        scope_detail_axes = []
        for ch_idx in range(4):
            row = scope_idx * 4 + ch_idx
            ax = fig.add_subplot(gs[row, 1])
            scope_detail_axes.append(ax)
        detail_axes.append(scope_detail_axes)

    # Histograms - Column 2, 4 scopes stacked (4 rows each)
    for scope_idx in range(num_scopes):
        start_row = scope_idx * 4
        end_row = start_row + 4
        hist_ax = fig.add_subplot(gs[start_row:end_row, 2])
        hist_axes.append(hist_ax)

    # Stats panels - Column 3, 4 scopes stacked (4 rows each)
    for scope_idx in range(num_scopes):
        start_row = scope_idx * 4
        end_row = start_row + 4
        stats_ax = fig.add_subplot(gs[start_row:end_row, 3])
        stats_ax.axis('off')
        stats_axes.append(stats_ax)

    # Populate with sample data
    # Main timeline plots
    for ch_global in range(16):
        scope_idx = ch_global // 4
        ch_idx = ch_global % 4
        ax = main_axes[ch_global]

        # Generate sample data
        t = np.linspace(0, 5, 1000)
        data = np.sin(2 * np.pi * (ch_global + 1) * 0.5 * t) * (ch_global + 1) * 0.5
        ax.scatter(t, data, c=colors[ch_idx], s=1)

        ch_name = mock_channel_names[scope_idx].get(ch_idx+1, f'CH{ch_idx+1}')
        ch_name = ch_name[:8] if len(ch_name) > 8 else ch_name
        ax.set_ylabel(f'S{scope_idx+1}\n{ch_name}\n(V)', fontsize=5, labelpad=8)
        if ch_global == 15:
            ax.set_xlabel('Time (s)', fontsize=6)
        else:
            ax.set_xticklabels([])

        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=6)

    # Detail plots
    for scope_idx in range(num_scopes):
        for ch_idx in range(4):
            ax = detail_axes[scope_idx][ch_idx]

            # Plot multiple overlaid waveforms
            for i in range(10):
                samples = np.arange(100)
                data = np.sin(2 * np.pi * samples / 50 + i * 0.5) + np.random.randn(100) * 0.1
                alpha = 0.3 + (i / 10) * 0.7
                ax.plot(samples, data, color=colors[ch_idx], alpha=alpha, linewidth=0.8)

            ch_name = mock_channel_names[scope_idx].get(ch_idx+1, f'CH{ch_idx+1}')
            ch_name = ch_name[:8] if len(ch_name) > 8 else ch_name
            ax.set_ylabel(f'S{scope_idx+1} {ch_name}\n(V)', fontsize=5, labelpad=8)

            if scope_idx == num_scopes - 1 and ch_idx == 3:
                ax.set_xlabel('Sample', fontsize=6)
            else:
                ax.set_xticklabels([])

            if scope_idx == 0 and ch_idx == 0:
                ax.set_title('Last 10 Waveforms', fontsize=8, fontweight='bold', color='#fcb911')

            ax.grid(True, alpha=0.3)
            ax.tick_params(labelsize=6)

    # Histograms
    for scope_idx in range(num_scopes):
        ax = hist_axes[scope_idx]

        # Generate sample histogram data
        data = np.random.randn(1000) * (scope_idx + 1) * 0.5
        ax.hist(data, bins=50, color='purple', alpha=0.7, edgecolor='black')

        ax.set_title(f'Scope {scope_idx+1}\nVoltage Dist', fontsize=8, fontweight='bold', color='#fcb911')

        if scope_idx == num_scopes - 1:
            ax.set_xlabel('Voltage (V)', fontsize=6)
        else:
            ax.set_xticklabels([])

        ax.set_ylabel('Count', fontsize=6)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=6)

    # Stats text
    for scope_idx in range(num_scopes):
        ax = stats_axes[scope_idx]

        stats_str = (f"S{scope_idx+1}\n"
                    f"DS1ZA273M0\n"
                    f"Rate:\n4.5c/s\n"
                    f"Cov:\n2.7%\n"
                    f"Caps:\n620\n"
                    f"Time:\n138s\n"
                    f"Drop:\n0\n"
                    f"Err:\n0")

        ax.text(0.02, 0.98, stats_str, transform=ax.transAxes,
               fontsize=5, verticalalignment='top')

    plt.subplots_adjust(top=0.995, bottom=0.03, left=0.04, right=0.99)

    print("Layout preview displayed. Close window to exit.")
    plt.show()

if __name__ == "__main__":
    main()
