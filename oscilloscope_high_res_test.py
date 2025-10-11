import os, time, sys, struct
from datetime import datetime, timezone
from rigol_usb_locator import RigolUsbLocator

OUT_DIR = "Tests"
FILE_PATH = os.path.join(OUT_DIR, 'oscilloscope_binary_capture.bin')
RUNS = 10
PROGRESS_BAR_CHAR_LENGTH = 25
CHUNK = 250_000
# MEMORY_DEPTH = 12_000_000
MEMORY_DEPTHS_TO_TEST = [24_000_000]
POINTS_PER_SECOND = 1_000_000_000
# TIME_SCALE = MEMORY_DEPTH / (POINTS_PER_SECOND * 12 * 2)
HDR_FMT = "<4sH I Q I f f f f f f B B 6x"   # 4+2+4+8+4+4*6+1+1+6 = 48 B
# fields: MAGIC,VER,N, t0_ns, dt_ps, XINC,XOR,XREF, YINC,YOR,YREF, chan, flags, pad
MAGIC, VER = b"RGOL", 1

perf_times = {k : [] for k in MEMORY_DEPTHS_TO_TEST}

def draw_progress_bar(start, acquired_points):
    debug_progress = int(100*start/acquired_points)
    debug_bar_progress = int(debug_progress/100*PROGRESS_BAR_CHAR_LENGTH)
    sys.stdout.write(f"\r[{debug_bar_progress*'#'+(PROGRESS_BAR_CHAR_LENGTH-debug_bar_progress)*' '}] {debug_progress}% complete")
    sys.stdout.flush()

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

def utc_iso():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")

def write_header(f, i, pre):
    # ... inside your acquisition loop, right after you queried WAV:PRE? ...
    pre = i.query(":WAV:PRE?").split(",")
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

    loc = RigolUsbLocator(verbose=False); loc.refresh()
    osc = loc.get_oscilloscope()
    i = osc.instrument
    i.timeout = 60000           # 60 s
    i.chunk_size = 1024*1024    # 1 MiB
    i.read_termination = ''     # binary
    i.write_termination = '\n'

    i.write(":RUN") # setting memory depth is only reliable in run mode
    # i.write(f":ACQ:MDEP {MEMORY_DEPTH}")
    i.write(":CHAN1:DISP ON; :CHAN2:DISP OFF; :CHAN3:DISP OFF; :CHAN4:DISP OFF")
    i.write(":ACQ:TYPE NORM")
    # i.write(f":TIM:SCAL {TIME_SCALE}") # 1 sample per nanosecond is the upper limit of the instrument

    with open(FILE_PATH, "wb", buffering=1024*1024) as f:
        for MEMORY_DEPTH in MEMORY_DEPTHS_TO_TEST:
            i.write(":RUN") # setting memory depth is only reliable in run mode
            i.write(f":ACQ:MDEP {MEMORY_DEPTH}")
            TIME_SCALE = MEMORY_DEPTH / (POINTS_PER_SECOND * 12 * 2)
            i.write(f":TIM:SCAL {TIME_SCALE}") # 1 sample per nanosecond is the upper limit of the instrument

            for idx in range(RUNS):
                i.write(":SING")
                wait_for_trigger_stop(i)
                i.write(":STOP")
                i.write(":WAV:SOUR CHAN1")
                i.write(":WAV:MODE RAW")
                i.write(":WAV:POIN:MODE RAW")
                i.write(":WAV:FORM BYTE")
                i.write(":WAV:BYTE LSBF") #explicitly state
                pre = i.query(":WAV:PRE?").split(",")
                acquired_points = int(pre[2]) # don't use int(i.query(":WAV:POIN?")) since it has 250k ceiling
                # print(f'DEBUG: total pts: {acquired_points}')

                write_header(f, i, pre)
                f.flush()

                # read_bytes = 0 #debug
                start = 1
                start_time = time.perf_counter()
                while start <= acquired_points:
                    # draw_progress_bar(start, acquired_points)

                    stop = min(start + CHUNK - 1, acquired_points) # stop idex is included, therefore subtract 1
                    i.write(f":WAV:STAR {start}")
                    i.write(f":WAV:STOP {stop}")

                    block = i.query_binary_values(":WAV:DATA?", datatype="B", container=bytearray)
                    # block = read_wave_block(i)
                    f.write(block)
                    f.flush()

                    # read_bytes += len(block) #debug
                    start = stop + 1
                elapsed_time = time.perf_counter() - start_time
                perf_times[MEMORY_DEPTH].append(elapsed_time)
                # sys.stdout.write('\n')
                # print(f'DEBUG: finished reading {read_bytes} bytes')
                print(f"RUN {idx}: time elapsed: {elapsed_time:.6f} seconds")
            print(f"at {MEMORY_DEPTH} points the average time is {sum(perf_times[MEMORY_DEPTH])/len(perf_times[MEMORY_DEPTH])} seconds")
    osc.close()

if __name__ == "__main__":
    main()
