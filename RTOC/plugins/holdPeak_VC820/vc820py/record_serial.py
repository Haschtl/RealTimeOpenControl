#!/usr/bin/python
import serial
import time
import csv
import sys
from pprint import pprint
from vc820 import MultimeterMessage
import json
import getopt


serialportname = None
outfile = None

opts, args = getopt.getopt(sys.argv[1:], "", ["outfile=", "serialport="])
for opt,arg in opts:
    if opt == "--outfile":
        outfile = open(arg, "wb")
    elif opt == "--serialport":
        serialportname = arg

if serialportname is None or outfile is None:
    print("error")
    exit(1)

serial_port = serial.Serial(serialportname, baudrate=2400, parity='N', bytesize=8, timeout=1, rtscts=1, dsrdtr=1)
serial_port.dtr = True
serial_port.rts = False

while True:
    data = serial_port.read(1)
    if len(data) != 1:
        print("no data received", file=sys.stderr)
        continue
    print(data.hex())
    outfile.write(data)
    outfile.flush()
