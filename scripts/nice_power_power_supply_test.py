import time, minimalmodbus, serial

PORT = "/dev/ttyUSB0"
SLAVE = 1

inst = minimalmodbus.Instrument(PORT, SLAVE, mode=minimalmodbus.MODE_RTU)
inst.serial.baudrate = 9600
inst.serial.bytesize = 8
inst.serial.parity   = serial.PARITY_NONE
inst.serial.stopbits = 1
inst.serial.timeout  = 0.5
inst.clear_buffers_before_each_transaction = True

BYTEORDER = minimalmodbus.BYTEORDER_BIG

# Registers (from the MODBUS doc)
REG_REMOTE = 0x0000        # 0=local, 1=remote (write with FC06)
REG_VSET   = 0x0001        # float (2 regs, big-endian words) write with FC16
REG_ISET   = 0x0003        # float (2 regs) write with FC16
REG_OUT    = 0x001B        # 0/1 output off/on (FC06)
REG_VOUT   = 0x001D        # float (2 regs) read with FC03
REG_IOUT   = 0x001F        # float (2 regs) read with FC03
REG_CVCC   = 0x0021        # 0=CV, 1=CC (FC03)

def set_remote(enable: bool):
    # write_register(addr, value, num_decimals=0, functioncode=6)
    inst.write_register(REG_REMOTE, 1 if enable else 0, 0, 6)
    time.sleep(0.02)

def set_voltage(volts: float):
    # Old/new minimalmodbus: write_float(addr, value, number_of_registers=2, byteorder=...)
    inst.write_float(REG_VSET, volts, 2, BYTEORDER)
    time.sleep(0.02)

def set_current(amps: float):
    inst.write_float(REG_ISET, amps, 2, BYTEORDER)
    time.sleep(0.02)

def output_on(on: bool):
    inst.write_register(REG_OUT, 1 if on else 0, 0, 6)
    time.sleep(0.02)

def read_voltage() -> float:
    # read_float(addr, functioncode=3, number_of_registers=2, byteorder=...)
    return inst.read_float(REG_VOUT, 3, 2, BYTEORDER)

def read_current() -> float:
    return inst.read_float(REG_IOUT, 3, 2, BYTEORDER)

def read_mode() -> str:
    # read_register(addr, number_of_decimals=0, functioncode=3)
    val = inst.read_register(REG_CVCC, 0, 3)
    return "CV" if val == 0 else "CC"

if __name__ == "__main__":
    set_remote(True)
    set_voltage(5.0)      # start low!
    set_current(0.10)
    output_on(True)
    time.sleep(0.2)
    print("V/I:", read_voltage(), read_current(), "mode:", read_mode())
    output_on(False)
