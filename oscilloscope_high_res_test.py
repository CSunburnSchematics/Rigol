import os, time, sys, struct
from datetime import datetime, timezone
from rigol_usb_locator import RigolUsbLocator

OUT_DIR = "Tests"
RUNS = float("inf")
PROGRESS_BAR_CHAR_LENGTH = 25
CHUNK = 250_000
MEMORY_DEPTH = 6_000_000
POINTS_PER_SECOND = 1_000_000_000
TIME_SCALE = MEMORY_DEPTH / (POINTS_PER_SECOND * 24 * 2)
HDR_FMT = "<4sH I Q I f f f f f f B B 6x"   # 4+2+4+8+4+4*6+1+1+6 = 48 B
# fields: MAGIC,VER,N, t0_ns, dt_ps, XINC,XOR,XREF, YINC,YOR,YREF, chan, flags, pad
MAGIC, VER = b"RGOL", 1

def wait_for_trigger_stop(i, wait_treshold = 10, query_cooldown = 0.005):
    start = time.time()
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

def write_header(f, pre, chan):
    XINC = float(pre[4]); XOR = float(pre[5]); XREF = float(pre[6])
    YINC = float(pre[7]); YOR = float(pre[8]); YREF = float(pre[9])
    dt_ps = int(round(XINC * 1e12))
    t0_ns = time.time_ns()
    acquired_points = int(pre[2])
    hdr = struct.pack(HDR_FMT, MAGIC, VER, acquired_points, t0_ns, dt_ps,
                    XINC, XOR, XREF, YINC, YOR, YREF, chan, 0)
    f.write(hdr)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Get device address from command line, or use auto-detect
    osc_address = sys.argv[1] if len(sys.argv) > 1 else None

    if osc_address:
        from Rigol_DS1054z import RigolOscilloscope
        osc = RigolOscilloscope(osc_address)
        # Extract serial from address: USB0::0x1AB1::0x04CE::DS1A123456::INSTR
        serial = osc_address.split("::")[3] if "::" in osc_address else "unknown"
    else:
        loc = RigolUsbLocator(verbose=False); loc.refresh()
        osc = loc.get_oscilloscope()
        serial = "auto"

    i = osc.instrument
    i.timeout = 60000           # 60 s
    i.chunk_size = 1024*1024    # 1 MiB
    i.read_termination = ''     # binary
    i.write_termination = '\n'

    i.write(":RUN") # setting memory depth is only reliable in run mode
    i.write(f":ACQ:MDEP {MEMORY_DEPTH}")
    i.write(":CHAN1:DISP ON; :CHAN2:DISP ON; :CHAN3:DISP ON; :CHAN4:DISP ON")
    i.write(":CHAN1:SCAL 0.1; :CHAN2:SCAL 0.1; :CHAN3:SCAL 0.1; :CHAN4:SCAL 0.1")
    i.write(":CHAN1:PROB 100; :CHAN2:PROB 100; :CHAN3:PROB 100; :CHAN4:PROB 100")
    i.write(":ACQ:TYPE NORM")
    i.write(f":TIM:SCAL {TIME_SCALE}") # 1 sample per nanosecond is the upper limit of the instrument

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"osc_{serial}_{timestamp}.bin"
    FILE_PATH = os.path.join(OUT_DIR, filename)
    print(f"Output file: {FILE_PATH}")

    idx = 0
    with open(FILE_PATH, "ab", buffering=1024*1024) as f:
        while idx < RUNS:
            i.write(":SING")
            wait_for_trigger_stop(i)
            i.write(":STOP")

            i.write(":WAV:MODE RAW")
            i.write(":WAV:POIN:MODE RAW")
            i.write(":WAV:FORM BYTE")
            i.write(":WAV:BYTE LSBF")

            start_time = time.perf_counter()
            for chan in range(1, 5):
                i.write(f":WAV:SOUR CHAN{chan}")
                pre = i.query(":WAV:PRE?").split(",")
                acquired_points = int(pre[2])

                write_header(f, pre, chan)

                start = 1
                while start <= acquired_points:
                    stop = min(start + CHUNK - 1, acquired_points)
                    i.write(f":WAV:STAR {start};:WAV:STOP {stop}")
                    block = i.query_binary_values(":WAV:DATA?", datatype="B", container=bytearray)
                    f.write(block)
                    start = stop + 1
                f.flush()
            elapsed_time = time.perf_counter() - start_time
            print(f"RUN {idx}: {elapsed_time:.6f}s")
            idx += 1
    osc.close()

if __name__ == "__main__":
    main()
