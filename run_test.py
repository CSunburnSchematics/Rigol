import subprocess
import datetime
import os
import cv2 
import shutil  
import time


#Change variables
TEST_SETUP_NAME = "#9"
NOTES = "465khz N49 4:4 19.2 uH 2oz RLS.020.030-3-SEC(orange) R1:15k R6:18k R9:62k R8:1.2k R7:1.2k"  
CURRENT_TEST_LIST = [0.0, 0.25, 0.5, 1, 2, 4, 8.4] 
INPUT_VOLTAGE_TEST_LIST =  [36, 50.5, 60] #[36, 52, 60]  

OSC_1_CH_1 = "Preactive Fet Gate"
OSC_1_CH_2 = "Main Fet Gate"
OSC_1_CH_3 = "Forward Fet Gate"
OSC_1_CH_4 = "Catch Fet Gate"

OSC_2_CH_1 = "Preactive Fet VDS"
OSC_2_CH_2 = "Main Fet VDS"
OSC_2_CH_3 = "Forward Fet VDS"
OSC_2_CH_4 = "Catch Fet VDS"

#not changed often
DWELL_TIME = 2
INPUT_CURRENT_LIMIT = 5
WEBCAM_NUMBER = 1
POWER_SUPPLY = "korad" #"rigol"



def capture_two_webcam_images(output_path1, output_path2):
    # Ensure the output paths include valid image extensions
    if not output_path1.lower().endswith((".png", ".jpg", ".jpeg")):
        output_path1 += ".png"  # Default to PNG for the first image
    if not output_path2.lower().endswith((".png", ".jpg", ".jpeg")):
        output_path2 += ".png"  # Default to PNG for the second image

    # Initialize webcam with timing
    start_time = time.time()
    webcam = cv2.VideoCapture(WEBCAM_NUMBER, cv2.CAP_DSHOW)
    if not webcam.isOpened():
        print("Error: Unable to access the webcam.")
        return
    print(f"Webcam initialized in {time.time() - start_time:.2f} seconds.")

    # Optimize resolution and FPS
    # webcam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    # webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
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

def run_test():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    test_folder = f"Test_{TEST_SETUP_NAME.replace(" ", "_")}_{timestamp}"
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
        f"--power_supply={POWER_SUPPLY}",
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


assets_folder = os.path.join(os.getcwd(), "assets")  # Get the 'assets' folder in the root directory

if os.path.exists(assets_folder) and os.path.isdir(assets_folder):
    shutil.rmtree(assets_folder)
    print("Assets folder deleted successfully.")
else:
    print("Assets folder does not exist.")

if __name__ == "__main__":
    test_folder = run_test()
    run_dashboard(test_folder)
