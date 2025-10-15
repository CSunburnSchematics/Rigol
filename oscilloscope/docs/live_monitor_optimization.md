# Live Monitor Optimization Guide

## Timeout Errors and Performance Issues

The timeout errors (`VI_ERROR_TMO`) occur when the oscilloscope is busy or USB communication gets congested. This is normal behavior for USB-based instruments.

## Optimizations Applied

### 1. Increased Scope Stabilization Delay
- **Changed**: `time.sleep(0.1)` → `time.sleep(0.2)` after `:RUN` command
- **Why**: Gives oscilloscope more time to stabilize before requesting data
- **Location**: `capture_waveform()` function

### 2. Increased USB Timeout
- **Changed**: `scope.timeout = 5000` → `scope.timeout = 10000` (5s → 10s)
- **Why**: Allows more time for slow USB transfers
- **Location**: `connect_scope()` function

### 3. Reduced Plot Update Frequency
- **Added**: Plot updates only every 3 captures instead of every capture
- **Why**: Reduces matplotlib overhead and window lag
- **Effect**: Window responds faster, less "frozen" appearance
- **Location**: `capture_and_update()` function

### 4. Increased Capture Interval
- **Changed**: `capture_interval=0.3` → `capture_interval=0.5` (300ms → 500ms)
- **Why**: Gives scope more time between captures to process data
- **Effect**: Fewer timeout errors, more reliable capturing
- **Location**: `main()` function call to `monitor.run()`

### 5. Longer Error Recovery Delay
- **Changed**: Error delay from `2x` to `3x` the normal interval
- **Why**: Gives scope more time to recover after timeout errors
- **Effect**: Better recovery from error conditions
- **Location**: `run()` method

## Expected Performance After Optimization

### Before:
- Frequent timeout errors (every 2-3 captures)
- Window lag/freezing during plot updates
- Unreliable capture rate

### After:
- Fewer timeout errors (expect ~1 every 5-10 captures)
- Smoother window updates
- More consistent capture rate
- ~2 captures per second effective rate

## Fine-Tuning Parameters

You can adjust these in the code:

### Capture Interval
```python
monitor.run(duration_sec=60, capture_interval=0.5)
```
- **Decrease** (e.g., 0.4s) for faster capturing (more timeout risk)
- **Increase** (e.g., 0.7s) for more reliable capturing (slower data rate)

### Plot Update Frequency
```python
self.update_every = 3  # Update plot every N captures
```
- **Decrease** (e.g., 2) for more frequent visual updates (more lag)
- **Increase** (e.g., 5) for smoother window response (less frequent updates)

### Timeout Duration
```python
scope.timeout = 10000  # milliseconds
```
- **Increase** if you still see timeouts
- **Decrease** if captures are too slow

## CSV Data Integrity

**Important**: Even when timeout errors occur, all successfully captured data is saved to CSV immediately. The CSV flush happens after each capture, so you won't lose data even if the script crashes.

## Recommended Usage

For best results:
1. Start with the default optimized settings
2. Monitor the console output for timeout frequency
3. If timeouts are still frequent (>30% of captures), increase `capture_interval` to 0.7s
4. If window is still laggy, increase `update_every` to 5

## Known Limitations

- USB-TMC protocol has inherent latency (~200-300ms per transfer)
- Screen buffer limited to 1,200 points per capture
- Deep memory (RAW mode) not reliable over USB with PyVISA-py
- Windows USB stack can introduce additional delays

## Alternative Approaches

If timeout errors persist:
1. **Use Ethernet/LAN connection** instead of USB (requires VXI-11)
2. **Switch to NI-VISA** instead of PyVISA-py (commercial drivers)
3. **Reduce sample points** by adjusting timebase on oscilloscope
4. **Use slower timebase** settings on the oscilloscope itself
