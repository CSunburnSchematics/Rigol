# NicePowerSupply (SPPS-D series, Modbus RTU over CP210x COM)
# pip install minimalmodbus pyserial

import time
import minimalmodbus
import serial

class NicePowerSupply:
    """
    Nice-Power / KUAIQU SPPS-Dxxxx (e.g., SPPS-D8001-232)
    Transport: Modbus RTU over CP210x virtual COM port.
    """

    # ---- Modbus register map (float = 2 regs, big-endian words) ----
    REG_REMOTE = 0x0000   # 0=local, 1=remote (FC06)
    REG_VSET   = 0x0001   # float, set voltage (FC16 write, FC03 read)
    REG_ISET   = 0x0003   # float, set current (FC16 write, FC03 read)
    REG_OUT    = 0x001B   # 0/1 output (FC06)
    REG_VOUT   = 0x001D   # float, measured V (FC03)
    REG_IOUT   = 0x001F   # float, measured I (FC03)
    REG_CVCC   = 0x0021   # 0=CV, 1=CC (FC03)

    def __init__(self, port, slave_addr=1, baudrate=9600, timeout=0.5, parity="N"):
        """
        :param port: 'COM5' (Windows) or '/dev/ttyUSB0' (Linux)
        :param slave_addr: Modbus slave address (default 1)
        :param baudrate: typically 9600
        :param timeout: read timeout seconds
        :param parity: 'N' or 'E' (docs/examples work with 8N1; try 'E' if needed)
        """
        self.port = port
        self.slave = int(slave_addr)
        self.byteorder = minimalmodbus.BYTEORDER_BIG

        self.inst = minimalmodbus.Instrument(self.port, self.slave, mode=minimalmodbus.MODE_RTU)
        self.inst.serial.baudrate = baudrate
        self.inst.serial.bytesize = 8
        self.inst.serial.parity   = serial.PARITY_NONE if parity.upper() == "N" else serial.PARITY_EVEN
        self.inst.serial.stopbits = 1
        self.inst.serial.timeout  = timeout
        self.inst.clear_buffers_before_each_transaction = True

        time.sleep(0.1)

    def _sleep(self, seconds=0.02):
        time.sleep(seconds)

    def _write_u16(self, reg, value):
        # write_register(addr, value, decimals, functioncode)
        self.inst.write_register(reg, int(value), 0, 6)
        self._sleep()

    def _write_float(self, reg, value):
        # write_float(addr, value, number_of_registers=2, byteorder=...)
        self.inst.write_float(reg, float(value), 2, self.byteorder)
        self._sleep()

    def _read_u16(self, reg):
        # read_register(addr, decimals, functioncode)
        v = self.inst.read_register(reg, 0, 3)
        self._sleep()
        return v

    def _read_float(self, reg):
        # read_float(addr, functioncode, number_of_registers, byteorder)
        v = self.inst.read_float(reg, 3, 2, self.byteorder)
        self._sleep()
        return float(v)

    def close(self):
        try:
            if self.inst and self.inst.serial and self.inst.serial.is_open:
                self.inst.serial.close()
        except Exception:
            pass

    def check_connection(self):
        try:
            mode = self._read_u16(self.REG_CVCC)
            print(f"Modbus OK (mode={'CV' if mode==0 else 'CC'})")
            return True
        except Exception as e:
            print(f"Connection check failed: {e}")
            return False

    def set_remote(self, enable=True):
        """Enable/disable remote (required to allow writes)."""
        self._write_u16(self.REG_REMOTE, 1 if enable else 0)

    def turn_on(self):
        self._write_u16(self.REG_OUT, 1)

    def turn_off(self):
        self._write_u16(self.REG_OUT, 0)

    def set_voltage(self, channel_ignored, voltage):
        self._write_float(self.REG_VSET, float(voltage))

    def set_current_limit(self, channel_ignored, current):
        self._write_float(self.REG_ISET, float(current))

    def measure_voltage(self, channel_ignored=1):
        return self._read_float(self.REG_VOUT)

    def measure_current(self, channel_ignored=1):
        return self._read_float(self.REG_IOUT)

    def read_set_voltage(self):
        return self._read_float(self.REG_VSET)

    def read_set_current(self):
        return self._read_float(self.REG_ISET)

    def reset(self):
        try:
            self.set_voltage(1, 0.0)
        finally:
            self.turn_off()

    def configure_voltage_current(self, voltage, current, verify=True, max_retries=3, tol=0.2):
        """
        Set V/I and (re)enable output.
        :param voltage: desired volts (float) — start LOW on first use!
        :param current: desired amps (float)
        :param verify: if True, read back set registers (not measured!) to confirm
        :param max_retries: retries if verification misses tolerance
        :param tol: acceptable absolute error when verifying set registers
        """
        # Enter remote first
        self.set_remote(True)

        # Set points
        self.set_voltage(1, voltage)
        self.set_current_limit(1, current)

        # Optional verification against set registers (stable, load-agnostic)
        if verify:
            for attempt in range(1, max_retries + 1):
                vset = self.read_set_voltage()
                iset = self.read_set_current()
                dv   = abs(vset - voltage)
                di   = abs(iset - current)
                if dv <= tol and di <= tol:
                    break
                # retry writes
                if dv > tol:
                    self.set_voltage(1, voltage)
                if di > tol:
                    self.set_current_limit(1, current)
            else:
                raise RuntimeError(f"Failed to verify setpoints: Vset={vset:.3f} (want {voltage}), Iset={iset:.3f} (want {current})")

        # Enable output at the end (safer)
        self.turn_on()

    # ---------------- Extras ----------------

    def sweep_voltage(self, start_v, stop_v, step_v, delay_s=0.1, current_limit=None):
        """
        Simple ramp/sweep (monotonic). Returns a list of (v_meas, i_meas).
        """
        if current_limit is not None:
            self.set_current_limit(1, current_limit)
        self.set_remote(True)
        seq = []
        direction = 1 if stop_v >= start_v else -1
        v = start_v
        while True:
            self.set_voltage(1, v)
            time.sleep(delay_s)
            vm = self.measure_voltage()
            im = self.measure_current()
            seq.append((vm, im))
            if (direction > 0 and v >= stop_v) or (direction < 0 and v <= stop_v):
                break
            v = v + direction * abs(step_v)
        return seq

# ---------------- Example usage ----------------
if __name__ == "__main__":
    # Windows: port like "COM5"; Linux: "/dev/ttyUSB0"
    ps = NicePowerSupply(port="COM5", slave_addr=1, baudrate=9600, parity="N")

    try:
        print("DEBUG: 1")
        # print(ps.inst.read_register(0, 0, functioncode=3))
        ps.set_remote(True)
        print("DEBUG: 2")
        ps.set_current_limit(1, 1)         # 100 mA limit — SAFE default
        print("DEBUG: 3")
        ps.turn_on()
        print("DEBUG: 4")

        # Sweep 0 → 20 V in 1 V steps, ~100 ms dwell per step
        data = ps.sweep_voltage(start_v=0.0, stop_v=5.0, step_v=1.0, delay_s=1.0)

        for idx, (vm, im) in enumerate(data):
            print(f"Step {idx:02d}: {vm:.3f} V, {im:.3f} A")
    finally:
        ps.set_remote(False)
        ps.turn_off()
        ps.close()