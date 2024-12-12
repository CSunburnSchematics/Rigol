import subprocess
import datetime
import os
import cv2

#Change variables
TEST_SETUP_NAME = "Code testing" #"RLS.020.030_Coupon_7_Voltage_24_30_36_Current_0_to_8.3"
NOTES = "1:1 N49 transformer"  # Add notes here
CURRENT_TEST_LIST = [0.0, 0.25, 0.5, 1, 2, 4, 8.3] # 0.4, 0.8, 1.6, 3.2, 6.4, 8.3]
INPUT_VOLTAGE_TEST_LIST = [24, 30, 36]

#not changed often
DWELL_TIME = 2
INPUT_CURRENT_LIMIT = 3
WEBCAM_NUMBER = 1

def capture_webcam_image(output_path):
    webcam = cv2.VideoCapture(WEBCAM_NUMBER)
    if not webcam.isOpened():
        print("Error: Unable to access the webcam.")
        return
    ret, frame = webcam.read()
    if ret:
        cv2.imwrite(output_path, frame)
        print(f"Image captured and saved to {output_path}")
    else:
        print("Error: Unable to capture an image from the webcam.")
    webcam.release()

def run_test():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    test_folder = f"Test_{TEST_SETUP_NAME}_{timestamp}"
    os.makedirs(test_folder, exist_ok=True)
    webcam_image_path = os.path.join(test_folder, "webcam_image.png")
    capture_webcam_image(webcam_image_path)
    
    subprocess.run([
        "python", "main.py",
        f"--current_list={CURRENT_TEST_LIST}",
        f"--test_setup_name={TEST_SETUP_NAME}",
        f"--voltage_list={INPUT_VOLTAGE_TEST_LIST}",
        f"--dwell_time={DWELL_TIME}",
        f"--input_current_limit={INPUT_CURRENT_LIMIT}",
        f"--test_folder={test_folder}"
    ], check=True)

    return test_folder

def run_dashboard(test_folder):
    subprocess.run([
        "python", "dashboard.py",
        test_folder,
        TEST_SETUP_NAME,
        NOTES
    ], check=True)

if __name__ == "__main__":
    test_folder = run_test()
    run_dashboard(test_folder)
