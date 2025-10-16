@echo off
REM Final Radiation Testing Script Runner
REM This script can be run from anywhere and will automatically navigate to the correct directory

cd /d C:\Users\andre\Claude\Rigol\oscilloscope
python ./scripts/final_rad_testing_script.py ./configs/GAN_HV_TESTCONFIG.json C:/Users/andre/Claude/rad_test_data
