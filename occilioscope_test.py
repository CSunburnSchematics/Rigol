import shutil
import pyvisa
import datetime
import time
import csv
import os
import argparse
from Rigol_DS1054z import RigolOscilloscope

OSCILLOSCOPE_ADDRESS = "USB0::0x1AB1::0x04CE::DS1ZA192006991::INSTR"
rm = pyvisa.ResourceManager()

oscilloscope = RigolOscilloscope(OSCILLOSCOPE_ADDRESS)

oscilloscope.check_connection()
oscilloscope.trigger_single()
oscilloscope.capture_screenshot("osc_3_test_pic.png")
oscilloscope.trigger_run()
oscilloscope.close()

