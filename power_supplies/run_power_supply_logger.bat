@echo off
REM Run power supply continuous logger (no GUI)
REM Usage: run_power_supply_logger.bat [config_file] [output_directory] [sample_interval_ms]
REM Default config: ../../configs/GAN_HV_RAD_TEST.json
REM Default output: C:/Users/andre/Claude/rad_test_data
REM COM ports are specified in the config file

setlocal

REM Set defaults
set CONFIG=%1
set OUTPUT_DIR=%2
set SAMPLE_INTERVAL=%3

if "%CONFIG%"=="" set CONFIG=../../configs/GAN_HV_RAD_TEST.json
if "%OUTPUT_DIR%"=="" set OUTPUT_DIR=C:/Users/andre/Claude/rad_test_data
if "%SAMPLE_INTERVAL%"=="" set SAMPLE_INTERVAL=1000

echo ============================================================
echo Power Supply Continuous Logger
echo ============================================================
echo Config: %CONFIG%
echo Output: %OUTPUT_DIR%
echo Sample Interval: %SAMPLE_INTERVAL% ms
echo ============================================================
echo.

cd /d "%~dp0"
python power_supply_continuous_logger.py %CONFIG% %OUTPUT_DIR% %SAMPLE_INTERVAL%

pause
