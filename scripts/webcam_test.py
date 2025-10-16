import cv2
import time

WEBCAM_NUMBER = 1


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


capture_two_webcam_images("webcam_pic1", "webcam_pic2")
