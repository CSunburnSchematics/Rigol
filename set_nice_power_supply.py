import sys, time
import serial

VOLTAGE_LIMIT = 5
BAUDRATE = 9600
TIMEOUT = 1

def send_command(ser, command):
    """Send command and return response"""
    ser.write(command.encode('ascii'))
    time.sleep(0.1)  # Small delay for device to process
    # Read response (fixed 13 char response)
    response = ser.read(13).decode('ascii', errors='ignore')
    return response

def format_voltage_value(voltage):
    """Format voltage as 6-digit string (voltage * 1000 with leading zeros)"""
    voltage_int = int(voltage * 1000)
    return f"{voltage_int:06d}"

def format_current_value(current):
    """Format current as 6-digit string (current * 1000 with leading zeros)"""
    current_int = int(current * 1000)
    return f"{current_int:06d}"

if __name__ == "__main__":
    # Get COM port and voltage from command line (both required)
    # Usage: python set_nice_power_supply.py COM6 1.5 [device_addr]
    com_port = sys.argv[1]
    voltage = float(sys.argv[2])
    device_addr = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    try:
        # Open serial connection
        ser = serial.Serial(
            port=com_port,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=TIMEOUT
        )

        # Clear any existing data
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        # Connect handshake
        send_command(ser, '<09100000000>')

        # Set to remote mode (unlock)
        send_command(ser, '<08100000000>')

        # Set current limit to 0.001A (1mA)
        current_str = format_current_value(0.1)
        send_command(ser, f'<03{current_str}000>')

        # Safety check: voltage over limit
        if voltage > VOLTAGE_LIMIT:
            print(f"ERROR: Voltage {voltage}V exceeds {VOLTAGE_LIMIT}V limit!")
            # Set to 0V and turn off
            send_command(ser, '<01000000000>')
            send_command(ser, '<07200000000>')  # Output OFF
            # Disconnect
            send_command(ser, '<09200000000>')
            ser.close()
            raise ValueError(f"Voltage {voltage}V exceeds {VOLTAGE_LIMIT}V safety limit")

        # If 0V, set to 0 and turn off
        if voltage == 0:
            send_command(ser, '<01000000000>')
            send_command(ser, '<07200000000>')  # Output OFF
            print(f"Nice Power supply on {com_port} (addr {device_addr}) set to 0V and turned OFF")
        else:
            # Set voltage and turn on
            voltage_str = format_voltage_value(voltage)
            send_command(ser, f'<01{voltage_str}000>')
            send_command(ser, f'<07100000000>')  # Output ON
            print(f"Nice Power supply on {com_port} (addr {device_addr}) set to {voltage}V and turned ON")

        # Disconnect
        send_command(ser, '<09200000000>')

    except serial.SerialException as e:
        print(f"Serial error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
