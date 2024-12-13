import subprocess
import datetime
import os
import cv2

#Change variables
TEST_SETUP_NAME = "test" #"#11_475KHz_Voltage_36_52_60_Current_0_to_8.3" #"#12_333KHz_Voltage_36_52_60_Current_0_to_8.3" #"#10_Voltage_36_52_60_Current_0_to_8.3"
NOTES = "testing code" #"r1=15k r6=27k, RCS1=.003 Q3=G900P15D5, Q1,Q2,Q4 = TPH5200"  #"r1=15k r6=27k, RCS1=.003 Q3=G900P15D5, Q1,Q2,Q4 = TPH5200" 
CURRENT_TEST_LIST = [0.0] #[0.0, 0.25, 0.5, 1, 2, 4, 8.3] # 0.4, 0.8, 1.6, 3.2, 6.4, 8.3]
INPUT_VOLTAGE_TEST_LIST =  [30] #[36, 52, 60]

OSC_1_CH_1 = "Channel 1"
OSC_1_CH_2 = "Channel 2"
OSC_1_CH_3 = "Channel 3"
OSC_1_CH_4 = "Channel 4"

OSC_2_CH_1 = "Channel 1"
OSC_2_CH_2 = "Channel 2"
OSC_2_CH_3 = "Channel 3"
OSC_2_CH_4 = "Channel 4"

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

def capture_two_webcam_images(output_path1, output_path2):
    # Ensure the output paths include valid image extensions
    if not output_path1.lower().endswith((".png", ".jpg", ".jpeg")):
        output_path1 += ".png"  # Default to PNG for the first image
    if not output_path2.lower().endswith((".png", ".jpg", ".jpeg")):
        output_path2 += ".png"  # Default to PNG for the second image

    webcam = cv2.VideoCapture(WEBCAM_NUMBER)
    if not webcam.isOpened():
        print("Error: Unable to access the webcam.")
        return
    
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

def run_test():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    test_folder = f"Test_{TEST_SETUP_NAME}_{timestamp}"
    os.makedirs(test_folder, exist_ok=True)
    webcam_image_path_1 = os.path.join(test_folder, "webcam_image_1.png")
    webcam_image_path_2 = os.path.join(test_folder, "webcam_image_2.png")

    capture_two_webcam_images(webcam_image_path_1, webcam_image_path_2)
    
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
        NOTES.replace(" ", "_"),  
        OSC_1_CH_1.replace(" ", "_"),
        OSC_1_CH_2.replace(" ", "_"),
        OSC_1_CH_3.replace(" ", "_"), 
        OSC_1_CH_4.replace(" ", "_"),
        OSC_2_CH_1.replace(" ", "_"),
        OSC_2_CH_2.replace(" ", "_"),
        OSC_2_CH_3.replace(" ", "_"),
        OSC_2_CH_4.replace(" ", "_")
    ], check=True)

if __name__ == "__main__":
    test_folder = run_test()
    run_dashboard(test_folder)
