# Oscilloscope Capture Configuration Files

This directory contains JSON configuration files for the oscilloscope data capture scripts.

## Usage

Run the configurable capture script with a config file:
```bash
python live_4ch_configurable.py <config_file.json>
```

If no config file is specified, it will use `default_capture_config.json`.

## Available Configurations

### `default_capture_config.json`
Standard 4-channel capture at 1ms/div timebase with 120 points per channel.
- Timebase: 1ms/div
- Points per channel: 120
- Probe attenuation: 10x
- Scale: 1V/div per channel
- Duration: 30 seconds (configurable via display)

### `high_speed_capture_config.json`
High-speed capture optimized for faster sampling with fewer points.
- Timebase: 1us/div
- Points per channel: 30
- Probe attenuation: 10x
- Scale: 1V/div per channel
- Duration: 60 seconds
- Faster display updates (100ms vs 50ms)

## Configuration Structure

```json
{
  "capture_settings": {
    "duration_seconds": 30,              // Not used in real-time (manual stop)
    "points_per_channel": 120,           // Number of samples per channel
    "capture_mode": "RAW",               // WAVeform mode (RAW or NORMAL)
    "update_interval_ms": 50,            // Plot update interval
    "max_display_time_seconds": 10,      // Scrolling window size
    "max_points_per_channel": 10000      // Rolling buffer size
  },
  "oscilloscope": {
    "timeout_ms": 1000,                  // VISA timeout
    "chunk_size": 102400,                // VISA chunk size
    "timebase_seconds": 0.001,           // Time per division (1ms)
    "run_mode": "RUN",                   // RUN or STOP
    "channels": {
      "1": {
        "enabled": true,                 // Enable/disable channel
        "scale_volts_per_div": 1.0,      // Vertical scale (V/div)
        "offset_volts": 0.0,             // Vertical offset
        "probe_attenuation": 10,         // Probe setting (1x, 10x, 100x)
        "coupling": "DC"                 // DC or AC coupling
      },
      // ... channels 2-4
    }
  },
  "output": {
    "csv_enabled": true,                 // Save to CSV
    "csv_path": "../../data",            // CSV output directory
    "csv_prefix": "live_4ch",            // CSV filename prefix
    "screenshot_enabled": true,          // Save screenshot on exit
    "screenshot_path": "../../plots",    // Screenshot output directory
    "screenshot_prefix": "live_4ch_screenshot"  // Screenshot filename prefix
  },
  "display": {
    "figure_width": 18,                  // Plot width in inches
    "figure_height": 14,                 // Plot height in inches
    "histogram_bins": 50,                // Number of histogram bins
    "show_stats": true,                  // Show statistics panel
    "show_histogram": true,              // Show voltage histogram
    "show_detail_waveforms": true,       // Show last N waveforms
    "detail_waveform_count": 10          // Number of waveforms to overlay
  }
}
```

## Creating Custom Configurations

1. Copy an existing config file
2. Modify the values according to your needs
3. Save with a descriptive name (e.g., `my_test_config.json`)
4. Run: `python live_4ch_configurable.py my_test_config.json`

## Tips

- **Faster capture**: Reduce `points_per_channel` to 30 or 50
- **More coverage**: Use smaller timebase (e.g., 1us instead of 1ms)
- **Memory optimization**: Adjust `max_points_per_channel` for longer runs
- **Performance**: Increase `update_interval_ms` if plotting is slow
- **Different signal ranges**: Adjust `scale_volts_per_div` and `offset_volts`
- **High-voltage probes**: Set `probe_attenuation` to 100 for 100x probes

## Example: Quick Single-Channel Test

To quickly test just channel 1:
```json
"channels": {
  "1": { "enabled": true, ... },
  "2": { "enabled": false, ... },
  "3": { "enabled": false, ... },
  "4": { "enabled": false, ... }
}
```
