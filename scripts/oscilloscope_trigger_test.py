import os, time, sys, struct
from datetime import datetime, timezone
from rigol_usb_locator import RigolUsbLocator
from Rigol_DS1054z import RigolOscilloscope

OUT_DIR = "Tests"
CHUNK = 250_000
MEMORY_DEPTH = 24_000_000
POINTS_PER_SECOND = 1_000_000_000
TIME_SCALE = MEMORY_DEPTH / (POINTS_PER_SECOND * 12 * 2 * 2)
HDR_FMT = "<4sH I Q I f f f f f f B B 6x"   # 4+2+4+8+4+4*6+1+1+6 = 48 B
# fields: MAGIC,VER,N, t0_ns, dt_ps, XINC,XOR,XREF, YINC,YOR,YREF, chan, flags, pad
MAGIC, VER = b"RGOL", 1

def utc_iso():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")

def wait_for_trigger_stop(i, wait_treshold = 10, query_cooldown = 0.005):
    deadline = time.monotonic() + wait_treshold
    while time.monotonic() < deadline:
        state = i.query(":TRIG:STAT?").strip().upper()
        if state == "STOP":
            # print("DEBUG: waited for trigger stop for ", time.time() - start, " seconds")
            return
        elif state == "WAIT":
            i.write(":TFOR")
            # print("DEBUG: force triggered after ", time.time() - start, " seconds")
            return
        time.sleep(query_cooldown)
    raise TimeoutError(f"Waiting for Trigger STOP. timed out after {wait_treshold} seconds.") 

def write_header(f, i, pre):
    # ... inside your acquisition loop, right after you queried WAV:PRE? ...
    # Common DS1054Z ordering: ... XINC,XOR,XREF,YINC,YOR,YREF at indices 4..9
    XINC = float(pre[4]); XOR = float(pre[5]); XREF = float(pre[6])
    YINC = float(pre[7]); YOR = float(pre[8]); YREF = float(pre[9])
    dt_ps = int(round(XINC * 1e12))
    t0_ns = time.time_ns()
    chan = 1
    flags = 0
    acquired_points = int(pre[2])  # you already do this

    hdr = struct.pack(HDR_FMT, MAGIC, VER, acquired_points, t0_ns, dt_ps,
                    XINC, XOR, XREF, YINC, YOR, YREF, chan, flags)
    f.write(hdr)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Get device address from command line, or use auto-detect
    osc_address = sys.argv[1] if len(sys.argv) > 1 else None

    if osc_address:
        osc = RigolOscilloscope(osc_address)
        # Extract serial from address: USB0::0x1AB1::0x04CE::DS1A123456::INSTR
        serial = osc_address.split("::")[3] if "::" in osc_address else "unknown"
    else:
        loc = RigolUsbLocator(verbose=False); loc.refresh()
        osc = loc.get_oscilloscope()
        serial = "auto"

    # Create filename
    if serial == "auto":
        filename = "trigger_auto.bin"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"trigger_{serial}_{timestamp}.bin"
    FILE_PATH = os.path.join(OUT_DIR, filename)
    print(f"Output file: {FILE_PATH}")

    i = osc.instrument

    i.timeout = 60000           # 60 s
    i.chunk_size = 1024*1024    # 1 MiB
    i.read_termination = ''     # binary
    i.write_termination = '\n'

    i.write(":RUN")
    i.write(f":ACQ:MDEP {MEMORY_DEPTH}")
    i.write(":CHAN1:DISP ON; :CHAN2:DISP OFF; :CHAN3:DISP OFF; :CHAN4:DISP OFF")
    i.write(":ACQ:TYPE NORM")
    i.write(f":TIM:SCAL {TIME_SCALE}")

    # Trigger mode and settings
    i.write(":TRIG:MODE EDGE")              # Set to edge trigger mode
    i.write(":TRIG:EDGE:SOUR CHAN1")        # Trigger source: Channel 1
    i.write(":TRIG:EDGE:SLOP NEG")          # Trigger slope: POS (rising) or NEG (falling)
    i.write(":TRIG:EDGE:LEV -0.13")           # Trigger level in volts
    i.write(":TRIG:SWE NORM")               # Trigger sweep: NORMAL (waits for trigger, not AUTO)

    # Trigger position (50% = center)
    i.write(":TIM:OFFS 0")                  # 0 offset = trigger at 50% of screen

    with open(FILE_PATH, "wb", buffering=1024*1024) as f:
        i.write(":SING")
        print("DEBUG: sing")
        wait_for_trigger_stop(i)
        i.write(":STOP")
        print("DEBUG: STOP")

        i.write(":WAV:SOUR CHAN1")
        i.write(":WAV:MODE RAW")
        i.write(":WAV:POIN:MODE RAW")
        i.write(":WAV:FORM BYTE")
        i.write(":WAV:BYTE LSBF")
        pre = i.query(":WAV:PRE?").split(",")
        acquired_points = int(pre[2])

        write_header(f, i, pre)

        start = 1
        while start <= acquired_points:
            stop = min(start + CHUNK - 1, acquired_points)
            i.write(f":WAV:STAR {start}")
            i.write(f":WAV:STOP {stop}")

            block = i.query_binary_values(":WAV:DATA?", datatype="B", container=bytearray)
            f.write(block)

            start = stop + 1
    osc.close()

if __name__ == "__main__":
    main()