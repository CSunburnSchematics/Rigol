import os, time, sys
from datetime import datetime, timezone
from rigol_usb_locator import RigolUsbLocator

OUT_DIR = "Tests"
FILE_PATH = os.path.join(OUT_DIR, 'oscilloscope_binary_capture.bin')
RUNS = 10
PROGRESS_BAR_CHAR_LENGTH = 25
CHUNK = 250_000
MEMORY_DEPTH = 24_000_000

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
            print("DEBUG: waited for trigger stop for ", time.time() - start, " seconds")
            return
        elif state == "WAIT":
            i.write(":TFOR")
            print("DEBUG: force triggered after ", time.time() - start, " seconds")
            return
        time.sleep(query_cooldown)
    raise TimeoutError(f"Waiting for Trigger STOP. timed out after {wait_treshold} seconds.") 

def read_wave_block(i, expected_len=None):
    i.write(":WAV:DATA?")
    raw = i.read_raw()
    if not raw or raw[:1] != b'#':
        raise IOError("Bad IEEE block header")
    nd = int(raw[1:2])                  # digits in length field
    n = int(raw[2:2+nd])                # payload size in bytes
    off = 2 + nd
    payload = raw[off:off+n]
    while len(payload) < n:             # finish partial read if backend split it
        payload += i.read_bytes(n - len(payload))
    if expected_len is not None and n != expected_len:
        raise IOError(f"Size mismatch: got {n}, expected {expected_len}")
    return payload


def utc_iso():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")

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
    i.write(f":ACQ:MDEP {MEMORY_DEPTH}")
    i.write(":CHAN1:DISP ON; :CHAN2:DISP OFF; :CHAN3:DISP OFF; :CHAN4:DISP OFF")
    i.write(":ACQ:TYPE NORM")
    i.write(f":TIM:SCAL 0.0005") # 1 sample per nanosecond is the upper limit of the instrument

    with open(FILE_PATH, "ab", buffering=1024*1024) as f:
        for idx in range(RUNS):
            i.write(":SING")
            wait_for_trigger_stop(i)
            i.write(":STOP")
            i.write(":WAV:SOUR CHAN1")
            i.write(":WAV:MODE RAW")
            i.write(":WAV:POIN:MODE RAW")
            i.write(":WAV:FORM BYTE")
            i.write(":WAV:BYTE LSBF") #explicitly state
            acquired_points = int(i.query(":WAV:PRE?").split(",")[2]) # don't use int(i.query(":WAV:POIN?")) since it has 250k ceiling
            print(f'DEBUG: total pts: {acquired_points}')

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

                # read_bytes += len(block) #debug
                start = stop + 1
            elapsed_time = time.perf_counter() - start_time
            # sys.stdout.write('\n')
            # print(f'DEBUG: finished reading {read_bytes} bytes')
            print(f"RUN {idx}: time elapsed: {elapsed_time:.6f} seconds")
    osc.close()

if __name__ == "__main__":
    main()