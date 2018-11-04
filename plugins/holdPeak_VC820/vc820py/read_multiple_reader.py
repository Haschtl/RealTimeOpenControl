#!/usr/bin/python
import csv
import getopt
import os
import stat
import sys
import threading
import time
from time import sleep
import reader

start_time = time.time() #unix time

cur_msg = {} #:store latest message from each source

def print_error(text):
    """
    Prefix text with Thread name and send to stderr
    """
    thread_name = str(threading.current_thread().getName())
    print('\r[%s] %s'%(thread_name,text),file=sys.stderr)

def store_message(message,source):
    cur_msg[str(source)] = message

def delete_message(source):
    try:
        del cur_msg[str(source)]
    except KeyError:
        pass

def handle_messages():
    messages = dict(cur_msg) #make working copy of dict to make sure values don't change
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

def usage():
    print("""Usage:

--csv <file>                Write recorded data as CSV to the specified file
--filewait <sec>            Set the wait time between values read from file
--source <device>[,<model>] Add source to read from. device must be either file or serial port
--no-stdout                 Don't print values on stdout
--rate <sec>                Read values every x seconds
--manual                    Take an additional value from stdin
--help                      Show this message
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
        parsed = arg.split(",")
        source = parsed[0]
        try:
            model = parsed[1]
        except IndexError:
            model = "vc820"
        sources.append(reader.Source(source,model))
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
    readthread = reader.ThreadedReader(source,value_callback=store_message,error_callback=delete_message,filewait=filewait)
    readthreads.append(readthread)
    readthread.start()
    print_error("Thread %s started"%source)

try:
    i = 0
    sleep(1)
    no_values = False

    start_time = time.time() #unix time

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
    for thread in readthreads:
        thread.stop()
