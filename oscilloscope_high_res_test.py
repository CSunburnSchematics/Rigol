import os, time, sys, struct, json
from datetime import datetime, timezone
from rigol_usb_locator import RigolUsbLocator

OUT_DIR = "Tests"
RUNS = float("inf")
HDR_FMT = "<4sH I Q I f f f f f f B B 6x"   # 4+2+4+8+4+4*6+1+1+6 = 48 B
"""
Header fields:
  MAGIC (4s): b"RGOL" - file format identifier
  VER (H): format version number (currently 1)
  N (I): number of samples for this channel
  t0_ns (Q): absolute trigger timestamp in nanoseconds (Unix epoch)
  dt_ps (I): time between samples in picoseconds (from XINC)
  XINC (f): seconds per sample (e.g., 4e-9 = 4ns)
  XOR (f): X-axis origin offset (usually 0)
  XREF (f): X-axis reference point (usually 0)
  YINC (f): volts per ADC count - voltage conversion factor
  YOR (f): Y-axis origin offset
  YREF (f): Y-axis reference point
  chan (B): channel number (1-4)
  flags (B): reserved for future use
  pad (6x): 6 bytes padding for alignment
Voltage formula: voltage = (raw_byte - YREF - YOR) * YINC
"""
MAGIC, VER = b"RGOL", 1

def wait_for_trigger_stop(i, max_attempts=2000, query_cooldown=0.005):
    """Wait until trigger fires and acquisition completes. Returns timestamp when ready."""
    for _ in range(max_attempts):
        state = i.query(":TRIG:STAT?").strip().upper()
        if state == "STOP":
            return time.time_ns()
        elif state == "WAIT":
            i.write(":TFOR")
            return time.time_ns()
        time.sleep(query_cooldown)
    raise TimeoutError(f"Trigger timed out after {max_attempts} attempts") 

def write_header(f, pre, chan, t0_ns):
    XINC = float(pre[4]); XOR = float(pre[5]); XREF = float(pre[6])
    YINC = float(pre[7]); YOR = float(pre[8]); YREF = float(pre[9])
    dt_ps = int(round(XINC * 1e12))
    acquired_points = int(pre[2])
    hdr = struct.pack(HDR_FMT, MAGIC, VER, acquired_points, t0_ns, dt_ps,
                    XINC, XOR, XREF, YINC, YOR, YREF, chan, 0)
    f.write(hdr)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Get device address and config file from command line
    osc_address = sys.argv[1] if len(sys.argv) > 1 else None
    config_file = sys.argv[2] if len(sys.argv) > 2 else "default_config.json"
    config_path = os.path.join("Configs", config_file)

    # Load config
    with open(config_path, 'r') as f:
        config = json.load(f)

    if osc_address:
        from Rigol_DS1054z import RigolOscilloscope
        osc = RigolOscilloscope(osc_address)
        # Extract serial from address: USB0::0x1AB1::0x04CE::DS1A123456::INSTR
        serial = osc_address.split("::")[3] if "::" in osc_address else "unknown"
    else:
        loc = RigolUsbLocator(verbose=False); loc.refresh()
        osc = loc.get_oscilloscope()
        serial = "auto"

    # Get oscilloscope config by serial
    osc_config = config["oscilloscopes"]["rigol"].get(serial)
    if not osc_config:
        print(f"ERROR: No config found for oscilloscope {serial}")
        return

    # Get settings from config
    MEMORY_DEPTH = osc_config["memory_depth"]
    TIME_SCALE = osc_config["time_scale"]
    CHUNK = config["test_settings"]["chunk_size"]

    i = osc.instrument
    i.timeout = 60000           # 60 s
    i.chunk_size = 1024*1024    # 1 MiB
    i.read_termination = ''     # binary
    i.write_termination = '\n'

    i.write(":RUN") # setting memory depth is only reliable in run mode

    # Configure channels from config
    ch_scales = [osc_config["channels"][str(ch)]["scale"] for ch in range(1, 5)]
    ch_probes = [osc_config["channels"][str(ch)]["probe"] for ch in range(1, 5)]
    i.write(":CHAN1:DISP ON; :CHAN2:DISP ON; :CHAN3:DISP ON; :CHAN4:DISP ON")
    i.write(f":CHAN1:SCAL {ch_scales[0]}; :CHAN2:SCAL {ch_scales[1]}; :CHAN3:SCAL {ch_scales[2]}; :CHAN4:SCAL {ch_scales[3]}")
    i.write(f":CHAN1:PROB {ch_probes[0]}; :CHAN2:PROB {ch_probes[1]}; :CHAN3:PROB {ch_probes[2]}; :CHAN4:PROB {ch_probes[3]}")
    i.write(":ACQ:TYPE NORM")

    # Set time scale FIRST, then memory depth (scope may auto-adjust based on memory)
    i.write(f":TIM:SCAL {TIME_SCALE}")
    i.write(f":ACQ:MDEP {MEMORY_DEPTH}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"osc_{serial}_{timestamp}.bin"
    FILE_PATH = os.path.join(OUT_DIR, filename)
    print(f"Output file: {FILE_PATH}")

    idx = 0
    with open(FILE_PATH, "ab", buffering=1024*1024) as f:
        while idx < RUNS:
            i.write(":SING")
            trigger_time_ns = wait_for_trigger_stop(i)
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

                write_header(f, pre, chan, trigger_time_ns)

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
