#!/usr/bin/python
import os
import sys
import threading
import stat
import time

import serial

def print_thread_err(text):
    """
    Prefix text with Thread name and send to stderr
    """
    thread_name = str(threading.current_thread().getName())
    print('\r[%s] %s'%(thread_name,text),file=sys.stderr)


class Source:
    def __init__(self,path,model="vc820"):
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

        self.MultimeterMessage = __import__(model).MultimeterMessage
        self.model = model
        self.path = path

    def __str__(self):
        return self.model+"["+self.path+"]"

    def __repr__(self):
        return "Source(path="+self.path+",model="+self.model+")"

class Reader():
    def __init__(self,source,message_handler=None,raw_handler=None,filewait=0.5,quiet=False):
        self.quiet = quiet
        self.source = source
        self.message_handler = message_handler
        self.raw_handler = raw_handler
        self.filewait = filewait

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

    def print(self, *args,**kwargs):
        if not self.quiet:
            print(*args,**kwargs)

    def read_one(self):
        while True:
            test = self.serial_port.read(1)
            if len(test) != 1:
                if self.source.type == "file":
                    return #EOF
                raise Exception("recieved incomplete data")
            if self.source.MultimeterMessage.check_first_byte(test[0]):
                data = test + self.serial_port.read(self.source.MultimeterMessage.MESSAGE_LENGTH-1)
            else:
                self.print("received incorrect data (%s), skipping..."%test.hex(), file=sys.stderr)
                continue
            if len(data) != self.source.MultimeterMessage.MESSAGE_LENGTH:
                self.print("received incomplete message (%s), skipping..."%data.hex(), file=sys.stderr)
                continue
            return self.source.MultimeterMessage(data)

    def start(self):
        while True:
            test = self.serial_port.read(1)
            if len(test) != 1:
                if self.source.type == "file":
                    return #EOF
                self.print("recieved incomplete data, skipping...", file=sys.stderr)
                continue
            if self.source.MultimeterMessage.check_first_byte(test[0]):
                data = test + self.serial_port.read(self.source.MultimeterMessage.MESSAGE_LENGTH-1)
                if self.raw_handler is not None:
                    self.raw_handler(data,self.source)
            else:
                if self.raw_handler is not None:
                    self.raw_handler(test,self.source)
                self.print("received incorrect data (%s), skipping..."%test.hex(), file=sys.stderr)
                continue
            if len(data) != self.source.MultimeterMessage.MESSAGE_LENGTH:
                self.print("received incomplete message (%s), skipping..."%data.hex(), file=sys.stderr)
                continue
            try:
                message = self.source.MultimeterMessage(data)
            except ValueError as e:
                self.print("Error decoding: %s on message %s"%(str(e),data.hex()))
                continue
            if self.message_handler(message,self.source) == "exit":
                break
            if self.source.type == "file":
                time.sleep(filewait)


class ThreadedReader(threading.Thread):
    def __init__(self,source,value_callback=None,error_callback=None,filewait=0.5):
        threading.Thread.__init__(self)
        self.source = source
        self.setName(str(self.source))
        self.stop_flag = False
        self.value_callback = value_callback
        self.error_callback = error_callback
        self.filewait = filewait

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

    def stop(self):
        self.stop_flag = True

    def run(self):
        while True:
            if self.stop_flag:
                return
            if self.source.type == "file":
                time.sleep(self.filewait)

            test = self.serial_port.read(1) #read one byte, used for determining if message is valid
                                            #blocking if using fifo, times out if using serial port
            if len(test) != 1:
                if self.source.type == "file":
                    if self.error_callback is not None:
                        self.error_callback(source)
                    print_thread_err("EOF reached")
                    exit(0) #EOF
                print_thread_err("recieved incomplete data, skipping...")
                if self.error_callback is not None:
                    self.error_callback(self.source)
                continue

            if self.source.MultimeterMessage.check_first_byte(test[0]):
                data = test + self.serial_port.read(self.source.MultimeterMessage.MESSAGE_LENGTH-1) #looks good, read the remaining message
            else:
                print_thread_err("received incorrect data (%s), skipping..."%test.hex())
                if self.error_callback is not None:
                    self.error_callback(self.source)
                continue

            if len(data) != self.source.MultimeterMessage.MESSAGE_LENGTH:
                print_thread_err("received incomplete message (%s), skipping..."%data.hex())
                if self.error_callback is not None:
                    self.error_callback(source)
                continue

            try:
                message = self.source.MultimeterMessage(data)
            except ValueError as e:
                print_thread_err("Error decoding: %s on message %s"%(str(e),data.hex()))
                if self.error_callback is not None:
                    self.error_callback(self.source)
                continue

            if self.value_callback is not None:
                self.value_callback(message,self.source)
