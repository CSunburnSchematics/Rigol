# tail_plot.py
import sys, os, time, struct, numpy as np, matplotlib.pyplot as plt, matplotlib.dates as mdates
from datetime import datetime, timezone
from oscilloscope_high_res_test import HDR_FMT, MAGIC

PATH = sys.argv[1] if sys.argv[1] else os.path.join("Tests", "oscilloscope_binary_capture.bin")
print(PATH)
HDR_SZ = struct.calcsize(HDR_FMT)
BINS, WIN = 2048, 2_000_000

def read_header_at(f, off):
    f.seek(off); buf = f.read(HDR_SZ)
    if len(buf) < HDR_SZ: return None
    magic, ver, N, t0_ns, dt_ps, XINC, XOR, XREF, YINC, YOR, YREF, chan, flags = struct.unpack(HDR_FMT, buf)
    if magic != MAGIC: return None
    return N, t0_ns, dt_ps, XINC, XOR, XREF, YINC, YOR, YREF, chan, flags

def main():
    with open(PATH, "rb") as f:
        while os.path.getsize(PATH) < HDR_SZ: time.sleep(0.2)
        hdr = f.read(HDR_SZ)
        MAGIC, ver, N, t0_ns, dt_ps, XINC, XOR, XREF, YINC, YOR, YREF, chan, flags = struct.unpack(HDR_FMT, hdr)
        if MAGIC != b"RGOL": return
        dt = dt_ps * 1e-12
        t0_num = mdates.date2num(datetime.fromtimestamp(t0_ns / 1e9, tz=timezone.utc))
        
        dt_days = dt / 86400.0
        data_off = HDR_SZ

        plt.ion()
        fig, ax = plt.subplots()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S.%f', tz=timezone.utc))
        fig.autofmt_xdate()
        (ln_min,) = ax.plot([], [], lw=0.8)
        (ln_max,) = ax.plot([], [], lw=0.8)
        ax.set_ylabel("V")

        while True:
            sz = os.path.getsize(PATH)
            raw_avail = max(0, sz - data_off)

            # if current run finished, see if a new header is present right after it
            if raw_avail >= N and sz >= (data_off + N + HDR_SZ):
                nxt = read_header_at(f, data_off + N)  # parse 48-B header at next offset
                if nxt:
                    off = data_off + N
                    N, t0_ns, dt_ps, XINC, XOR, XREF, YINC, YOR, YREF, chan, flags = nxt
                    data_off = off + HDR_SZ
                    dt = dt_ps * 1e-12
                    t0_num = mdates.date2num(datetime.fromtimestamp(t0_ns/1e9, tz=timezone.utc))
                    dt_days = dt / 86400.0
                    continue

            avail = min(N, raw_avail)
            if avail == 0: time.sleep(0.2); continue
            
            n = min(WIN, avail)
            f.seek(data_off + (avail - n))
            raw = np.fromfile(f, dtype=np.uint8, count=n)
            v = (raw.astype(np.float32) - YREF - YOR) * YINC

            step = max(1, n // BINS)
            m = (n // step) * step
            seg = v[:m].reshape(-1, step)
            vmin = seg.min(1); vmax = seg.max(1)

            start_sample = avail - m
            idx = start_sample + (np.arange(vmin.size) + 0.5) * step
            x = t0_num + idx * dt_days

            ln_min.set_data(x, vmin); ln_max.set_data(x, vmax)
            ax.relim(); ax.autoscale_view()
            plt.pause(0.1)

if __name__ == "__main__":
    main()