import sys
import os
import time
import traceback
import json
import csv
import xlsxwriter
import importlib
from threading import Thread
from collections import deque
import numpy as np
#from multiprocessing.connection import Listener
import socket

import plugins
import data.lib.general_lib as lib
from data.loggerlib import *
from data.ScriptFunctions import ScriptFunctions
import data.scriptLibrary as rtoc
import jsonsocket
from LoggerPlugin import LoggerPlugin

class RTLogger(ScriptFunctions):
    def __init__(self):
        #sys.setrecursionlimit(1500)
        self.run = True
        self.config = {}
        self.load_config()
        # self.plugins={}
        self.pluginObjects = {}  # dict with all plugins
        self.pluginFunctions = {}
        self.pluginParameters = {}
        self.pluginStatus = {}
        self.maxLength = self.config["defaultRecordLength"]
        self.latestSignal = []
        self.devicenames = []
        for finder, name, ispkg in iter_namespace(plugins):
            if name not in ["plugins.Template", "plugins.LoggerPlugin"]:
                self.devicenames += [name]
        #print("Available devices")
        #[print("- "+name.replace("plugins.", "")) for name in self.devicenames]
        #print("")

        self.signals = []
        self.signalNames = []
        self.signalUnits = []
        self.signalIDs = []
        self.events = []

        self.triggerExpressions = []
        self.triggerValues = []

        # self.__server = Thread(target=self.multiprocessingListener)    # Actualize data
        # self.__server.start()

        #self.tcp = jsonsocket.Server("localhost",self.config["tcpPort"])
        self.tcp = None
        self.toggleTcpServer(self.config['tcpserver'])

        self.clearSignals()
        self.callback = None
        self.newSignalCallback = None
        #self.newSignal = None
        self.scriptExecutedCallback = None
        self.handleScriptCallback = None
        self.clearCallback = None

        self.tcpclient = LoggerPlugin(None,None,None)

    def toggleTcpServer(self, value = None):
        if value == None:
            value = self.config['tcpserver']
        self.config['tcpserver'] = value
        if value:
            self.tcpRunning = True
            print("TCPServer gestartet")
            self.tcp = jsonsocket.Server("0.0.0.0",self.config["tcpPort"])
            self.__tcpserver = Thread(target=self.tcpListener)
            self.__tcpserver.start()
        else:
            self.tcpRunning = False
            print("TCPServer beendet")
            if self.tcp:
                self.tcp.close()

    def sendTCP(self, hostname="localhost", *args, **kwargs):
        self.tcpclient.createTCPClient(hostname)
        self.tcpclient.sendTCP(*args, **kwargs)

    # client
    # def multiprocessingChild(self, conn):
    #     while self.run:
    #         try:
    #             msg = conn.recv()
    #             # this just echos the value back, replace with your custom logic
    #             if type(msg) == list:
    #                 datasY = []
    #                 datanames = [""]
    #                 devicename = "noDevice"
    #                 callback = [""]
    #                 datasX = [None]
    #                 for idx, value in enumerate(msg):
    #                     if idx == 0:
    #                         datasY = value
    #                     elif idx == 1:
    #                         datanames = value
    #                     elif idx == 2:
    #                         devicename = value
    #                     elif idx == 3:
    #                         callback = value
    #                     elif idx == 4:
    #                         datasX = value
    #                 self.addDataCallback(datasY, datanames, devicename, callback, datasX, True)
    #                 msg = True
    #             else:
    #                 msg = False
    #             conn.send(msg)
    #         except EOFError:
    #             print("Error in reading")
    #             try:
    #                 conn.send(False)
    #             except:
    #                 print("... and in sending")
    #                 break

    def tcpListener(self):
        #while self.run:
        #self.tcp.listen()
        while self.tcpRunning:
            ans = {'error':False}
            try:
                self.tcp.accept()
                msg = self.tcp.recv()
                if type(msg) == dict:
                    if 'y' in msg.keys():
                        plot = msg.get('plot', False)
                        datasY = msg.get('y',[])
                        datanames = msg.get('sname',[""])
                        devicename = msg.get('dname',"noDevice")
                        unit = msg.get('unit',[""])
                        datasX = msg.get('x',None)
                        if devicename == None:
                            devicename = "noDevice"
                        if plot:
                            self.plot(datasX, datasY, datanames,devicename, unit)
                        else:
                            self.addDataCallback(datasY, datanames, devicename, unit, datasX, True)
                        ans['sent'] = True
                    if 'getSignallist' in msg.keys():
                        ans['signallist'] =self.signalNames
                    if 'event' in msg.keys():
                        self.addNewEvent(*msg['event'])
                    if 'getEvent' in msg.keys():
                        ans['events']={}
                        for device in msg['getEvent']:
                            dev=device.split('.')
                            sig = self.getEvents(self.getSignalId(dev[0],dev[1]))
                            ans['events'][device]= [list(sig[0]),list(sig[1])]
                    if 'getSignal' in msg.keys():
                        ans['signals']={}
                        for device in msg['getSignal']:
                            dev=device.split('.')
                            sig = self.getSignal(self.getSignalId(dev[0],dev[1]))
                            ans['signals'][device]= [list(sig[0]),list(sig[1])]
                    if 'remove' in msg.keys():
                        ans['remove']='Not implemented'
                    for key in msg.keys():
                        if key not in ans.keys():
                            ans[key]=msg[key]
                self.tcp.send(ans)
            except:
                tb = traceback.format_exc()
                print(tb)
                print("Error in TCP-Connection")
                ans['error']=True
                #self.tcp.send(ans)

    # server
    # def multiprocessingListener(self):
    #     address = ('127.0.0.1', self.config['multithreadingPort'])
    #     self.serv = Listener(address)
    #     while self.run:
    #         try:
    #             #serv = Listener(address)
    #             client = self.serv.accept()
    #             self.multiprocessingChild(client)
    #             # self.serv.close()
    #         except:
    #             print("multiprocessingListener died almost")


    # Plugin functions ############################################################

    def startPlugin(self, name, callback=None):
        # Starts the specified plugin and connects callback if possible
        try:
            name = 'plugins.' + name
            if name in self.devicenames:
                #self.plugins[name] = importlib.import_module(name)
                if callback is None:
                    self.pluginObjects[name] = importlib.import_module(
                        name).Plugin(self.addDataCallback, self.plot, self.addNewEvent)
                else:
                    self.pluginObjects[name] = importlib.import_module(
                        name).Plugin(callback, self.addNewEvent)
                self.analysePlugin(self.pluginObjects[name], name)
                self.pluginStatus[name] = "OK"
                print("PLUGIN: " + name+' connected\n')
                self.addNewEvent(text=self.tr("Plugin gestartet: ")+name.replace("plugins.",""),sname="", dname="RTOC", priority = 0)
                return True, ""
            else:
                print("PLUGIN not found: '"+str(name)+"'\n")
                return False, "PLUGIN not found: '"+str(name)+"'\n"
        except:
            tb = traceback.format_exc()
            self.pluginStatus[name] = tb
            print(tb)
            print("PLUGIN FAILURE\nCould not load Plugin '"+str(name)+"'\n")
            return False, tb

    def stopPlugin(self, name):
        # Stops the specified plugin
        try:
            name = 'plugins.' + name
            if name in self.pluginObjects.keys():
                #self.pluginObjects[name].run = False
                self.pluginStatus[name] = "STOPPED"
                self.pluginObjects[name].close()
                print("PLUGIN: " + name+' disconnected\n')
                self.addNewEvent(text=self.tr("Plugin gestoppt: ")+name.replace("plugins.",""),sname="", dname="RTOC", priority = 0)
            # else:
            #    print("Plugin "+name+" not loaded")
            return True
        except:
            tb = traceback.format_exc()
            self.pluginStatus[name] = tb
            print(tb)
            print("PLUGIN FAILURE\nCould not stop Plugin '"+str(name)+"'\n")
            return False

    def stop(self):
        # Stops all plugins
        self.run = False
        #self.serv.close()
        #self.__tcpserver.run = False
        self.tcpRunning = False
        if self.tcp:
            self.tcp.close()
        print("TCPServer beendet")
        # self.serv.close()
        for name in self.devicenames:
            self.stopPlugin(name.replace("plugins.", ""))

    def analysePlugin(self, object, name):
        # Adds public Plugin-functions and parameters to local attributes pluginFunctions and pluginParameters
        all = dir(object)
        name = name.replace("plugins.", "")
        for element in all:
            if str(element)[0] != "_":
                if callable(getattr(object, element)):
                    self.pluginFunctions[name+"."+element] = "self.pluginObjects['plugins." + \
                        name+"']."+getattr(object, element).__name__
                else:
                    self.pluginParameters[name+"." +
                                          element] = "self.pluginObjects['plugins."+name+"']."+str(element)

# Signal functions ############################################################

    def clearCB(self):
        if self.clearCallback:
            self.clearCallback()

        self.clear()
        time.sleep(1)

    def clear(self):
        self.signals = []
        self.signalNames = []
        self.signalUnits = []
        self.signalIDs = []
        self.events = []
        self.selectedTriggerSignals = []
        self.clearSignals()

    def clearSignals(self, newLength=None):
        # Change the size of the recording
        if newLength == None:
            newLength = self.maxLength
        else:
            self.maxLength = newLength
            self.config["defaultRecordLength"] = self.maxLength
        self.signals = [[deque([], newLength), deque([], newLength)]
                        for _ in range(len(self.signalNames))]
        self.signalUnits = [deque([], newLength) for _ in range(len(self.signalNames))]
        self.events = [[deque([], newLength), deque([], newLength), deque([], newLength)]
                       for _ in range(len(self.signalNames))]

    def resizeSignals(self, newLength=None):
        if newLength == None:
            newLength = self.maxLength
        else:
            self.maxLength = newLength
            self.config["defaultRecordLength"] = self.maxLength

        self.signals = [[deque(list(self.signals[idx][0]), newLength), deque(list(self.signals[idx][1]), newLength)]
                        for idx in range(len(self.signalNames))]
        self.signalUnits = [deque(list(self.signalUnits[idx]), newLength)
                            for idx in range(len(self.signalNames))]

        self.events = [[deque(list(self.events[idx][0]), newLength), deque(list(self.events[idx][1]), newLength), deque(list(self.events[idx][2]), newLength)]
                       for idx in range(len(self.signalNames))]

    def removeSignal(self, id):
        idx=self.signalIDs.index(id)
        if idx != -1:
            self.signalNames.pop(idx)
            self.signalIDs.pop(idx)
            self.signals.pop(idx)
            self.signalUnits.pop(idx)

        return idx

    def getNewID(self):
        newID = 0
        while newID in self.signalIDs or newID==0:
            newID += 1
        return newID

    def __addNewSignal(self, dataY, dataunit, devicename, dataname, dataX=None, createCallback=True):
        # Add a new signal-stream
        print("LOGGER: Adding signal: "+devicename+", "+dataname)
        newLength = self.maxLength
        self.signalNames += [[devicename, dataname]]
        newID = self.getNewID()
        self.signalIDs.append(newID)
        self.signals += [[deque([], newLength), deque([], newLength)]]
        self.events += [[deque([], newLength), deque([], newLength),deque([], self.maxLength)]]
        self.signalUnits += [deque([], newLength)]
        if self.newSignalCallback:
            #self.newSignal = [len(self.signalNames)-1, devicename, dataname, dataunit]
            self.newSignalCallback(newID, devicename, dataname, dataunit)
        self.addNewEvent(text=self.tr("Signal-Stream hinzugefügt: ")+dataname+"."+devicename,sname="", dname="RTOC", priority = 0)
        self.__addNewData(dataY, dataunit, devicename, dataname, dataX, createCallback)

    def __addNewData(self, dataY, dataunit, devicename, dataname, dataX=None, createCallback=True):
        # Add new data to a signal-stream
        # self.latestSignal.append([devicename,dataname])
        self.latestSignal = [devicename, dataname]
        idx = self.signalNames.index([devicename, dataname])
        if dataX is None:
            self.signals[idx][0].append(time.time())
        else:
            self.signals[idx][0].append(dataX)
        self.signals[idx][1].append(dataY)
        self.signalUnits[idx].append(dataunit)
        if self.handleScriptCallback:
            self.handleScriptCallback(devicename, dataname)
        if self.callback and createCallback:
            self.callback()

    def addNewEvent(self,  *args, **kwargs):
        strung = kwargs.get('text', "")
        dataname = kwargs.get('sname', "noName")
        devicename = kwargs.get('dname', "noDevice")
        x = kwargs.get('x', None)
        priority = kwargs.get('priority', 0)
        for idx, arg in enumerate(args):
            if idx == 0:
                strung = arg
            if idx == 1:
                dataname = arg
            if idx == 2:
                devicename = arg
            if idx == 3:
                x = arg
            if idx == 4:
                priority = arg

        if priority not in [0,1,2]:
            priority = 0

        callback = False
        if [devicename, dataname] not in self.signalNames:
            self.signalNames += [[devicename, dataname]]
            self.signals += [[deque([], self.maxLength), deque([], self.maxLength)]]
            newID = self.getNewID()
            self.signalIDs.append(newID)
            self.events += [[deque([], self.maxLength), deque([], self.maxLength), deque([], self.maxLength)]]
            self.signalUnits += [deque([], self.maxLength)]
            self.signals[self.signalNames.index([devicename, dataname])][0].append(time.time())
            self.signals[self.signalNames.index([devicename, dataname])][1].append(0)
            self.signalUnits[self.signalNames.index([devicename, dataname])].append("")
            callback = True
        idx = self.signalNames.index([devicename, dataname])
        if x == None:
            self.events[idx][0].append(time.time())
            x=time.time()
        else:
            self.events[idx][0].append(float(x))
        self.events[idx][1].append(strung)
        self.events[idx][2].append(priority)
        if self.newEventCallback:
            self.newEventCallback(x, strung, devicename, dataname, priority)
        if self.newSignalCallback and callback and (devicename!="RTOC"):
            #self.newSignal = [len(self.signalNames)-1, devicename, dataname, ""]
            self.newSignalCallback(newID, devicename, dataname, "")
        # if self.callbackEvent:
        #    self.callbackEvent()

    def tr(self, *args):
        return args

    def __plotNewSignal(self, x, y, dataunit, devicename, dataname, createCallback=False):
        # Add a new signal-stream
        print("LOGGER: Adding signalplot: "+devicename+", "+dataname)
        newLength = self.maxLength
        self.signalNames += [[devicename, dataname]]
        self.events += [[deque([], self.maxLength), deque([], self.maxLength),deque([], self.maxLength)]]
        self.signalIDs.append(self.getNewID())
        self.signals += [[deque([], newLength), deque([], newLength)]]
        self.signalUnits += [deque([], newLength)]
        self.__plotNewData(x, y, dataunit, devicename, dataname, createCallback)
        if self.newSignalCallback:
            #self.newSignal = [self.signalIDs[-1], devicename, dataname, dataunit]
            self.newSignalCallback(self.signalIDs[-1], devicename, dataname, dataunit)
        self.addNewEvent(text=self.tr("Signal-Plot hinzugefügt: ")+dataname+"."+devicename,sname="", dname="RTOC", priority = 0)

    def __plotNewData(self, x, y, dataunit, devicename, dataname, createCallback=False):
        # Add new data to a signal-stream
        # self.latestSignal.append([devicename,dataname])
        self.latestSignal = [devicename, dataname]
        idx = self.signalNames.index([devicename, dataname])
        self.signals[idx][0].clear()
        self.signals[idx][1].clear()
        self.signals[idx][0] = deque(x, self.maxLength)
        self.signals[idx][1] = deque(y, self.maxLength)
        if type(dataunit) == str:
            self.signalUnits[idx] = deque([dataunit]*len(x), self.maxLength)
        elif type(dataunit) == list:
            self.signalUnits[idx] = deque(dataunit, self.maxLength)
        else:
            print("no unit specified")
            self.signalUnits[idx] = deque([""]*len(x), self.maxLength)
        if self.handleScriptCallback:
            self.handleScriptCallback(devicename, dataname)
        if self.callback and createCallback:
            self.callback()

    def printSignals(self):
        # Prints the signals to console
        for idx, signal in enumerate(self.signals):
            print("Device: "+self.signalNames[idx][0]+", Signal: "+self.signalNames[idx][1])
            print("Timebase:")
            for data in self.signals[idx][0]:
                sys.stdout.write(str(round(data, 1))+'\t')
            print("\nData:")
            for data in self.signals[idx][1]:
                sys.stdout.write(str(round(data, 1))+'\t\t')
            print("\nUnits:")
            for data in self.signalUnits[idx]:
                sys.stdout.write(str(data)+'\t\t')
            print("")

    def getSignalId(self, devicename, dataname):
        curridx = -1
        for idx, value in enumerate(self.signalNames):
            if value[0] == devicename and value[1] == dataname:
                curridx = idx
                break
        if curridx != -1:
            return self.signalIDs[curridx]
        else:
            return -1


# Callback functions ##########################################################

    def addDataCallback(self, datasY=[], *args, **kwargs):
        datanames = kwargs.get('snames', [""])
        devicename = kwargs.get('dname', "noDevice")
        callback = kwargs.get('unit', [""])
        datasX = kwargs.get('x', [None])
        createCallback = kwargs.get("c", True)
        for idx, arg in enumerate(args):
            if idx == 0:
                datanames = arg
            if idx == 1:
                devicename = arg
            if idx == 2:
                callback = arg
            if idx == 3:
                datasX = arg
            if idx == 4:
                createCallback = arg

        if type(datasY) == list:
            if datasX == [None]:
                datasX = [None]*len(datasY)
            if callback == [""] or callback == None:
                callback = [""]*len(datasY)
            for idx, data in enumerate(datasY):
                if [devicename, datanames[idx]] in self.signalNames:
                    self.__addNewData(float(datasY[idx]),
                                      callback[idx], devicename, datanames[idx], datasX[idx], createCallback)
                else:
                    self.__addNewSignal(float(datasY[idx]),
                                        callback[idx], devicename, datanames[idx], datasX[idx], createCallback)
        elif type(datasY) == str:
            self.addNewEvent(datasY)

    def addData(self, data=0, *args, **kwargs):
        dataname = kwargs.get('sname', "noName")
        devicename = kwargs.get('dname', "noDevice")
        dataunit = kwargs.get('unit', "")
        createCallback = kwargs.get('c', False)
        for idx, arg in enumerate(args):
            if idx == 0:
                dataname = arg
            if idx == 1:
                devicename = arg
            if idx == 2:
                dataunit = arg
            if idx == 3:
                createCallback = arg

        try:
            if type(data) == list:
                if len(data) == 2:
                    if [devicename, dataname] in self.signalNames:
                        self.__addNewData(float(data[1]),
                                          dataunit, devicename, dataname, float(data[0]), createCallback)
                    else:
                        self.__addNewSignal(float(data[1]),
                                            dataunit, devicename, dataname, float(data[0]), createCallback)
                else:
                    print("Wrong data size")
            else:
                if [devicename, dataname] in self.signalNames:
                    self.__addNewData(data,
                                      dataunit, devicename, dataname, None, createCallback)
                else:
                    self.__addNewSignal(data,
                                        dataunit, devicename, dataname, None, createCallback)
        except:
            tb = traceback.format_exc()
            print(tb)
            print("SCRIPT FAILURE\nSignal not available")

    def plot(self, x=[], y=[], *args, **kwargs):
        dataname = kwargs.get('sname', "noName")
        devicename = kwargs.get('dname', "noDevice")
        dataunit = kwargs.get('unit', "")
        createCallback = kwargs.get('c', False)
        for idx, arg in enumerate(args):
            if idx == 0:
                dataname = arg
            if idx == 1:
                devicename = arg
            if idx == 2:
                dataunit = arg
            if idx == 3:
                createCallback = arg

        if y == []:
            y = x
            x = list(range(len(x)))
        try:
            if len(x) == len(y):
                if [devicename, dataname] in self.signalNames:
                    self.__plotNewData(x, y,
                                       dataunit, devicename, dataname, createCallback)

                else:
                    self.__plotNewSignal(x, y,
                                         dataunit, devicename, dataname, createCallback)
            else:
                print("Plotting aborted. len(x)!=len(y)")
        except:
            tb = traceback.format_exc()
            print(tb)
            print("SCRIPT FAILURE\nPlotting failed!")

# Other functions #########################################################

    def exportData(self, *args, **kwargs):
        filename = kwargs.get('filename', None)
        filetype = kwargs.get('filetype', "json")
        for idx, arg in enumerate(args):
            if idx == 0:
                filename = arg
            if idx == 1:
                filetype = arg

        if filename == None:
            filename = self.generateFilename()
        if filetype == "xlsx":
            self.exportXLSX(filename)
        elif filetype == "json":
            self.exportJSON(filename)
        else:
            self.exportCSV(filename)

    def generateFilename(self):
        minx = []
        maxx = []
        for signal in self.signals:
            minx.append(min(list(signal[0])))
        minx = max(minx)
        now = time.strftime("%d_%m_%y_%H_%M", time.localtime(minx))
        return str(now)

    def exportXLSX(self, filename):
        workbook = xlsxwriter.Workbook(filename+".xslx")

        worksheet = workbook.add_worksheet()
        row = -1
        col = -1

        jsonfile = {}
        jsonfile["maxLength"] = self.maxLength

        for key in jsonfile.keys():
            col = 0
            row += 1
            worksheet.write(row, col, key)
            if type(jsonfile[key]) == list:
                for item in jsonfile[key]:
                    col += 1
                    if np.isnan(item):
                        data = -1
                    worksheet.write(row, col, item)
            else:
                if np.isnan(jsonfile[key]):
                    jsonfile[key] = -1
                worksheet.write(row, col + 1, jsonfile[key])

        worksheet2 = workbook.add_worksheet()
        row = 0
        col = -1

        for signalname in self.signalNames:
            col += 1
            worksheet2.write(row, col, ".".join(signalname)+" X")
            col += 1
            worksheet2.write(row, col, ".".join(signalname) + " Y")
            col += 1
            worksheet2.write(row, col, "Einheit")
        row += 1
        col = -1
        for idx, signal in enumerate(self.signals):
            for xy in signal:
                col += 1
                row = 1
                for data in xy:
                    if np.isnan(data):
                        data = -1
                    worksheet2.write(row, col, data)
                    row += 1
            col += 1
            row = 1
            for data in self.signalUnits[idx]:
                if np.isnan(data):
                    data = -1
                worksheet2.write(row, col, data)
                row += 1

        workbook.close()

    def exportJSON(self, filename):
        jsonfile = {}
        jsonfile["maxLength"] = self.maxLength
        jsonfile["data"] = {}
        jsonfile["events"] = {}
        for idx, name in enumerate(self.signalNames):
            jsonfile["data"][".".join(name)] = []
            jsonfile["events"][".".join(name)] = []
            x = list(self.signals[idx][0])
            y = list(self.signals[idx][1])
            x = np.nan_to_num(x)
            for idx2, value in enumerate(x):
                if isinstance(value, np.generic):
                    x[idx2] = np.asscalar(value)
            y = np.nan_to_num(y)
            for idx2, value in enumerate(y):
                if isinstance(value, np.generic):
                    y[idx2] = np.asscalar(value)
            jsonfile["data"][".".join(name)].append(x.tolist())
            if len(self.signalUnits[idx]) == 0:
                self.signalUnits[idx].append("")
            jsonfile["data"][".".join(name)].append(y.tolist())
            jsonfile["data"][".".join(name)].append(self.signalUnits[idx][0])
            jsonfile["events"][".".join(name)].append(list(self.events[idx][0]))
            jsonfile["events"][".".join(name)].append(list(self.events[idx][1]))

        with open(filename+".json", 'w') as fp:
            json.dump(jsonfile, fp, sort_keys=False, indent=4, separators=(',', ': '))

    def restoreJSON(self, filename="restore.json"):
        try:
            if os.path.exists(filename):
                with open(filename) as f:
                    data = json.load(f)
                self.clear()
                self.maxLength = data["maxLength"]
                #self.events[0]=deque(data["events"][0], self.maxLength)
                #self.events[1]=deque(data["events"][1], self.maxLength)
                for signal in data["data"].keys():
                    name = signal.split(".")
                    if len(data["data"][signal][0]) != 0:
                        self.plot(data["data"][signal][0], data["data"][signal][1],
                                  name[1], name[0], data["data"][signal][2], False)
                for signal in data["events"].keys():
                    if signal != ".":
                        name = signal.split(".")
                        for idx, event in enumerate(data["events"][signal][0]):
                            self.addNewEvent(data["events"][signal][1][idx], name[1], name[0], event, data["events"][signal][2])
            return True
        except:
            tb = traceback.format_exc()
            print(tb)
            return False

    def exportCSV(self, filename):
        textfile = ''
        with open(filename+".csv", 'w', newline='') as myfile:
            wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
            for idx, sig in enumerate(self.signals):
                wr.writerow(sig[0])
                wr.writerow(sig[1])
                signame = '.'.join(self.signalNames[idx])
                textfile = textfile+signame+" X\n"+signame+" Y\n"
        with open(filename+".txt", 'w') as myfile:
            myfile.write(textfile)

    def exportSignal(self, filename, signal):
        x = list(signal[0])
        y = list(signal[1])
        with open(filename+".csv", 'w', newline='') as myfile:
            wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
            wr.writerow(signal[0])
            wr.writerow(signal[1])

    def load_config(self):
        self.lastEditedList = []
        with open("config.json", encoding="UTF-8") as jsonfile:
            self.config = json.load(jsonfile, encoding="UTF-8")
        newlist = []
        for path in self.config["lastSessions"]:
            if os.path.exists(path):
                newlist.append(path)
        self.config["lastSessions"] = newlist
        for lastpath in self.config["lastSessions"]:
            self.lastEditedList.append(lastpath)
        lib.logging('config loaded')

    def save_config(self):
        with open("config.json", 'w', encoding="utf-8") as fp:
            json.dump(self.config, fp,  sort_keys=False, indent=4, separators=(',', ': '))

    def getSignal(self, id):
        if id in self.signalIDs:
            idx = self.signalIDs.index(id)
            return self.signals[idx]
        else:
            return [[],[]]

    def getEvents(self, id):
        if id in self.signalIDs:
            idx = self.signalIDs.index(id)
            return self.events[idx]
        else:
            return [[],[],[]]

    def getSignalUnits(self, id):
        if id in self.signalIDs:
            idx = self.signalIDs.index(id)
            return self.signalUnits[idx]
        else:
            return []

    def getSignalNames(self, id):
        if id in self.signalIDs:
            idx = self.signalIDs.index(id)
            return self.signalNames[idx]
        else:
            return [[],[]]




if __name__ == "__main__":
    kl = RTLogger()
    time.sleep(1)
    kl.startPlugin('holdPeak_VC820')
    # time.sleep(2)
    kl.startPlugin('func_generator')
    # time.sleep(2)
    # kl.stopPlugin('func_generator')
