@echo off
REM NICE Power Supply COM Port Verification and Remapping
REM Run this after power cycles or USB reconnections

echo ============================================================
echo NICE Power Supply COM Port Verification
echo ============================================================
echo.
echo This script will:
echo  1. Detect all NICE Power supplies
echo  2. Set COM ports to test voltages (2V, 6V, 8V)
echo  3. Tell you which COM port displays which voltage
echo  4. Ask you to identify which device is showing that voltage
echo  5. Update all config files automatically
echo.
echo Press Ctrl+C to cancel, or
pause

cd /d "%~dp0"
python verify_and_remap_nice_power.py
pause
