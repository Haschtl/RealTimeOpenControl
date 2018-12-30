# LoggerPlugin v1.6
import traceback
import time
import sys
import os

try:
    from . import jsonsocket
except:
    import jsonsocket

import hashlib

class LoggerPlugin:
    def __init__(self, stream=None, plot=None, event=None):
        # Plugin setup
        self.setDeviceName()
        self.deviceName = "noDevice"
        self.datanames = ['']     # Names for every data-stream
        self.__cb = stream
        self.__ev = event
        self.__plt = plot
        self.sock = None
        # -------------
        self.run = False  # False -> stops thread
        self.smallGUI = False
        self.tcppassword = ''
        self.tcpport=5050
        self.tcpaddress=''
        self.xy = False
        self.widget = None

    def getDir(self, dir = None):
        if dir == None:
            dir = __file__
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/plugins'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(dir))

        return packagedir

    def stream(self, *args, **kwargs):
        if self.__cb:
            y = kwargs.get('y', [0])
            for idx, arg in enumerate(args):
                if idx == 0:
                    y = arg
            if type(y) == list:
                kwargs['x'] = [time.time()]*len(y)
            else:
                kwargs['x'] = [time.time()]
            self.__cb(*args, **kwargs)
        else:
            print('ERROR: cannot stream signals. No callback connected')

    def plot(self, x=[], y=[], *args, **kwargs):
        dataname = kwargs.get('sname', "noName")
        devicename = kwargs.get('dname', "noDevice")
        dataunit = kwargs.get('unit', "")
        hold = kwargs.get('hold', "off")
        autoResize = kwargs.get('autoResize', False)
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
            self.__plt(x, y, dataname, devicename, dataunit, hold=hold, autoResize=autoResize)
        else:
            print("No event connected")

    def event(self, *args, **kwargs):
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

        if dataname is None:
            if len(self.datanames) != 0:
                dataname = self.datanames[0]
            else:
                dataname = "unknownEvent"
        if devicename is None:
            devicename = self.deviceName
        if self.__ev:
            self.__ev(text, dataname, devicename, xpos, priority)
        else:
            print("No event connected")

    def createTCPClient(self, address="localhost", password=None, tcpport=5050):
        self.tcpaddress = address
        self.tcpport = tcpport
        self.sock = jsonsocket.Client()
        if password != None:
            self.tcppassword = password
            self.sock.setKeyword(password)

    def sendTCP(self, *args, **kwargs):
        dataY = kwargs.get('y', None)
        datanames = kwargs.get('sname', None)
        devicename = kwargs.get('dname', self.devicename)
        dataunits = kwargs.get('unit', None)
        dataX = kwargs.get('x', None)
        signals = kwargs.get('getSignal', None)
        latest = kwargs.get('getLatest', None)
        events = kwargs.get('getEvent', None)
        signallist = kwargs.get('getSignalList', False)
        eventlist = kwargs.get('getEventList', False)
        pluginlist = kwargs.get('getPluginList', False)
        plot = kwargs.get('plot', False)
        event = kwargs.get('event', None)
        remove = kwargs.get('remove', None)
        plugin = kwargs.get('plugin', None)
        logger = kwargs.get('logger', None)

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

        if dataX is None and dataY is not None and not plot:
            dataX = [time.time()]*len(dataY)
        dicti = {}
        if dataY is not None:
            dicti['plot'] = plot
            dicti['y'] = dataY
            dicti['x'] = dataX
            dicti['sname'] = datanames
            dicti['dname'] = devicename
            dicti['unit'] = dataunits
        if signallist:
            dicti['getSignalList'] = True
        if eventlist:
            dicti['getEventList'] = True
        if event is not None:
            dicti['event'] = event
        if events is not None:
            dicti['getEvent'] = events
        if signals is not None:
            dicti['getSignal'] = signals
        if latest is not None:
            dicti['getLatest'] = latest
        if remove is not None:
            dicti['remove'] = remove
        if plugin is not None:
            dicti['plugin'] = plugin
        if logger is not None:
            dicti['logger'] = logger
        if pluginlist:
            dicti['getPluginList'] = True
        #if self.tcppassword != '' and self.tcppassword != None:
            #hash_object = hashlib.sha256(self.tcppassword.encode('utf-8'))
            #hex_dig = hash_object.hexdigest()
            #dicti['password'] = hex_dig
        if self.sock:
            try:
                self.sock.connect(self.tcpaddress, self.tcpport, self.tcppassword)
                self.sock.send(dicti)
                response = self.sock.recv()
                self.sock.close()
                if response == None:
                #if 'password' in response.keys():
                    print('passwordprotected')
                    return None
                else:
                    return response
            except ConnectionRefusedError:
                print('TCP Connection refused')
                try:
                    self.sock.close()
                except:
                    pass
                return False
            except:
                tb = traceback.format_exc()
                print(tb)
                print("Error sending over TCP")
                try:
                    self.sock.close()
                except:
                    pass
                self.sock = jsonsocket.Client()
                return False
        else:
            print("Please createTCPClient first")
            self.createTCPClient()
            return False

    def setDeviceName(self, devicename="noDevice"):
        self.devicename = devicename    # Is shown in GUI

    def close(self):
        self.run = False
        if self.widget:
            self.widget.hide()
            self.widget.close()
        # if self.sock:
            # self.sock.close()
