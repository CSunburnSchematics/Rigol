import subprocess
import datetime
import os

# Parameters for the test
MIN_CURRENT = 0.0
MAX_CURRENT = 1.0
STEP_SIZE = 0.1
DWELL_TIME = 2
INPUT_VOLTAGE = 30
INPUT_CURRENT_LIMIT = 1

def run_test():
    # Create a unique folder for the test
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    test_folder = f"test_min_{MIN_CURRENT}_max_{MAX_CURRENT}_step_{STEP_SIZE}_{timestamp}"
    os.makedirs(test_folder, exist_ok=True)

    # Run the test script with all parameters
    subprocess.run([
        "python", "main.py",
        f"--min_current={MIN_CURRENT}",
        f"--max_current={MAX_CURRENT}",
        f"--step_size={STEP_SIZE}",
        f"--dwell_time={DWELL_TIME}",
        f"--input_voltage={INPUT_VOLTAGE}",
        f"--input_current_limit={INPUT_CURRENT_LIMIT}",
        f"--test_folder={test_folder}"
    ], check=True)

    return test_folder

def run_dashboard(test_folder):
    # Run the dashboard script with the test folder
    subprocess.run(["python", "dashboard.py", test_folder], check=True)

if __name__ == "__main__":
    test_folder = run_test()  # Run the test and wait for it to complete
    run_dashboard(test_folder)  # Launch the dashboard with the test folder
