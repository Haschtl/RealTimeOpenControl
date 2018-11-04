#!/usr/bin/python
import serial
import time
import csv
import sys
from pprint import pprint
import json
import getopt

def store_message(message,elapsed_time):
    if save_csv:
        csv_writer.writerow([elapsed_time,message.value*message.multiplier,message.base_unit,message.mode,message.hold,message.rel])
        csvfile.flush()
    if save_rawtime:
        rawtimefile.write(str(elapsed_time)+" "+message.raw_message.hex()+"\n")
    if save_json:
        f = open(jsonfile, "w")
        f.write(message.get_json())
        f.close()



#huge fucking mess
#TODO: split into smaller functions
def handle_message(message): 
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
                print("WARNING, THRESHOLD CROSSED")
                if stop_on_threshold:
                    exit(0)
                under_threshold = (threshold > message.base_value)
                over_threshold = (threshold < message.base_value)

def usage():
    print("""Usage:

--csv <file>            Write recorded data as CSV to the specified file
--raw <file>            Write raw recorded data to the specified file
--rawtime <file>        Write the timedelta and the hex representation of the message to the specified file
--currentjson <file>    Write the decoded message in JSON format to the specified file each time a new message is received
--debug <file>          Debug mode. Read values from specified file instead of serial port
--filewait <sec>        Set the wait time between values in debug mode
--serialport <device>   Specify the serial port to be used. Defaults to /dev/ttyUSB0
--threshold <number>    Warn if base reading crosses this value
--stop-on-threshold     Stop if threshold is crossed
--base                  Print values in the base unit
--help                  Show this message
    """)

save_csv = False
csvfile = None

save_raw = False
rawfile = None

save_rawtime = False
rawtimefile = None

save_json = False
jsonfile = None

#default value
portname = "/dev/ttyUSB0"

debug = False
debugfile = None
debugwait = 0.5

threshold = None
stop_on_threshold = False

base = False

model = "vc820"

#start parsing arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["csv=", "raw=", "rawtime=", "currentjson=", "debug=", "serialport=", "help", "filewait=", "threshold=", "base", "stop-on-threshold", "model="])
except getopt.GetoptError as e:
    print(e)
    usage()
    exit(1)

for opt,arg in opts:
    if opt == "--csv":
        save_csv = True
        csvfile = open(arg, "w")
    elif opt == "--raw":
        save_raw = True
        rawfile = open(arg, "wb")
    elif opt == "--rawtime":
        save_rawtime = True
        rawtimefile = open(arg, "w")
    elif opt == "--currentjson":
        save_json = True
        jsonfile = arg
    elif opt == "--debug":
        debug = True
        debugfile = arg
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
    elif opt == "--model":
        model = arg
#stop parsing arguments

exec("from "+model+" import MultimeterMessage")

start_time = time.time()

if save_csv:
    csv_writer = csv.writer(csvfile, 'excel-tab')
    csv_writer.writerow(["#Time [s]", "Value", "Unit", "Modus", "Hold", "Relative"])

if not debug:
    serial_port = serial.Serial(portname, baudrate=2400, parity='N', bytesize=8, timeout=1, rtscts=1, dsrdtr=1)
    #dtr and rts settings required for adapter
    serial_port.dtr = True
    serial_port.rts = False
else:
    serial_port = open(debugfile, "rb")

under_threshold = None
over_threshold = None

while True:
    test = serial_port.read(1)
    if len(test) != 1:
        if debug:
            exit(0) #EOF
        print("recieved incomplete data, skipping...", file=sys.stderr)
        continue
    if MultimeterMessage.check_first_byte(test[0]):
        data = test + serial_port.read(MultimeterMessage.MESSAGE_LENGTH-1)
        if save_raw:
            rawfile.write(data)
    else:
        if save_raw:
            rawfile.write(test)
        print("received incorrect data (%s), skipping..."%test.hex(), file=sys.stderr)
        continue
    if len(data) != MultimeterMessage.MESSAGE_LENGTH:
        print("received incomplete message (%s), skipping..."%data.hex(), file=sys.stderr)
        continue
    try:
        message = MultimeterMessage(data)
    except ValueError as e:
        print("Error decoding: %s on message %s"%(str(e),data.hex()))
        continue
    handle_message(message)
    if debug:
        time.sleep(debugwait)
