import sys, os, struct, numpy as np, csv
from oscilloscope_high_res_test import HDR_FMT, MAGIC

HDR_SZ = struct.calcsize(HDR_FMT)

def read_header_at(f, off):
    f.seek(off)
    buf = f.read(HDR_SZ)
    if len(buf) < HDR_SZ:
        return None
    magic, ver, N, t0_ns, dt_ps, XINC, XOR, XREF, YINC, YOR, YREF, chan, flags = struct.unpack(HDR_FMT, buf)
    return (N, t0_ns, dt_ps, XINC, XOR, XREF, YINC, YOR, YREF, chan, flags) if magic == MAGIC else None

def extract_run(f, run_offsets):
    """Extract one complete run (all 4 channels) and return as dict."""
    channels = {}
    for chan in range(1, 5):
        if chan not in run_offsets:
            continue
        hdr = read_header_at(f, run_offsets[chan])
        if not hdr:
            continue
        N, t0_ns, dt_ps, XINC, XOR, XREF, YINC, YOR, YREF, _, _ = hdr
        f.seek(run_offsets[chan] + HDR_SZ)
        raw = np.fromfile(f, dtype=np.uint8, count=N)
        volts = (raw.astype(np.float32) - YREF - YOR) * YINC
        time_seconds = np.arange(N) * (dt_ps * 1e-12)
        channels[chan] = {'time': time_seconds, 'volts': volts, 't0_ns': t0_ns}
    return channels

def main():
    if len(sys.argv) < 2:
        print("Usage: python binary_to_csv_all.py <input.bin> [output.csv]")
        print("  Exports ALL runs from binary file to CSV")
        return

    bin_file = sys.argv[1]
    csv_file = sys.argv[2] if len(sys.argv) > 2 else bin_file.replace('.bin', '.csv')

    print(f"Reading: {bin_file}")

    with open(bin_file, "rb") as f:
        sz = os.path.getsize(bin_file)
        off = 0
        runs = []

        while off + HDR_SZ <= sz:
            hdr = read_header_at(f, off)
            if not hdr:
                break
            N, t0_ns = hdr[0], hdr[1]
            chan = hdr[9]
            data_end = off + HDR_SZ + N

            if sz >= data_end:
                if not runs or runs[-1][0] != t0_ns:
                    runs.append((t0_ns, {}))
                runs[-1][1][chan] = off
                off = data_end
            else:
                break

        print(f"Found {len(runs)} run(s)")

        if not runs:
            print("No complete runs found")
            return

        print(f"Exporting ALL {len(runs)} runs to: {csv_file}")

        total_samples = 0
        with open(csv_file, 'w', newline='') as csvf:
            writer = csv.writer(csvf)
            writer.writerow(['Time_s', 'CH1_V', 'CH2_V', 'CH3_V', 'CH4_V'])

            cumulative_time = 0.0
            for run_idx, (t0_ns, run_offsets) in enumerate(runs):
                channels = extract_run(f, run_offsets)
                max_samples = max(len(channels[ch]['volts']) for ch in channels)

                for i in range(max_samples):
                    row = []
                    time_val = channels[1]['time'][i] if 1 in channels and i < len(channels[1]['time']) else i * 1e-9
                    row.append(f"{(cumulative_time + time_val):.12e}")
                    for ch in range(1, 5):
                        if ch in channels and i < len(channels[ch]['volts']):
                            row.append(f"{channels[ch]['volts'][i]:.6f}")
                        else:
                            row.append('')
                    writer.writerow(row)

                dt = channels[1]['time'][1] if 1 in channels and len(channels[1]['time']) > 1 else 1e-9
                cumulative_time += max_samples * dt
                total_samples += max_samples

        print(f"Wrote {total_samples:,} samples. Done!")

if __name__ == "__main__":
    main()
