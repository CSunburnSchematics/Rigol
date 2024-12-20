import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import subprocess
import os
import shutil
import datetime
import cv2

# Function to capture webcam images
def capture_two_webcam_images(output_path1, output_path2):
    webcam = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    if not webcam.isOpened():
        messagebox.showerror("Error", "Unable to access the webcam.")
        return

    ret, frame = webcam.read()
    if ret:
        cv2.imwrite(output_path1, frame)
    else:
        messagebox.showerror("Error", "Unable to capture image.")
        return

    ret, frame = webcam.read()
    if ret:
        cv2.imwrite(output_path2, frame)
    else:
        messagebox.showerror("Error", "Unable to capture image.")
    webcam.release()

# Run Test
def run_test_gui():
    global current_test_list, voltage_test_list, test_setup_name, notes, dwell_time, current_limit, power_supply
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    test_folder = f"Test_{test_setup_name.get().replace(' ', '_')}_{timestamp}"
    os.makedirs(test_folder, exist_ok=True)

    webcam_image_path_1 = os.path.join(test_folder, "webcam_image_1.png")
    webcam_image_path_2 = os.path.join(test_folder, "webcam_image_2.png")
    capture_two_webcam_images(webcam_image_path_1, webcam_image_path_2)

    subprocess.run([
        "python", "main.py",
        f"--current_list={current_test_list.get()}",
        f"--test_setup_name={test_setup_name.get()}",
        f"--voltage_list={voltage_test_list.get()}",
        f"--dwell_time={dwell_time.get()}",
        f"--input_current_limit={current_limit.get()}",
        f"--power_supply={power_supply.get()}",
        f"--test_folder={test_folder}"
    ], check=True)

    messagebox.showinfo("Success", f"Test completed! Results saved in: {test_folder}")

# GUI Setup
root = tk.Tk()
root.title("Test Runner Configuration")

# Variables
test_setup_name = tk.StringVar(value="#9")
notes = tk.StringVar(value="465khz N49 8:8 106 uH 1oz R1:15k R6:18k R9:62k R8:1.2k R7:1.2k")
current_test_list = tk.StringVar(value="0.0, 0.25, 0.5, 1, 2, 4, 8.4")
voltage_test_list = tk.StringVar(value="36, 50.5, 60")
dwell_time = tk.IntVar(value=2)
current_limit = tk.IntVar(value=5)
power_supply = tk.StringVar(value="korad")

# GUI Layout
tk.Label(root, text="Test Setup Name:").grid(row=0, column=0, sticky="w")
tk.Entry(root, textvariable=test_setup_name, width=40).grid(row=0, column=1)

tk.Label(root, text="Notes:").grid(row=1, column=0, sticky="w")
tk.Entry(root, textvariable=notes, width=40).grid(row=1, column=1)

tk.Label(root, text="Current Test List (comma-separated):").grid(row=2, column=0, sticky="w")
tk.Entry(root, textvariable=current_test_list, width=40).grid(row=2, column=1)

tk.Label(root, text="Voltage Test List (comma-separated):").grid(row=3, column=0, sticky="w")
tk.Entry(root, textvariable=voltage_test_list, width=40).grid(row=3, column=1)

tk.Label(root, text="Dwell Time (s):").grid(row=4, column=0, sticky="w")
tk.Entry(root, textvariable=dwell_time, width=40).grid(row=4, column=1)

tk.Label(root, text="Input Current Limit (A):").grid(row=5, column=0, sticky="w")
tk.Entry(root, textvariable=current_limit, width=40).grid(row=5, column=1)

tk.Label(root, text="Power Supply:").grid(row=6, column=0, sticky="w")
power_supply_menu = ttk.Combobox(root, textvariable=power_supply, values=["korad", "rigol"], state="readonly")
power_supply_menu.grid(row=6, column=1)

# Run Button
tk.Button(root, text="Run Test", command=run_test_gui, bg="green", fg="white").grid(row=7, column=0, columnspan=2, pady=10)

root.mainloop()
