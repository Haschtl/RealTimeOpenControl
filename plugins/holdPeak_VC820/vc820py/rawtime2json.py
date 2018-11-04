#!/usr/bin/python
import csv
from sys import stderr,stdout
import sys
from pprint import pprint
from vc820 import MultimeterMessage
import json

values_list = []

if len(sys.argv) != 2:
    print("wrong number of arguments")
    exit(1)

inputfile = open(sys.argv[1], "r")

dictlist = []

lasttime = 0

for line in inputfile:
    timestr,msgstr = line.split(" ")
    message = MultimeterMessage(bytes.fromhex(msgstr.strip()))
    time = float(timestr)
    deltatime = time - lasttime
    lasttime = time
    mdict =   { "reading": message.get_reading(),
                "base_reading": message.get_base_reading(),
                "mode": message.mode,
                "battery_low": message.batlow,
                "hold": message.hold,
                "relative": message.rel,
                "autorange": message.auto,
                "raw_message": message.raw_message.hex(),
                "time": time,
                "deltatime": deltatime,
                "value": message.value,
                "unit": message.unit,
                "diode_test": message.diode }
    dictlist.append(mdict)

print(json.dumps(dictlist, indent=1))
