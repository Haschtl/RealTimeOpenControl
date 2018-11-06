# from multiprocessing.connection import Client
import traceback
#import socket
#import json
import jsonsocket
import pickle
import time

class LoggerPlugin:
    def __init__(self, stream=None, plot = None, event=None):
        # Plugin setup
        self.setDeviceName()
        self.dataY = [0]                 # Array containing different data-streams
        self.dataX = [None]
        self.dataunits = ['']           # Represents the unit of the current data
        self.datanames = ['']     # Names for every data-stream
        self.__cb = stream
        self.__ev = event
        self.__plt = plot
        self.sock = None
        # -------------
        self.run = False  # False -> stops thread
        self.smallGUI = False
        self.xy = False

    def stream(self, *args, **kwargs):
        if self.__cb:
            y = kwargs.get('y', [0])
            for idx, arg in enumerate(args):
                if idx == 0:
                    y = arg
            kwargs['x'] = [time.time()]*len(y)
            self.__cb(*args, **kwargs)

    def plot(self, x=[], y=[], *args, **kwargs):
        dataname = kwargs.get('sname', "noName")
        devicename = kwargs.get('dname', "noDevice")
        dataunit = kwargs.get('unit', "")
        for idx, arg in enumerate(args):
            if idx == 0:
                dataname = arg
            if idx == 1:
                devicename = arg
            if idx == 2:
                dataunit = arg

        if y == []:
            y = x
            x = list(range(len(x)))

        if self.__plt:
            self.__plt(x, y, dataname, devicename, dataunit)
        else:
            print("No event connected")

    def event(self, *args, **kwargs): # text="", dataname=None, devicename=None, xpos=None):
        text = kwargs.get('text', "")
        dataname = kwargs.get('sname', None)
        devicename = kwargs.get('dname', None)
        xpos = kwargs.get('x', None)
        priority = kwargs.get('priority', 0)
        for idx, arg in enumerate(args):
            if idx == 0:
                text = arg
            if idx == 1:
                dataname = arg
            if idx == 2:
                devicename = arg
            if idx == 3:
                xpos = arg
            if idx == 4:
                priority = arg

        if dataname == None:
            if len(self.datanames) != 0:
                dataname = self.datanames[0]
            else:
                dataname = "unknownEvent"
        if devicename == None:
            devicename = self.deviceName
        if self.__ev:
            self.__ev(text, dataname, devicename, xpos, priority)
        else:
            print("No event connected")

    # def createClient(self, address = 'localhost'):
    #     self.client = Client((address, 5056))

    def createTCPClient(self, address="localhost"):
        # self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # # Connect the socket to the port where the server is listening
        # server_address = (socket.gethostname(), 5055)
        # self.sock.connect(server_address)
        self.tcpaddress = address
        self.sock = jsonsocket.Client()
        #self.sock.connect(address, 5055)
        #client.close()

    def sendTCP(self, *args, **kwargs):
        dataY = kwargs.get('y', None)
        datanames = kwargs.get('sname', None)
        devicename = kwargs.get('dname', self.devicename)
        dataunits = kwargs.get('unit', None)
        dataX = kwargs.get('x', None)
        signals = kwargs.get('getSignal', None)
        events = kwargs.get('getEvent', None)
        signallist = kwargs.get('getSignalList', False)
        plot = kwargs.get('plot', False)
        event = kwargs.get('event', None)
        remove = kwargs.get('remove', None)

        for idx, arg in enumerate(args):
            if idx == 0:
                dataY = arg
            if idx == 1:
                datanames = arg
            if idx == 2:
                devicename = arg
            if idx == 3:
                dataunits = arg
            if idx == 4:
                dataX = arg

        if dataX == None and dataY != None and not plot:
            dataX = [time.time()]*len(dataY)
        dicti = {}
        if dataY != None:
            dicti['plot']=plot
            dicti['y']=dataY
            dicti['x']=dataX
            dicti['sname']=datanames
            dicti['dname']=devicename
            dicti['unit']=dataunits
        if signallist:
            dicti['getSignallist']=True
        if event != None:
            dicti['event']=event
        if events != None:
            dicti['getEvent']=events
        if signals != None:
            dicti['getSignal']=signals
        if remove != None:
            dicti['remove'] = remove

        #data=pickle.dumps(list(dicti))

        if self.sock and self.run:
            try:
                self.sock.connect(self.tcpaddress, 5050)
                self.sock.send(dicti)
                response = self.sock.recv()
                self.sock.close()
                return response
            except:
                tb = traceback.format_exc()
                print(tb)
                print("Error sending over TCP")
                self.sock = jsonsocket.Client()
                return False
        else:
            print("Please createTCPClient first")
            return False

    # def sendData(self, *args, **kwargs):
    #     dataY = kwargs.get('y', [1])
    #     datanames = kwargs.get('sname', ["noName"])
    #     devicename = kwargs.get('dname', "noDevice")
    #     dataunits = kwargs.get('unit', [""])
    #     dataX = kwargs.get('x', [time.time()]*len(dataY))
    #     for idx, arg in enumerate(args):
    #         if idx == 0:
    #             dataY = arg
    #         if idx == 1:
    #             datanames = arg
    #         if idx == 2:
    #             devicename = arg
    #         if idx == 3:
    #             dataunits = arg
    #         if idx == 4:
    #             dataX = arg
    #
    #     if self.client and self.run:
    #         try:
    #             self.client.send([dataY,  datanames, devicename, dataunits, dataX])
    #             # print(self.client.recv())
    #         except:
    #             tb = traceback.format_exc()
    #             print(tb)
    #     elif self.run:
    #         print("Please call 'self.createClient()' before running self.sendData()!")

    def setDeviceName(self, devicename="noDevice"):
        self.devicename = devicename    # Is shown in GUI

    def close(self):
        self.run = False
        if self.widget:
            self.widget.hide()
            self.widget.close()
        #if self.client:
        #    self.client.close()
        #if self.sock:
            #self.sock.close()
