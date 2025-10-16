#!/usr/bin/env python3
import sys, os, struct, numpy as np, csv
from datetime import datetime, timezone
from oscilloscope_high_res_test import HDR_FMT, MAGIC

HDR_SZ = struct.calcsize(HDR_FMT)

def read_header_at(f, off):
    f.seek(off)
    buf = f.read(HDR_SZ)
    if len(buf) < HDR_SZ:
        return None
    unpacked = struct.unpack(HDR_FMT, buf)
    if unpacked[0] != MAGIC:
        return None
    (
        _magic, ver, N, t0_ns, dt_ps, XINC, XOR, XREF,
        YINC, YOR, YREF, chan, flags
    ) = unpacked
    return {
        "ver": int(ver), "N": int(N), "t0_ns": int(t0_ns), "dt_ps": int(dt_ps),
        "XINC": float(XINC), "XOR": float(XOR), "XREF": float(XREF),
        "YINC": float(YINC), "YOR": float(YOR), "YREF": float(YREF),
        "chan": int(chan), "flags": int(flags),
    }

def build_run_index(f, file_size):
    """
    Return list of runs: [(t0_ns, {chan: header_offset}), ...]
    Only include channel segments whose header+data fully fit within the file.
    """
    runs = []
    off = 0
    while off + HDR_SZ <= file_size:
        h = read_header_at(f, off)
        if not h:
            break
        data_end = off + HDR_SZ + h["N"]
        if data_end > file_size:
            # Truncated tail; stop scanning
            break
        if not runs or runs[-1][0] != h["t0_ns"]:
            runs.append((h["t0_ns"], {}))
        runs[-1][1][h["chan"]] = off
        off = data_end
    return runs

def extract_run_channels(f, run_offsets):
    """
    Read all present channels for a given run and return:
      channels[ch] = { 'volts': np.float32[N], 'dt_ps': int }
    Uses exact Rigol conversion: V = (raw - YREF)*YINC + YOR
    """
    channels = {}
    for ch in range(1, 5):
        off = run_offsets.get(ch)
        if off is None:
            continue
        h = read_header_at(f, off)
        if not h:
            continue
        N = h["N"]
        f.seek(off + HDR_SZ)
        raw = np.fromfile(f, dtype=np.uint8, count=N)
        volts = (raw.astype(np.float32) - h["YREF"]) * h["YINC"] + h["YOR"]
        channels[ch] = {"volts": volts, "dt_ps": h["dt_ps"]}
    return channels

def pick_dt_ps(channels):
    """Pick dt_ps from any present channel; warn if inconsistent."""
    present = sorted(channels.keys())
    if not present:
        return None
    dt = channels[present[0]]["dt_ps"]
    for ch in present[1:]:
        if channels[ch]["dt_ps"] != dt:
            sys.stderr.write(
                f"WARNING: dt_ps differs across channels in a run; using CH{present[0]}={dt} ps\n"
            )
            break
    return dt

def main():
    if len(sys.argv) < 2:
        print("Usage: python binary_to_csv_all.py <input.bin> [output.csv]")
        return

    bin_file = sys.argv[1]
    csv_file = sys.argv[2] if len(sys.argv) > 2 else bin_file.replace(".bin", ".csv")

    with open(bin_file, "rb") as f:
        file_size = os.path.getsize(bin_file)
        runs = build_run_index(f, file_size)
        if not runs:
            print("No complete runs found")
            return

        print(f"Found {len(runs)} run(s)")
        total = 0

        with open(csv_file, "w", newline="") as csvf:
            w = csv.writer(csvf)
            # Only UTC time + channel voltages
            w.writerow(["DateTime_UTC", "CH1_V", "CH2_V", "CH3_V", "CH4_V"])

            for (t0_ns, run_offsets) in runs:
                channels = extract_run_channels(f, run_offsets)
                if not channels:
                    continue

                dt_ps = pick_dt_ps(channels)
                if not dt_ps or dt_ps <= 0:
                    sys.stderr.write("WARNING: missing/invalid dt_ps; skipping run\n")
                    continue

                max_samples = max(len(channels[ch]["volts"]) for ch in channels)
                for i in range(max_samples):
                    # Integer math for exactness: abs_time_ns = t0_ns + (i * dt_ps) // 1000
                    abs_time_ns = t0_ns + (i * dt_ps) // 1000  # ps -> ns
                    dt = datetime.fromtimestamp(abs_time_ns / 1e9, tz=timezone.utc)

                    row = [dt.strftime("%Y-%m-%d %H:%M:%S.%f")]
                    for ch in range(1, 5):
                        if ch in channels and i < len(channels[ch]["volts"]):
                            row.append(f"{channels[ch]['volts'][i]:.6f}")
                        else:
                            row.append("")
                    w.writerow(row)
                    total += 1

    print(f"Wrote {total:,} rows to {csv_file}")

if __name__ == "__main__":
    main()
