import shutil
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import subprocess
import os
import json
import datetime
import cv2
import time

SETTINGS_FILE = "test_settings.json"

def validate_inputs():
    """
    Validate all user inputs.
    """
    errors = []

    # Reset error highlighting (if any)
    save_folder_entry.config(bg="white")

    # Check if save folder exists
    if not os.path.exists(save_folder.get()):
        errors.append(f"Save folder does not exist: {save_folder.get()}")
        save_folder_entry.config(bg="pink")  # Highlight save folder field

    # Check if current_test_list is in correct format
    try:
        [float(x) for x in current_test_list.get().split(",")]
    except ValueError:
        errors.append("Current Test List must be a comma-separated list of numbers (e.g., 0.0, 0.25, 1).")

    # Check if voltage_test_list is in correct format
    try:
        [float(x) for x in voltage_test_list.get().split(",")]
    except ValueError:
        errors.append("Voltage Test List must be a comma-separated list of numbers (e.g., 36, 50.5, 60).")

    # Check if dwell_time is positive
    if dwell_time.get() <= 0:
        errors.append("Dwell Time must be a positive number.")

    # Check if current_limit is within acceptable range
    if current_limit.get() <= 0:
        errors.append("Input Current Limit must be a positive number.")

    return errors

# Function to load saved settings
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {
        "test_setup_name": "#9",
        "notes": "465khz N49 8:8 106 uH 1oz R1:15k R6:18k R9:62k R8:1.2k R7:1.2k",
        "current_test_list": "0.0, 0.25, 0.5, 1, 2, 4, 8.4",
        "voltage_test_list": "36, 50.5, 60",
        "dwell_time": 2,
        "current_limit": 5,
        "power_supply": "korad",
        "osc_1_channels": {
            "ch_1": "Preactive Fet Gate",
            "ch_2": "Main Fet Gate",
            "ch_3": "Forward Fet Gate",
            "ch_4": "Catch Fet Gate"
        },
        "osc_2_channels": {
            "ch_1": "Preactive Fet VDS",
            "ch_2": "Main Fet VDS",
            "ch_3": "Forward Fet VDS",
            "ch_4": "Catch Fet VDS"
        },
        "osc_3_channels": {
            "ch_1": "TBD",
            "ch_2": "TBD",
            "ch_3": "TBD",
            "ch_4": "TBD"
        },
        "osc_measurements": {
            "osc_1": {"ch_1": {"measurement": "VMax", "make_negative": False}, 
                      "ch_2": {"measurement": "VMax", "make_negative": False}, 
                      "ch_3": {"measurement": "VMax", "make_negative": False},
                      "ch_4": {"measurement": "VMax", "make_negative": False}},
            "osc_2": {"ch_1": {"measurement": "VMax", "make_negative": False}, 
                      "ch_2": {"measurement": "VMax", "make_negative": False}, 
                      "ch_3": {"measurement": "VMax", "make_negative": False},
                      "ch_4": {"measurement": "VMax", "make_negative": False}},
            "osc_3": {"ch_1": {"measurement": "VMax", "make_negative": False}, 
                      "ch_2": {"measurement": "VMax", "make_negative": False}, 
                      "ch_3": {"measurement": "VMax", "make_negative": False},
                      "ch_4": {"measurement": "VMax", "make_negative": False}}
        },
        "save_folder": "I:\\Shared drives\\Sunburn Schematics\\Clients\\Relativity Space\\Testing"
    }




# Function to save settings
def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)


def capture_two_webcam_images(output_path1, output_path2):
    # Ensure the output paths include valid image extensions
    if not output_path1.lower().endswith((".png", ".jpg", ".jpeg")):
        output_path1 += ".png"  # Default to PNG for the first image
    if not output_path2.lower().endswith((".png", ".jpg", ".jpeg")):
        output_path2 += ".png"  # Default to PNG for the second image

    # Initialize webcam with timing
    start_time = time.time()
    WEBCAM_NUMBER = 1
    webcam = cv2.VideoCapture(WEBCAM_NUMBER, cv2.CAP_DSHOW)
    if not webcam.isOpened():
        print("Error: Unable to access the webcam.")
        return
    print(f"Webcam initialized in {time.time() - start_time:.2f} seconds.")

   
    webcam.set(cv2.CAP_PROP_FPS, 15)

    print("Press 'Spacebar' to capture an image, and 'Q' to quit.")

    images_captured = 0  # Counter for captured images

    while images_captured < 2:
        ret, frame = webcam.read()
        if not ret:
            print("Error: Unable to read from the webcam.")
            break

        # Display the webcam feed
        cv2.imshow("Press Spacebar to Capture", frame)

        # Wait for user input
        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):  # Spacebar pressed
            if images_captured == 0:
                cv2.imwrite(output_path1, frame)
                print(f"First image captured and saved to {output_path1}")
                images_captured += 1
            elif images_captured == 1:
                cv2.imwrite(output_path2, frame)
                print(f"Second image captured and saved to {output_path2}")
                images_captured += 1
        elif key == ord('q'):  # 'Q' pressed to quit without completing
            print("Image capture aborted by user.")
            break

    # Release resources and close the window
    webcam.release()
    cv2.destroyAllWindows()

def update_current_limit_note(*args):
    if power_supply.get() == "korad":
        current_limit_note.set("Note: For Korad, the maximum current limit is 5A.")
    elif power_supply.get() == "rigol":
        current_limit_note.set("Note: For Rigol, the maximum current limit is 3.2A.")
    else:
        current_limit_note.set("")

def run_dashboard(test_folder):
    subprocess.run([
        "python", "dashboard.py",
        test_folder,
        test_setup_name.get().replace(" ", "_"),
        notes.get().replace(" ", "_"),
        *[osc_1_channels[key].get().replace(" ", "_") for key in osc_1_channels],
        *[osc_2_channels[key].get().replace(" ", "_") for key in osc_2_channels],
        *[osc_3_channels[key].get().replace(" ", "_") for key in osc_3_channels],
        save_folder.get()
    ], check=True)

# Function to run the test
def run_test_gui():
    global current_test_list, voltage_test_list, test_setup_name, notes, dwell_time, current_limit, power_supply, osc_1_channels, osc_2_channels, osc_3_channels, osc_measurement_options, save_folder

    errors = validate_inputs()
    if errors:
        messagebox.showerror("Validation Error", "\n".join(errors))
        return

    if not confirm_details():
        return

    root.destroy()

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    test_folder = f"Test_{test_setup_name.get().replace(' ', '_')}_{timestamp}"
    os.makedirs(test_folder, exist_ok=True)

    webcam_image_path_1 = os.path.join(test_folder, "webcam_image_1.png")
    webcam_image_path_2 = os.path.join(test_folder, "webcam_image_2.png")
    capture_two_webcam_images(webcam_image_path_1, webcam_image_path_2)

    osc_measurements = {
        "osc_1": {
            key: {
                "measurement": var["measurement"].get(),
                "make_negative": var["make_negative"].get()
            }
            for key, var in osc_channel_settings["osc_1"].items()
        },
        "osc_2": {
            key: {
                "measurement": var["measurement"].get(),
                "make_negative": var["make_negative"].get()
            }
            for key, var in osc_channel_settings["osc_2"].items()
        },
        "osc_3": {
            key: {
                "measurement": var["measurement"].get(),
                "make_negative": var["make_negative"].get()
            }
            for key, var in osc_channel_settings["osc_3"].items()
        },
    }
    osc_measurements_json = json.dumps(osc_measurements)  # Serialize the dictionary to JSON

    subprocess.run([
        "python", "main.py",
        f"--current_list={current_test_list.get()}",
        f"--test_setup_name={test_setup_name.get()}",
        f"--voltage_list={voltage_test_list.get()}",
        f"--dwell_time={dwell_time.get()}",
        f"--input_current_limit={current_limit.get()}",
        f"--power_supply={power_supply.get()}",
        f"--osc_measurements={osc_measurements_json}",  # Pass JSON string as argument
        f"--test_folder={test_folder}"
    ], check=True)

    save_settings({
        "test_setup_name": test_setup_name.get(),
        "notes": notes.get(),
        "current_test_list": current_test_list.get(),
        "voltage_test_list": voltage_test_list.get(),
        "dwell_time": dwell_time.get(),
        "current_limit": current_limit.get(),
        "power_supply": power_supply.get(),
        "osc_1_channels": {key: var.get() for key, var in osc_1_channels.items()},
        "osc_2_channels": {key: var.get() for key, var in osc_2_channels.items()},
        "osc_3_channels": {key: var.get() for key, var in osc_3_channels.items()},
        "osc_measurements": {
                            "osc_1": {
                                key: {
                                    "measurement": var["measurement"].get(),
                                    "make_negative": var["make_negative"].get()
                                }
                                for key, var in osc_channel_settings["osc_1"].items()
                            },
                            "osc_2": {
                                key: {
                                    "measurement": var["measurement"].get(),
                                    "make_negative": var["make_negative"].get()
                                }
                                for key, var in osc_channel_settings["osc_2"].items()
                            },
                            "osc_3": {
                                key: {
                                    "measurement": var["measurement"].get(),
                                    "make_negative": var["make_negative"].get()
                                }
                                for key, var in osc_channel_settings["osc_3"].items()
                            },
                        },


        "save_folder": save_folder.get()
    })

    run_dashboard(test_folder)

# Confirmation dialog
def confirm_details():
    return messagebox.askyesno(
        "Confirm Details",
        f"Are the following details correct?\n\n"
        f"Test Setup Name: {test_setup_name.get()}\n"
        f"Notes: {notes.get()}\n"
        f"Save Folder: {save_folder.get()}"
    )

# GUI Setup
root = tk.Tk()
root.geometry("600x600")
root.title("Test Runner Configuration")

# Create a notebook (tabbed interface)
notebook = ttk.Notebook(root)

# Tab 1: Main Configuration
main_frame = ttk.Frame(notebook)

notebook.add(main_frame, text="Main Configuration")

# Tab 2: Oscilloscope Settings
osc_frame = ttk.Frame(notebook)
osc_frame.grid_rowconfigure(0, weight=1)
osc_frame.grid_columnconfigure(0, weight=1)
notebook.add(osc_frame, text="Oscilloscope Settings")

notebook.pack(expand=True, fill="both")

# Load saved settings
settings = load_settings()

# Variables
current_limit_note = tk.StringVar()
test_setup_name = tk.StringVar(value=settings["test_setup_name"])
notes = tk.StringVar(value=settings["notes"])
current_test_list = tk.StringVar(value=settings["current_test_list"])
voltage_test_list = tk.StringVar(value=settings["voltage_test_list"])
dwell_time = tk.IntVar(value=settings["dwell_time"])
current_limit = tk.DoubleVar(value=settings["current_limit"])
power_supply = tk.StringVar(value=settings["power_supply"])
update_current_limit_note()
power_supply.trace_add("write", update_current_limit_note)

osc_1_channels = {key: tk.StringVar(value=value) for key, value in settings["osc_1_channels"].items()}
osc_2_channels = {key: tk.StringVar(value=value) for key, value in settings["osc_2_channels"].items()}
osc_3_channels = {key: tk.StringVar(value=value) for key, value in settings["osc_3_channels"].items()}

osc_measurement_options = ["VMax", "VMin", "None"]


# Initialize osc_channel_settings with loaded values
osc_channel_settings = {
    "osc_1": {
        key: {
            "measurement": tk.StringVar(value=settings["osc_measurements"]["osc_1"][key]["measurement"]),
            "make_negative": tk.BooleanVar(value=settings["osc_measurements"]["osc_1"][key]["make_negative"]),
        }
        for key in settings["osc_measurements"]["osc_1"]
    },
    "osc_2": {
        key: {
            "measurement": tk.StringVar(value=settings["osc_measurements"]["osc_2"][key]["measurement"]),
            "make_negative": tk.BooleanVar(value=settings["osc_measurements"]["osc_2"][key]["make_negative"]),
        }
        for key in settings["osc_measurements"]["osc_2"]
    },
    "osc_3": {
        key: {
            "measurement": tk.StringVar(value=settings["osc_measurements"]["osc_3"][key]["measurement"]),
            "make_negative": tk.BooleanVar(value=settings["osc_measurements"]["osc_3"][key]["make_negative"]),
        }
        for key in settings["osc_measurements"]["osc_3"]
    },
}



save_folder = tk.StringVar(value=settings["save_folder"])

# GUI Layout
tk.Label(main_frame, text="Test Setup Name:").grid(row=0, column=0, sticky="w")
tk.Entry(main_frame, textvariable=test_setup_name, width=40).grid(row=0, column=1)

tk.Label(main_frame, text="Notes:").grid(row=1, column=0, sticky="w")
tk.Entry(main_frame, textvariable=notes, width=40).grid(row=1, column=1)

tk.Label(main_frame, text="Current Test List (comma-separated):").grid(row=2, column=0, sticky="w")
tk.Entry(main_frame, textvariable=current_test_list, width=40).grid(row=2, column=1)

tk.Label(main_frame, text="Voltage Test List (comma-separated):").grid(row=3, column=0, sticky="w")
tk.Entry(main_frame, textvariable=voltage_test_list, width=40).grid(row=3, column=1)

tk.Label(main_frame, text="Dwell Time (s):").grid(row=4, column=0, sticky="w")
tk.Entry(main_frame, textvariable=dwell_time, width=40).grid(row=4, column=1)

tk.Label(main_frame, text="Input Current Limit (A):").grid(row=5, column=0, sticky="w")
tk.Entry(main_frame, textvariable=current_limit, width=40).grid(row=5, column=1)

tk.Label(main_frame, textvariable=current_limit_note, fg="blue").grid(row=6, column=0, columnspan=2, sticky="w")

tk.Label(main_frame, text="Power Supply:").grid(row=7, column=0, sticky="w")
power_supply_menu = ttk.Combobox(main_frame, textvariable=power_supply, values=["korad", "rigol"], state="readonly")
power_supply_menu.grid(row=7, column=1)

tk.Label(main_frame, text="Oscilloscope 1 Channel Labels:").grid(row=8, column=0, columnspan=2, sticky="w")
tk.Label(main_frame, text="Ch 1:").grid(row=9, column=0, sticky="w")
tk.Entry(main_frame, textvariable=osc_1_channels["ch_1"], width=40).grid(row=9, column=1)

tk.Label(main_frame, text="Ch 2:").grid(row=10, column=0, sticky="w")
tk.Entry(main_frame, textvariable=osc_1_channels["ch_2"], width=40).grid(row=10, column=1)

tk.Label(main_frame, text="Ch 3:").grid(row=11, column=0, sticky="w")
tk.Entry(main_frame, textvariable=osc_1_channels["ch_3"], width=40).grid(row=11, column=1)

tk.Label(main_frame, text="Ch 4:").grid(row=12, column=0, sticky="w")
tk.Entry(main_frame, textvariable=osc_1_channels["ch_4"], width=40).grid(row=12, column=1)

tk.Label(main_frame, text="Oscilloscope 2 Channel Labels:").grid(row=13, column=0, columnspan=2, sticky="w")
tk.Label(main_frame, text="Ch 1:").grid(row=14, column=0, sticky="w")
tk.Entry(main_frame, textvariable=osc_2_channels["ch_1"], width=40).grid(row=14, column=1)

tk.Label(main_frame, text="Ch 2:").grid(row=15, column=0, sticky="w")
tk.Entry(main_frame, textvariable=osc_2_channels["ch_2"], width=40).grid(row=15, column=1)

tk.Label(main_frame, text="Ch 3:").grid(row=16, column=0, sticky="w")
tk.Entry(main_frame, textvariable=osc_2_channels["ch_3"], width=40).grid(row=16, column=1)

tk.Label(main_frame, text="Ch 4:").grid(row=17, column=0, sticky="w")
tk.Entry(main_frame, textvariable=osc_2_channels["ch_4"], width=40).grid(row=17, column=1)

tk.Label(main_frame, text="Oscilloscope 3 Channel Labels:").grid(row=18, column=0, columnspan=2, sticky="w")
tk.Label(main_frame, text="Ch 1:").grid(row=19, column=0, sticky="w")
tk.Entry(main_frame, textvariable=osc_3_channels["ch_1"], width=40).grid(row=19, column=1)

tk.Label(main_frame, text="Ch 2:").grid(row=20, column=0, sticky="w")
tk.Entry(main_frame, textvariable=osc_3_channels["ch_2"], width=40).grid(row=20, column=1)

tk.Label(main_frame, text="Ch 3:").grid(row=21, column=0, sticky="w")
tk.Entry(main_frame, textvariable=osc_3_channels["ch_3"], width=40).grid(row=21, column=1)

tk.Label(main_frame, text="Ch 4:").grid(row=22, column=0, sticky="w")
tk.Entry(main_frame, textvariable=osc_3_channels["ch_4"], width=40).grid(row=22, column=1)

tk.Label(main_frame, text="Save folder:").grid(row=24, column=0, sticky="w")
tk.Entry(main_frame, textvariable= save_folder, width=65).grid(row=24, column=1)

save_folder_entry = tk.Entry(main_frame, textvariable=save_folder, width=65)
save_folder_entry.grid(row=24, column=1)

# def create_osc_section(frame, osc_name, osc_settings, start_row):
#     """
#     Create a section for oscilloscope settings, with dropdowns and checkboxes.
#     """
#     tk.Label(frame, text=f"{osc_name.upper()} Channels:", font=("Arial", 12)).grid(
#         row=start_row, column=0, columnspan=3, sticky="w", pady=5
#     )
#     row = start_row + 1
#     for ch, settings in osc_settings.items():
#         # Ensure settings is a dictionary
#         if isinstance(settings, dict):
#             # Extract existing tkinter variables or initialize new ones
#             measurement_value = (
#                 settings["measurement"].get() if isinstance(settings["measurement"], tk.StringVar) else settings.get("measurement", "None")
#             )
#             dropdown_var = tk.StringVar(value=measurement_value)

#             dropdown = ttk.Combobox(
#                 frame,
#                 textvariable=dropdown_var,
#                 values=osc_measurement_options,
#                 state="readonly",
#                 width=10,
#             )
#             dropdown.grid(row=row, column=1, padx=5, pady=2)

#             make_negative_value = (
#                 settings["make_negative"].get() if isinstance(settings["make_negative"], tk.BooleanVar) else settings.get("make_negative", False)
#             )
#             make_negative_var = tk.BooleanVar(value=make_negative_value)

#             tk.Checkbutton(
#                 frame, text="Make Negative", variable=make_negative_var
#             ).grid(row=row, column=2, sticky="w", padx=10)

#             # Save the updated variables back into the settings dictionary
#             settings["measurement"] = dropdown_var  # Bind the dropdown value
#             settings["make_negative"] = make_negative_var  # Bind the checkbox value

#         else:
#             print(f"Warning: Unexpected settings format for {ch} in {osc_name}: {settings}")

#         # Add channel label
#         tk.Label(frame, text=f"{ch.capitalize()}:", width=15).grid(
#             row=row, column=0, sticky="w", padx=5
#         )
#         row += 1
#     return row

def create_osc_section(frame, osc_name, osc_settings, start_row):
    """
    Create a section for oscilloscope settings, with dropdowns and checkboxes.
    """
    tk.Label(frame, text=f"{osc_name.upper()} Channels:", font=("Arial", 12)).grid(
        row=start_row, column=0, columnspan=3, sticky="w", pady=5
    )
    row = start_row + 1
    for ch, settings in osc_settings.items():
        # Ensure settings is a dictionary
        if isinstance(settings, dict):
            # Extract existing tkinter variables or initialize new ones
            dropdown_var = settings["measurement"]  # tk.StringVar from loaded settings
            make_negative_var = settings["make_negative"]  # tk.BooleanVar from loaded settings

            # Create dropdown for measurement
            dropdown = ttk.Combobox(
                frame,
                textvariable=dropdown_var,
                values=osc_measurement_options,
                state="readonly",
                width=10,
            )
            dropdown.grid(row=row, column=1, padx=5, pady=2)

            # Create checkbox for "Make Negative"
            tk.Checkbutton(
                frame, text="Make Negative", variable=make_negative_var
            ).grid(row=row, column=2, sticky="w", padx=10)

        else:
            print(f"Warning: Unexpected settings format for {ch} in {osc_name}: {settings}")

        # Add channel label
        tk.Label(frame, text=f"{ch.capitalize()}:", width=15).grid(
            row=row, column=0, sticky="w", padx=5
        )
        row += 1
    return row



# Create sections for all three oscilloscopes
create_osc_section(osc_frame, "OSC_1", osc_channel_settings["osc_1"], 1)
create_osc_section(osc_frame, "OSC_2", osc_channel_settings["osc_2"], 6)
create_osc_section(osc_frame, "OSC_3", osc_channel_settings["osc_3"], 11)



tk.Button(main_frame, text="Run Test", command=run_test_gui, bg="green", fg="white").grid(row=26, column=0, columnspan=2, pady=10)

assets_folder = os.path.join(os.getcwd(), "assets")
if os.path.exists(assets_folder) and os.path.isdir(assets_folder):
    shutil.rmtree(assets_folder)
    print("Assets folder deleted successfully.")
else:
    print("Assets folder does not exist.")

root.mainloop()
