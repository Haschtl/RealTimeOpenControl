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
outputfile = open(1,"wb")

for line in inputfile:
    timestr,msgstr = line.split(" ")
    outputfile.write(bytes.fromhex(msgstr.strip()))
