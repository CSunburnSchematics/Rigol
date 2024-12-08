import serial
import time

# Replace 'COM5' with the correct port name if necessary
SERIAL_PORT = 'COM5'
BAUD_RATE = 115200

try:
    # Open serial port with specified settings
    ser = serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUD_RATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1,  # Timeout for read/write
        xonxoff=False,  # Software flow control
        rtscts=False,  # Hardware flow control
        dsrdtr=False  # Data Set Ready/Data Terminal Ready flow control
    )

    if ser.is_open:
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")

        # Send a test command (modify as per device documentation)
        test_command = b'help\n'  # Command must be in bytes
        ser.write(test_command)
        print(f"Sent command: {test_command.decode('utf-8').strip()}")

        # Wait for a response
        time.sleep(0.5)
        response = ser.read_all().decode('utf-8', errors='ignore')  # Read response
        print(f"Response from device: {response}")

except serial.SerialException as e:
    print(f"Serial error: {e}")

except Exception as e:
    print(f"Error: {e}")

finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("Serial connection closed.")
