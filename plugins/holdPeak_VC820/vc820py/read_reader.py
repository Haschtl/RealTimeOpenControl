#!/usr/bin/python
import time
import csv
import sys
from pprint import pprint
import json
import getopt
import subprocess

import reader

def store_message(message,elapsed_time):
    if csvfile is not None:
        csv_writer.writerow([elapsed_time,message.value*message.multiplier,message.base_unit,message.mode,message.hold,message.rel])
        csvfile.flush()
    if rawtimefile is not None:
        rawtimefile.write(str(elapsed_time)+" "+message.raw_message.hex()+"\n")
    if jsonfile is not None:
        f = open(jsonfile, "w")
        f.write(message.get_json())
        f.close()

def handle_threshold_crossed():
    print("WARNING, THRESHOLD CROSSED")
    if run_on_threshold is not None:
        subprocess.Popen(run_on_threshold, shell=True)
    if stop_on_threshold:
        exit(0)
    

#huge fucking mess
#TODO: split into smaller functions
def handle_message(message,source): 
    if base:
        print(message.get_base_reading())
    else:
        print(str(message))
    packet_time = time.time()
    elapsed_time = round(packet_time - start_time,4)

    store_message(message, elapsed_time)

    #threshold handling
    global under_threshold,over_threshold #necessary to prevent UnboundLocalError
    if threshold is not None:
        if under_threshold is None or over_threshold is None:
            under_threshold = (threshold > message.base_value)
            over_threshold = (threshold < message.base_value)
        else:
            if message.base_value == threshold:
                pass
            elif ((threshold < message.base_value) != over_threshold) or ((threshold > message.base_value) != under_threshold):
                handle_threshold_crossed()
                under_threshold = (threshold > message.base_value)
                over_threshold = (threshold < message.base_value)

def usage():
    print("""Usage:

--csv <file>                Write recorded data as CSV to the specified file
--raw <file>                Write raw recorded data to the specified file
--rawtime <file>            Write the timedelta and the hex representation of the message to the specified file
--currentjson <file>        Write the decoded message in JSON format to the specified file each time a new message is received
--filewait <sec>            Set the wait time between values when reading file
--serialport <device>       Specify the serial port to be used. Defaults to /dev/ttyUSB0
--model <model>             Set multimeter model. Defaults to vc820
--threshold <number>        Warn if base reading crosses this value
--stop-on-threshold         Stop if threshold is crossed
--run-on-threshold <cmd>    Run specified command when threshold is crossed
--base                      Print values in the base unit
--help                      Show this message
    """)

csvfile = None
rawfile = None
rawtimefile = None
jsonfile = None

#default value
portname = "/dev/ttyUSB0"

debug = False
debugfile = None
debugwait = 0.5

threshold = None
stop_on_threshold = False
run_on_threshold = None

base = False

model = "vc820"

#start parsing arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["csv=", "raw=", "rawtime=", "currentjson=", "serialport=", "help", "filewait=", "threshold=", "base", "stop-on-threshold", "model=", "run-on-threshold="])
except getopt.GetoptError as e:
    print(e)
    usage()
    exit(1)

for opt,arg in opts:
    if opt == "--csv":
        csvfile = open(arg, "w")
    elif opt == "--raw":
        rawfile = open(arg, "wb")
    elif opt == "--rawtime":
        rawtimefile = open(arg, "w")
    elif opt == "--currentjson":
        jsonfile = arg
    elif opt == "--serialport":
        portname = arg
    elif opt == "--filewait":
        debugwait = float(arg)
    elif opt == "--help":
        usage()
        exit(0)
    elif opt == "--threshold":
        threshold = float(arg)
    elif opt == "--base":
        base = True
    elif opt == "--stop-on-threshold":
        stop_on_threshold = True
    elif opt == "--run-on-threshold":
        run_on_threshold = arg
    elif opt == "--model":
        model = arg
#stop parsing arguments

start_time = time.time()

def save_raw(data,source):
    if rawfile is not None:
        rawfile.write(data)

meter = reader.Source(portname,model)
meterreader = reader.Reader(meter,message_handler=handle_message,filewait=debugwait,raw_handler=save_raw)

if csvfile is not None:
    csv_writer = csv.writer(csvfile, 'excel-tab')
    csv_writer.writerow(["#Time [s]", "Value", "Unit", "Modus", "Hold", "Relative"])

under_threshold = None
over_threshold = None

meterreader.start()
