@echo off
REM NICE Power Supply Controller Launcher
REM Can be run from anywhere in CMD

cd /d "%~dp0"
python nice_power_controller.py %*
pause
