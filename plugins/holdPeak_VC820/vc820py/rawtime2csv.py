#!/usr/bin/python
import csv
from sys import stderr,stdout
import sys
from pprint import pprint
from vc820 import MultimeterMessage
import json

if len(sys.argv) != 2:
    print("wrong number of arguments")
    exit(1)

inputfile = open(sys.argv[1], "r")
outputfile = open(1,"w")

csvw = csv.writer(outputfile, 'excel-tab')
csvw.writerow(["#Time [s]", "Value", "Unit", "Modus", "Hold", "Relative"])

for line in inputfile:
    timestr,msgstr = line.split(" ")
    msg = MultimeterMessage(bytes.fromhex(msgstr.strip()))
    csvw.writerow([timestr,msg.value*msg.multiplier,msg.base_unit,msg.mode,msg.hold,msg.rel])
