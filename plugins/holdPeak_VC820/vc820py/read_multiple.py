#!/usr/bin/python
import csv
import getopt
import os
import stat
import sys
import threading
import time
from time import sleep

import serial

from vc820 import MultimeterMessage

start_time = time.time() #unix time

cur_msg = {} #:store latest message from each source

stop_flag = False

def print_error(text):
    """
    Prefix text with Thread name and send to stderr
    """
    thread_name = str(threading.current_thread().getName())
    print('\r[%s] %s'%(thread_name,text),file=sys.stderr)


class Source:
    def __init__(self,path):
        if type(path) is not str:
            raise TypeError("Expecting str")

        if os.name == 'nt': #running on windows
            if os.path.exists(path):
                self.type = "file"
            else: #no file with this name, assuming serial port
                self.type = "serial"

        elif os.name == "posix": #Linux or Unix (including macOS)
            if stat.S_ISCHR(os.stat(path).st_mode): #Character device, assuming serial port
                self.type = "serial"
            elif stat.S_ISREG(os.stat(path).st_mode): #Regular file
                self.type = "file"
            elif stat.S_ISFIFO(os.stat(path).st_mode): #Pipe
                self.type = "pipe"
            else:
                raise TypeError("Unsupported input")

        self.path = path

    def __str__(self):
        return self.path

    def __repr__(self):
        return "Source(input="+self.path+")"


class ReadThread(threading.Thread):
    def __init__(self,source):
        threading.Thread.__init__(self)
        self.source = source
        self.setName(str(self.source))

        if source.type == "serial":
            self.serial_port = serial.Serial(source.path, baudrate=2400, parity='N', bytesize=8, timeout=1, rtscts=1, dsrdtr=1)
            #dtr and rts required for supplying adapter with power
            self.serial_port.dtr = True
            self.serial_port.rts = False
        elif source.type == "file" or source.type == "pipe":
            self.serial_port = open(source.path, "rb")
        else:
            #should never happen, prevented by Source.__init__()
            raise TypeError("Unsupported input")

    def _delete_value(self):
        try:
            del cur_msg[self.getName()]
        except KeyError:
            pass

    def run(self):
        while True:
            if stop_flag:
                return
            if source.type == "file":
                time.sleep(filewait)

            test = self.serial_port.read(1) #read one byte, used for determining if message is valid
                                            #blocking if using fifo, times out if using serial port
            if len(test) != 1:
                if source.type == "file":
                    self._delete_value() #prevent outdated values from hanging around
                    print_error("EOF reached")
                    exit(0) #EOF
                print_error("recieved incomplete data, skipping...")
                self._delete_value() #Multimeter has probably been turned off or disconnected
                continue

            if (test[0]&0b11110000) == 0b00010000: #check if first nibble is 0x1, if it isn't this is not the beginning of a valid message
                data = test + self.serial_port.read(13) #looks good, read the remaining message
            else:
                print_error("received incorrect data (%s), skipping..."%test.hex())
                self._delete_value()
                continue

            if len(data) != 14:
                print_error("received incomplete message (%s), skipping..."%data.hex())
                self._delete_value()
                continue

            try:
                message = MultimeterMessage(data)
            except ValueError as e:
                print_error("Error decoding: %s on message %s"%(str(e),data.hex()))
                self._delete_value()
                continue
            cur_msg[self.getName()] = message


def handle_messages():
    messages = cur_msg #make working copy of dict to make sure values don't change
    elapsed_time = round(time.time() - start_time, 4) #we don't need more than 4 digits
    printmsg = "%.4fs | "%elapsed_time

    #TODO: put in dedicated function
    if csvfile is not None:
        csv_dict = {"time": elapsed_time}
        for key,value in messages.items():
            if key == "manual":
                csv_dict.update({key:value})
            else:
                csv_dict.update({key:value.base_value})
        csvwriter.writerow(csv_dict)
        csvfile.flush()

    if output:
        for key,value in sorted(messages.items()):
            printmsg += str(value).strip()+" | "
        print(printmsg.strip())
        #sys.stdout.write("\r"+printmsg.strip()+"                   \b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b")
        #sys.stdout.flush()

def usage():
    print("""Usage:

--csv <file>            Write recorded data as CSV to the specified file
--filewait <sec>        Set the wait time between values read from file
--source <device>       Add source to read from. device must be either file or serial port
--no-stdout             Don't print values on stdout
--rate <sec>            Read values every x seconds
--manual                Take an additional value from stdin
--help                  Show this message
    """)

sources = []
readthreads = []

#default values
filewait = 0.5
mainwait = 0.5

csvfile = None

output = True

manual = False

valid_arguments = [ "source=", "help", "filewait=", "rate=", "csv=", "no-stdout", "manual" ]

try:
    opts, args = getopt.getopt(sys.argv[1:], "", valid_arguments)
except getopt.GetoptError as e:
    print(e)
    usage()
    exit(1)

for opt,arg in opts:
    if opt == "--source":
        sources.append(Source(str(arg)))
    elif opt == "--help":
        usage()
        exit(0)
    elif opt == "--filewait":
        filewait = float(arg)
    elif opt == "--rate":
        mainwait = float(arg)
    elif opt == "--csv":
        csvfile = open(arg, "w")
    elif opt == "--no-stdout":
        output = False
    elif opt == "--manual":
        manual = True

if len(sources) == 0:
    print_error("At least one Source is required")
    usage()
    exit(1)

if csvfile is not None:
    if manual:
        csvwriter = csv.DictWriter(csvfile, ["time", "manual"]+[ str(x) for x in sources], dialect="excel-tab")
    else:
        csvwriter = csv.DictWriter(csvfile, ["time"]+[ str(x) for x in sources], dialect="excel-tab")
    csvwriter.writeheader()

for source in sources:
    readthread = ReadThread(source)
    readthreads.append(readthread)
    readthread.start()
    print_error("Thread %s started"%source)

try:
    i = 0
    sleep(1)
    no_values = False

    #main loop
    while True:
        if manual:
            cur_msg["manual"] = float(input().replace(",","."))
        else:
            sleep(mainwait)
        if len(cur_msg) == 0:
            if no_values: #only exit if it occurrs a second time
                print_error("No values read, exiting...")
                break
            else:
                no_values = True
        handle_messages()
finally:
    stop_flag = True #signal Threads to stop
