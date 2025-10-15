"""
Identify cameras by testing their actual capabilities
Creates a persistent mapping file
"""
import cv2
import json
import os

def get_camera_signature(camera_index):
    """
    Get a unique signature for a camera by testing multiple resolutions
    """
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        return None

    signature = {
        'index': camera_index,
        'resolutions': []
    }

    # Test common resolutions
    test_resolutions = [
        (640, 480),
        (1280, 720),
        (1920, 1080),
        (2560, 1440),
        (3840, 2160)
    ]

    for width, height in test_resolutions:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        res_string = f"{actual_width}x{actual_height}"
        if res_string not in signature['resolutions']:
            signature['resolutions'].append(res_string)

    # Get max resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 9999)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 9999)
    max_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    max_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    signature['max_resolution'] = f"{max_width}x{max_height}"
    signature['max_pixels'] = max_width * max_height

    cap.release()
    return signature

def identify_all_cameras():
    """
    Identify all cameras and create a persistent mapping
    """
    print("Camera Identification Tool")
    print("=" * 80)
    print("This will test all cameras and create a persistent mapping.")
    print()

    cameras = []
    thermal_index = None

    for i in range(5):
        # Check if it's the thermal camera first (240x321)
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            if width == 240 and height == 321:
                thermal_index = i
                cameras.append({
                    'index': i,
                    'type': 'thermal',
                    'name': 'UTi 260B Thermal Camera',
                    'default_resolution': '240x321',
                    'max_resolution': '1280x720',
                    'max_pixels': 921600
                })
                print(f"Camera {i}: UTi 260B Thermal Camera (240x321)")
                cap.release()
                continue

            cap.release()

        # Get full signature for other cameras
        sig = get_camera_signature(i)
        if sig:
            print(f"\nCamera {i}:")
            print(f"  Max Resolution: {sig['max_resolution']} ({sig['max_pixels']:,} pixels)")
            print(f"  Supported Resolutions: {', '.join(sig['resolutions'])}")

            # Classify camera
            if sig['max_pixels'] >= 8000000:  # 8MP+ (4K)
                camera_type = '4k_webcam'
                camera_name = '4K External Webcam'
            elif sig['max_pixels'] >= 2000000:  # 2MP+ (1080p)
                camera_type = 'hd_webcam'
                camera_name = 'HD External Webcam'
            else:
                camera_type = 'standard_webcam'
                camera_name = 'Standard Built-in Webcam'

            cameras.append({
                'index': i,
                'type': camera_type,
                'name': camera_name,
                'max_resolution': sig['max_resolution'],
                'max_pixels': sig['max_pixels'],
                'resolutions': sig['resolutions']
            })

            print(f"  Identified as: {camera_name}")

    print("\n" + "=" * 80)
    print("Camera Summary:")
    print("=" * 80)

    for cam in cameras:
        print(f"Camera {cam['index']}: {cam['name']}")
        print(f"  Type: {cam['type']}")
        print(f"  Max Resolution: {cam['max_resolution']}")

    # Save mapping
    mapping_file = 'camera_mapping.json'
    with open(mapping_file, 'w') as f:
        json.dump(cameras, f, indent=2)

    print(f"\nCamera mapping saved to: {mapping_file}")
    print("\nRecommended Configuration:")

    # Find best webcam (highest resolution that's not thermal)
    webcams = [c for c in cameras if c['type'] != 'thermal']
    if webcams:
        best_webcam = max(webcams, key=lambda x: x['max_pixels'])
        print(f"  Thermal Camera: Camera {thermal_index}")
        print(f"  Best Webcam: Camera {best_webcam['index']} ({best_webcam['name']})")
        print(f"\nTo use this configuration:")
        print(f"  python dual_recorder.py {best_webcam['index']}")

    return cameras

if __name__ == "__main__":
    identify_all_cameras()
