# NicePowerSupply D2001 series (Custom ASCII protocol over RS232)
# Requires: pyserial

import time
import serial

class NicePowerSupply:
    """
    Nice-Power / KUAIQU SPPS-D2001-232
    Transport: Custom ASCII protocol over CP210x virtual COM port.

    Protocol format: <FFDDDDDDAAA>
    - F: Function code (2 digits)
    - D: Data (6 digits)
    - A: Device address (3 digits)
    Total: 13 characters including < and >
    """

    def __init__(self, port, device_addr=0, baudrate=9600, timeout=1):
        """
        :param port: 'COM6' (Windows) or '/dev/ttyUSB0' (Linux)
        :param device_addr: Device address (default 0)
        :param baudrate: typically 9600
        :param timeout: read timeout seconds
        """
        self.port = port
        self.device_addr = int(device_addr)
        self.baudrate = baudrate
        self.timeout = timeout

        # Open serial connection
        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.timeout
        )

        # Clear buffers
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()

        # Connect handshake
        self._send_command('<09100000000>')
        time.sleep(0.1)

    def _send_command(self, command):
        """Send command and read response"""
        self.serial.write(command.encode('ascii'))
        time.sleep(0.1)
        response = self.serial.read(13).decode('ascii', errors='ignore')
        return response

    def _format_voltage(self, voltage):
        """Format voltage as 6-digit string (voltage * 1000)"""
        return f"{int(voltage * 1000):06d}"

    def _format_current(self, current):
        """Format current as 6-digit string (current * 1000)"""
        return f"{int(current * 1000):06d}"

    def _format_device_addr(self):
        """Format device address as 3-digit string"""
        return f"{self.device_addr:03d}"

    def close(self):
        """Disconnect: send disconnect handshake and close serial port"""
        try:
            self._send_command('<09200000000>')  # Disconnect handshake
        except:
            pass
        try:
            if self.serial and self.serial.is_open:
                self.serial.close()
        except:
            pass

    def check_connection(self):
        """Check if the device is responding"""
        try:
            # Try to read voltage
            response = self._send_command(f'<02000000{self._format_device_addr()}>')
            # Valid response should start with '<1' (function 1x for voltage response)
            return response.startswith('<1') and len(response) == 13
        except Exception:
            return False

    def set_remote(self, enable=True):
        """Enable/disable remote mode"""
        if enable:
            self._send_command(f'<08100000{self._format_device_addr()}>')
        else:
            self._send_command(f'<08200000{self._format_device_addr()}>')

    def turn_on(self):
        """Turn on output"""
        self._send_command(f'<07000000{self._format_device_addr()}>')
        time.sleep(1)

    def enable_output(self):
        """Enable output (alias for turn_on for clarity)"""
        self.turn_on()

    def disable_output(self):
        """
        Disable output completely.
        Sets voltage to 0V first, then sends the explicit OFF command.
        """
        # Set voltage to 0V first for safety
        self.set_voltage(0.0)
        time.sleep(0.2)

        # Send explicit OFF command
        self._send_command(f'<07200000{self._format_device_addr()}>')
        time.sleep(0.3)

    def turn_off(self):
        """
        Turn off output by disabling it completely.
        This sets voltage to 0V and sends the explicit OFF command.
        """
        self.disable_output()

    def set_voltage(self, voltage):
       
        voltage_str = self._format_voltage(voltage)
        self._send_command(f'<01{voltage_str}{self._format_device_addr()}>')

        # # If setting to 0V, disable remote mode (output is already off)
        # if voltage == 0:
        #     self.turn_off()
        #     self.set_remote(False)

    def set_current_limit(self, current):
        """
        Set current limit
        :param current: Current in amps (float)
        """
        current_str = self._format_current(current)
        self._send_command(f'<03{current_str}{self._format_device_addr()}>')

#     rep = self._send_command(f'<020122000{self._format_device_addr()}>')
#     print(f"RAW reply: {rep!r}")

#     import re
# def measure_voltage(self):
#         rep = self._send_command(f'<020122000{self._format_device_addr()}>')
#         if not rep or not (rep.startswith('<') and rep.endswith('>')):
#             return None
#         m = re.match(r"<12(\d{5})\d{3}>", rep)  # 5 digits value, 3 digits addr
#         if not m:
#             # fallback: try any 5 consecutive digits after '12'
#             m = re.search(r"^<12(\d{5})", rep)
#             if not m: 
#                 return None
#         val = int(m.group(1))  # e.g., 04580
#         # Most firmwares use hundredths of a volt; some use millivolts. Pick scale by magnitude.
#         return val/100.0 if val >= 1000 else val/1000.0


    def measure_voltage(self):
        """
        Read actual voltage
        :return: Voltage in volts (float)
        """
        response = self._send_command(f'<02000000{self._format_device_addr()}>')
        # Response format: <12VVVVVV000> where VVVVVV is voltage * 100
        if response.startswith('<12') and len(response) == 13:
            voltage_str = response[3:9]
            return float(voltage_str) / 1000.0
        return 
    
    # def set_voltage(self):
    #     rep = self._send_command(f'<020122000{self._format_device_addr()}>')  # e.g., "<12004580000>"
    #     if not rep or rep[0] != '<' or rep[-1] != '>':
    #         return None
    #     core = rep[1:-1]              # "12004580000"
    #     if not core.startswith('12'):
    #         return None
    #     digits = ''.join(ch for ch in core[2:] if ch.isdigit()).ljust(5, '0')[:5]
    #     return int(digits) / 100.0     # -> volts


    def measure_current(self):
        """
        Read actual current
        :return: Current in amps (float)
        """
        response = self._send_command(f'<04000000{self._format_device_addr()}>')
        # Response format: <14XCCCCCC00> where X is CV/CC state, CCCCCC is current * 100
        if response.startswith('<14') and len(response) == 13:
            current_str = response[4:10]
            return float(current_str) / 100.0
        return 0.0

    def reset(self):
        """Reset to safe state (0V, output off)"""
        try:
            self.turn_off()  # Sets voltage to 0, which turns off output
        except:
            pass

    def configure_voltage_current(self, voltage, current):
        """
        Configure voltage and current, then turn on output
        :param voltage: Voltage in volts
        :param current: Current limit in amps
        """
        self.set_remote(True)
        self.set_current_limit(current)
        self.set_voltage(voltage)
        self.turn_on()


# ---- Example usage ----
if __name__ == "__main__":
    # Windows: port like "COM6"; Linux: "/dev/ttyUSB0"
    ps = NicePowerSupply(port="COM5", device_addr=0, baudrate=9600)

    try:
        print("Setting remote mode...")
        ps.set_remote(True)

        print("Setting current limit to 0.1A...")
        ps.set_current_limit(0.1)

        print("Setting voltage to 1.5V...")
        ps.set_voltage(1.5)

        print("Turning on output...")
        ps.turn_on()

        print("Reading measurements...")
        voltage = ps.measure_voltage()
        current = ps.measure_current()
        print(f"Measured: {voltage:.3f}V, {current:.3f}A")

    finally:
        print("Turning off and disconnecting...")
        ps.close()
