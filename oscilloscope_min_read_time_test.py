# from rigol_usb_locator import RigolUsbLocator
# import time

# RUNS = 100

# def main():
#     loc = RigolUsbLocator(verbose=False)
#     loc.refresh()
#     osc = loc.get_oscilloscope()
#     i = osc.instrument

#     i.write(":RUN")
#     elapsed_times = []
#     for idx in range(RUNS):
#         start_time = time.perf_counter()
#         v = float(i.query(':MEAS:VRMS? CHAN1'))
#         elapsed_time = time.perf_counter() - start_time
#         elapsed_times.append(elapsed_time)
#         print(f"voltage: {v}")
#         time.sleep(0.01)
#     average_time = sum(elapsed_times) / len(elapsed_times)
#     print(f"average elapased time: {average_time} seconds")

# if __name__ == "__main__":
#     main()







from rigol_usb_locator import RigolUsbLocator
import time

RUNS = 1000

def main():
    loc = RigolUsbLocator(verbose=False)
    loc.refresh()
    osc = loc.get_oscilloscope()
    i = osc.instrument

    # --- One-time config ---
    i.write(':WAV:SOUR CHAN1')
    i.write(':WAV:POIN:MODE NORM')   # stable on-screen points; fastest for single-point pulls
    i.write(':WAV:FORM BYTE')        # 1 byte per sample
    i.write(':CHAN1:OFFS 0')         # optional: center offset so YORIG ≈ 0
    i.write(':RUN')

    # One-time: get scaling + last index
    pre = i.query(':WAV:PRE?').strip().split(',')
    # FORMAT,TYPE,POINTS,COUNT,XINCR,XORIG,XREF,YMULT,YORIG,YOFF
    YMULT = float(pre[7]); YORIG = float(pre[8]); YOFF = float(pre[9])

    N = int(i.query(':WAV:POIN?'))   # number of points in NORM mode (~600)
    i.write(f':WAV:STAR {N}')
    i.write(f':WAV:STOP {N}')        # lock to the last on-screen point

    # --- Tight loop: 1 command per iteration ---
    elapsed_times = []
    for _ in range(RUNS):
        start_time = time.perf_counter()

        b = i.query_binary_values(':WAV:DATA?', datatype='B', container=list)[0]  # one byte
        v = (b - YOFF) * YMULT + YORIG                                           # volts

        elapsed_times.append(time.perf_counter() - start_time)
        print(f"voltage: {v}")

        # Optional tiny pause to avoid hammering the VISA stack:
        # time.sleep(0.001)

    avg = sum(elapsed_times) / len(elapsed_times)
    print(f"average elapsed time: {avg} seconds")

if __name__ == "__main__":
    main()