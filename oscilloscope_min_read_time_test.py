from rigol_usb_locator import RigolUsbLocator
import time
import os

RUNS = 10
CHUNK_SIZES = [1, 10, 100, 1_000, 10_000, 100_000]
MEMORY_DEPTH = 12_000
POINTS_PER_SECOND = 1_000_000_000
TIME_SCALE = MEMORY_DEPTH / (POINTS_PER_SECOND * 12 * 2)
FILE_PATH = os.path.join("Tests", 'oscilloscope_min_read_capture.bin')

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

def main():
    loc = RigolUsbLocator(verbose=False)
    loc.refresh()
    osc = loc.get_oscilloscope()
    i = osc.instrument

    i.write(":RUN") # setting memory depth is only reliable in run mode
    i.write(f":ACQ:MDEP {MEMORY_DEPTH}")
    i.write(":CHAN1:DISP ON; :CHAN2:DISP OFF; :CHAN3:DISP OFF; :CHAN4:DISP OFF")
    i.write(":ACQ:TYPE NORM")
    i.write(f":TIM:SCAL {TIME_SCALE}") # 1 sample per nanosecond is the upper limit of the instrument

    # pre = i.query(':WAV:PRE?').strip().split(',')
    # YMULT = float(pre[7]); YORIG = float(pre[8]); YOFF = float(pre[9])

    with open(FILE_PATH, "ab", buffering=1024*1024) as f:
        for CHUNK_SIZE in CHUNK_SIZES:            
            i.write(":SING")
            # i.write(":TFOR")
            # wait_for_trigger_stop(i)
            i.write(":WAV:SOUR CHAN1")
            i.write(":WAV:MODE RAW")
            i.write(":WAV:POIN:MODE RAW")
            i.write(":WAV:FORM BYTE")
            i.write(":WAV:BYTE LSBF")

            i.write(f":WAV:STAR {1}")
            i.write(f":WAV:STOP {CHUNK_SIZE}")
            
            elapsed_times = []
            for _ in range(RUNS):
                start_time = time.perf_counter()
                block = i.query_binary_values(':WAV:DATA?', datatype='B', container=bytearray)
                f.write(block)
                # v = (block[0] - YOFF) * YMULT + YORIG
                # print(f"voltage: {v}")
                elapsed_times.append(time.perf_counter() - start_time)
            print(f"average dump time for {CHUNK_SIZE} points: {sum(elapsed_times)/len(elapsed_times)} seconds")

if __name__ == "__main__":
    main()