import shutil
import pyvisa
import datetime
import time
import csv
import os
import argparse



LOAD_ADDRESS = "USB0::0x1AB1::0x0E11::DL3B262800287::INSTR"

current = 0

rm = pyvisa.ResourceManager()

load = rm.open_resource(LOAD_ADDRESS)


load.write(":FUNC CURR")

if current > 4:
    try:
        print("setting current range to 40 A")
        load.write(":INPUT OFF")
        load.write(":CURR:RANG 40")
        
    except Exception as e:
        print(f"Error setting current range: {e}")
else:
    try:
        print("setting current range to 4 A")
        load.write(":INPUT OFF")
        load.write(":CURR:RANG 4")
        
    except Exception as e:
        print(f"Error setting current range: {e}")

load.write(f":CURR {current:.3f}") 
load.write(":INPUT ON")
                    
