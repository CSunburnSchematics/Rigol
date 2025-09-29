import shutil
import pyvisa
import datetime
import time
import csv
import os
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")  # safe even on headless machines; remove if you want a window
import matplotlib.pyplot as plt
from Rigol_DS1054z import RigolOscilloscope


OSCILLOSCOPE_ADDRESS = "USB0::0x1AB1::0x04CE::DS1ZA172215665::INSTR"

rm = pyvisa.ResourceManager()

oscilloscope = RigolOscilloscope(OSCILLOSCOPE_ADDRESS)

oscilloscope.check_connection()

oscilloscope.instrument.write(":ACQ:MDEP 1200000")   # 1.2 Mpts
print("Memory depth:", oscilloscope.instrument.query(":ACQ:MDEP?"))
print("Sample rate:", oscilloscope.instrument.query(":ACQ:SRAT?"))

# or


#oscilloscope.trigger_single()
time.sleep(1)
#oscilloscope.capture_screenshot("osc_3_test_pic.png")
#put this in a file outside of repo!
#oscilloscope.trigger_run()

#oscilloscope.close()
# #oscilloscope. #... turn off function?


def save_csv(csv_path: str, t: np.ndarray, v: np.ndarray):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True) if os.path.dirname(csv_path) else None
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_s", "volts"])
        w.writerows(zip(t, v))

def save_png(png_path: str, t: np.ndarray, v: np.ndarray, title: str):
    os.makedirs(os.path.dirname(png_path), exist_ok=True) if os.path.dirname(png_path) else None
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t, v, linewidth=0.8)  # plot ALL points
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Voltage (V)")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(png_path, dpi=150)
    plt.close(fig)

   

def capture_csv_and_plot(scope,
                         channel=1,
                         window_s=500e-6,
                         shots=1,
                         out_dir="captures_500us",
                         prefix="shot",
                         zero_time_at_start=True):
    """
    For each shot:
      - capture window from scope
      - write CSV (time_s, volts)
      - write PNG plotting ALL points
    """
    for i in range(1, shots + 1):
        # 1) capture from scope (all points, already scaled)
        t, v, pre = scope.capture_window_on_demand(channel=channel, window_s=window_s)
        
        # Optional: shift time axis to start at 0 for nicer plots/CSVs
        if zero_time_at_start:
            t = t - t[0]

        # 2) save CSV
        csv_path = os.path.join(out_dir, f"{prefix}_{i:03d}.csv")
        save_csv(csv_path, t, v)

        # 3) save PNG (static)
        title = f"Capture {i}/{shots} — points={pre['points']}, Δt={pre['xinc']:.3e}s"
        png_path = os.path.join(out_dir, f"{prefix}_{i:03d}.png")
        save_png(png_path, t, v, title)

        print(f"[OK] {csv_path}  |  {png_path}") 


# Example usage after you’ve created/connected your scope instance:
# scope = RigolOscilloscope("USB0::0x1AB1::0x04CE::DS1ZAxxxxxxx::INSTR")

capture_csv_and_plot(oscilloscope, 
                     channel=1,
                     window_s=500e-6,
                     shots=1,
                     out_dir="captures_500us",
                     prefix="win")
