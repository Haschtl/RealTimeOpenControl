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

inputfile = open(sys.argv[1], "rb")

while True:
    test = inputfile.read(1)
    if len(test) != 1:
        break #EOF reached
    if (test[0]&0b11110000) == 0b00010000: #check if first nibble is 0x01
        data = test + inputfile.read(13)
    else:
        print("received incorrect byte, skipping...", file=stderr)
        continue
    message = MultimeterMessage(data)
    values_list.append(message)

human_readable_list = []
for message in values_list:
    mdict =   { "reading": message.get_reading(),
                "base_reading": message.get_base_reading(),
                "mode": message.mode,
                "battery_low": message.batlow,
                "hold": message.hold,
                "relative": message.rel,
                "autorange": message.auto,
                "raw_message": message.raw_message.hex(),
                "value": message.value,
                "unit": message.unit,
                "diode_test": message.diode }
    human_readable_list.append(mdict)

print(json.dumps(human_readable_list, indent=4))
