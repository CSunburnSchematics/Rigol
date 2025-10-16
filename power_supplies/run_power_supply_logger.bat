@echo off
REM Run power supply continuous logger (no GUI)
REM Usage: run_power_supply_logger.bat [config_file] [output_directory]
REM Default config: GAN_HV_TESTCONFIG.json
REM Default output: C:/Users/andre/Claude/rad_test_data

setlocal

REM Set defaults
set CONFIG=%1
set OUTPUT_DIR=%2

if "%CONFIG%"=="" set CONFIG=GAN_HV_TESTCONFIG.json
if "%OUTPUT_DIR%"=="" set OUTPUT_DIR=C:/Users/andre/Claude/rad_test_data

echo ============================================================
echo Power Supply Continuous Logger
echo ============================================================
echo Config: %CONFIG%
echo Output: %OUTPUT_DIR%
echo ============================================================
echo.

cd /d "%~dp0"
python power_supply_continuous_logger.py %CONFIG% %OUTPUT_DIR%

pause
