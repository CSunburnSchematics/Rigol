import subprocess
import datetime
import os
import cv2

# Parameters for the test
CURRENT_TEST_LIST = [0.0, 0.1, 0.2, 0.3]
MIN_CURRENT = 0.0
MAX_CURRENT = 0.2
STEP_SIZE = 0.1
DWELL_TIME = 2
INPUT_VOLTAGE = 30
INPUT_CURRENT_LIMIT = 2
WEBCAM_NUMBER = 1


def capture_webcam_image(output_path):
    # Open a connection to the webcam (0 is usually the default webcam)
    webcam = cv2.VideoCapture(WEBCAM_NUMBER)  # Use 1 if it's not the default webcam
    
    if not webcam.isOpened():
        print("Error: Unable to access the webcam.")
        return

    # Capture a single frame
    ret, frame = webcam.read()
    if ret:
        # Save the frame as an image
        cv2.imwrite(output_path, frame)
        print(f"Image captured and saved to {output_path}")
    else:
        print("Error: Unable to capture an image from the webcam.")

    # Release the webcam resource
    webcam.release()


def run_test():
    # Create a unique folder for the test
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    test_folder = f"test_min_{MIN_CURRENT}_max_{MAX_CURRENT}_step_{STEP_SIZE}_{timestamp}"
    os.makedirs(test_folder, exist_ok=True)
    webcam_image_path = os.path.join(test_folder, "webcam_image.png")
    capture_webcam_image(webcam_image_path)
    

    # Run the test script with all parameters
    subprocess.run([
        "python", "main.py",
        f"--current_list={CURRENT_TEST_LIST}",
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
