#self.addNewEventimport sys
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
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtCore import QObject
import sys
import subprocess
import hashlib
import pkgutil
from threading import Timer

try:
    from .data.lib import general_lib as lib
    from .data import loggerlib as loggerlib
    from .data.ScriptFunctions import ScriptFunctions
    from .data import scriptLibrary as rtoc
    from . import plugins
    from . import jsonsocket
    from .LoggerPlugin import LoggerPlugin
    from .telegramBot import telegramBot
except ImportError:
    from data.lib import general_lib as lib
    from data import loggerlib as loggerlib
    from data.ScriptFunctions import ScriptFunctions
    from data import scriptLibrary as rtoc
    import plugins
    import jsonsocket
    from LoggerPlugin import LoggerPlugin
    from telegramBot import telegramBot

userpath = os.path.expanduser('~')
if not os.path.exists(userpath):
    os.mkdir(userpath)
userpath = os.path.expanduser('~/.RTOC')
if not os.path.exists(userpath):
    os.mkdir(userpath)
if not os.path.exists(userpath+'/devices'):
    os.mkdir(userpath+'/devices')
sys.path.insert(0, userpath)
import devices


translate = QCoreApplication.translate

defaultconfig = {
    "language": "en",
    "lastSessions": [],
    "darkmode": True,
    "scriptWidget": True,
    "deviceWidget": True,
    "signalsWidget": True,
    "pluginsWidget": False,
    "eventWidget": True,
    "newSignalSymbols": True,
    "plotLabelsEnabled": True,
    "plotGridEnabled": True,
    "grid": [
        True,
        True,
        1.0
    ],
    "plotLegendEnabled": False,
    "blinkingIdentifier": False,
    "signalStyles": [],
    "defaultRecordLength": 500000,
    "plotRate": 8,
    "plotInverted": False,
    "xTimeBase": True,
    "timeAxis": True,
    "systemTray": False,
    "tcpserver": True,
    "defaultScriptSampleTime": 10,
    "lastScript": "",
    "signalInactivityTimeout": 2,
    "tcpPort": 5050,
    "telegram_bot": False,
    "telegram_name": "RTOC-Remote",
    "telegram_token": "",
    "telegram_eventlevel": 1,
    "telegram_chat_ids": [],
    "documentfolder": "",
    "rtoc_web": False,
    "tcppassword": '',
    "backupFile": '',
    "backupIntervall": 0,
    "csv_profiles":{}
}

class RTLogger(ScriptFunctions, QObject):
    def __init__(self, enableTCP=None, tcpport=None):
        self.run = True
        self.config = {}
        self.load_config()
        self.pluginObjects = {}  # dict with all plugins
        self.pluginFunctions = {}
        self.pluginParameters = {}
        self.pluginStatus = {}
        self.starttime = time.time()
        self.maxLength = self.config["defaultRecordLength"]
        self.latestSignal = []
        self.devicenames = {}
        self.getDeviceList()
        self.signals = []
        self.signalNames = []
        self.signalUnits = []
        self.signalIDs = []
        self.events = []
        self.triggerExpressions = []
        self.triggerValues = []

        self.tcp = None
        if enableTCP is not None:
            self.config['tcpserver'] = enableTCP
        if tcpport is not None:
            self.config["tcpPort"] = int(tcpport)

        self.toggleTcpServer(self.config['tcpserver'])

        self.clearSignals()
        self.callback = None
        self.newSignalCallback = None
        self.scriptExecutedCallback = None
        self.handleScriptCallback = None
        self.clearCallback = None
        self.newEventCallback = None
        self.startDeviceCallback = None
        self.stopDeviceCallback = None
        self.recordingLengthChangedCallback = None

        self.backupThread = None
        self.tcpclient = LoggerPlugin(None, None, None)
        self.rtoc_web = None

        if self.config['backupIntervall']>0:
            self.backupThread = Timer( self.config['backupIntervall'], self.exportJSON,  args=[self.config['backupFile']])
        self.telegramBot = telegramBot(self)
        self.toggleTelegramBot()
        self.toggleHTMLPage()
        self.load_autorun_plugins()
        #self.check_for_updates()

    def getDir(self, dir = None):
        if dir == None:
            dir = __file__
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(dir))

        return packagedir

    def getDeviceList(self):
        print("Default plugins:")
        for finder, name, ispkg in loggerlib.iter_namespace(plugins):
            namesplit = name.split('.')
            print(namesplit[-1])
            if namesplit[-1] not in ["LoggerPlugin"]:
                self.devicenames[namesplit[-1]] = name
                self.pluginStatus[namesplit[-1]] = False
        print('User plugins:')
        #print(loggerlib.list_submodules(devices))
        subfolders = [f.name for f in os.scandir(list(devices.__path__)[0]) if f.is_dir()]
        for folder in subfolders:
            if folder not in ['', '__pycache__', '.git']:
                a =__import__(devices.__name__+"."+ folder)
                #for finder, name, ispkg in loggerlib.iter_namespace(devices):
                #fullpath = pkgutil.extend_path(list(devices.__path__)[0], folder)
                #print(fullpath)
                #for finder, name, ispkg in pkgutil.iter_modules(fullpath,devices.__name__+'.'+folder+ "."):
                #for root, dirs, files in os.walklevel(list(devices.__path__)[0], level=1):
                for files in os.listdir(list(devices.__path__)[0]+"/"+folder):
                    if files.endswith('.py'):
                        name = devices.__name__+'.'+folder+"."+files.replace('.py','')
                        namesplit = name.split('.')
                        print(name)
                        if namesplit[-1] not in ["LoggerPlugin"]:
                            self.devicenames[namesplit[-1]] = name
                            self.pluginStatus[namesplit[-1]] = False

    def toggleTelegramBot(self, value=None):
        if value is None:
            value = self.config['telegram_bot']
        self.config['telegram_bot'] = value
        if value:
            ok = self.telegramBot.connect()
            if not ok:
                self.config['telegram_bot'] = False
                self.telegramBot.stop()
        else:
            self.telegramBot.stop()

    def toggleHTMLPage(self, value=None):
        if value is None:
            value = self.config['rtoc_web']
        self.config['rtoc_web'] = value
        if value:
            self.rtoc_web = subprocess.Popen(["bokeh", "serve", self.getDir(__file__)+"/RTOC_Web.py"], shell=False)
            print('HTML-Server running at localhost:5006')
        else:
            if self.rtoc_web:
                #subprocess.call(["kill", "-9", "%d" % self.rtoc_web.pid])
                print('HTML-Server killed')
                self.rtoc_web.kill()
                self.rtoc_web = None

    def toggleTcpServer(self, value=None):
        if value is None:
            value = self.config['tcpserver']
        self.config['tcpserver'] = value
        if value:
            try:
                password = None
                if self.config['tcppassword'] != "":
                    password = self.config['tcppassword']
                self.tcp = jsonsocket.Server("0.0.0.0", self.config["tcpPort"], password)
                self.tcpRunning = True
                self.__tcpserver = Thread(target=self.tcpListener)
                self.__tcpserver.start()
                print("TCPServer gestartet")
            except OSError:
                print("Port already in use. Cannot start TCP-Server")
                self.tcpRunning = False
                self.config['tcpserver'] = False
        else:
            self.tcpRunning = False
            print("TCPServer beendet")
            if self.tcp:
                self.tcp.close()

    def setTCPPassword(self, strung):
        self.config['tcppassword'] = strung
        if self.tcp:
            if strung == '' or strung == None:
                self.tcp.setKeyword(None)
            elif type(strung) == str:
                self.tcp.setKeyword(strung)

    def setTCPPort(self, port):
        self.config['tcpPort'] = port


    def sendTCP(self, hostname="localhost", *args, **kwargs):
        self.tcpclient.createTCPClient(hostname)
        self.tcpclient.sendTCP(*args, **kwargs)

    def getThread(self):
        return self.__tcpserver

    def tcpListener(self):
        while self.tcpRunning:
            ans = {'error': False}
            try:
                self.tcp.accept()
                msg = self.tcp.recv()
                if type(msg) == dict and msg != {}:
                    # if self.config['tcppassword'] == "":
                    #     authorized = True
                    # elif 'password' in msg.keys():
                    #     hash_object = hashlib.sha256(self.config['tcppassword'].encode('utf-8'))
                    #     hex_dig = hash_object.hexdigest()
                    #     if msg['password'] == hex_dig:
                    #         authorized = True
                    #     else:
                    #         authorized = False
                    # else:
                    #     authorized = False
                    # if 'password' in msg.keys():
                    #     msg.pop('password')
                    # if authorized:
                        if 'y' in msg.keys():
                            plot = msg.get('plot', False)
                            datasY = msg.get('y', [])
                            datanames = msg.get('sname', [""])
                            devicename = msg.get('dname', "noDevice")
                            unit = msg.get('unit', [""])
                            datasX = msg.get('x', None)
                            if devicename is None:
                                devicename = "noDevice"
                            if plot:
                                self.plot(datasX, datasY, datanames, devicename, unit)
                            else:
                                self.addDataCallback(datasY, datanames, devicename, unit, datasX, True)
                            ans['sent'] = True
                        if 'getSignalList' in msg.keys():
                            signalNames = self.signalNames
                            if ['RTOC', ''] in signalNames:
                                signalNames.pop(signalNames.index(['RTOC', '']))
                            ans['signalList'] = signalNames
                        if 'getPluginList' in msg.keys():
                            ans['pluginList'] = self.getPluginDict()
                        if 'event' in msg.keys():
                            self.addNewEvent(*msg['event'])
                        if 'getEventList' in msg.keys():
                            ans['events'] = {}
                            for name in self.signalNames:
                                sig = self.getEvents(self.getSignalId(name[0], name[1]))
                                ans['events'][".".join(name)] = [list(sig[0]), list(sig[1])]
                        if 'getEvent' in msg.keys():
                            ans['events'] = {}
                            for device in msg['getEvent']:
                                dev = device.split('.')
                                sig = self.getEvents(self.getSignalId(dev[0], dev[1]))
                                ans['events'][device] = [list(sig[0]), list(sig[1])]
                        if 'getSignal' in msg.keys():
                            ans['signals'] = {}
                            if type(msg['getSignal']) == list:
                                for device in msg['getSignal']:
                                    dev = device.split('.')
                                    sig = self.getSignal(self.getSignalId(dev[0], dev[1]))
                                    unit = self.getSignalUnits(self.getSignalId(dev[0], dev[1]))
                                    ans['signals'][device] = [list(sig[0]), list(sig[1]), unit]
                            elif msg['getSignal'] == 'all':
                                for dev in self.signalNames:
                                    sig = self.getSignal(self.getSignalId(dev[0], dev[1]))
                                    unit = self.getSignalUnits(self.getSignalId(dev[0], dev[1]))
                                    ans['signals']['.'.join(dev)] = [list(sig[0]), list(sig[1]), unit]
                        if 'getLatest' in msg.keys():
                            ans['latest'] = {}
                            for device in msg['getLatest']:
                                dev = device.split('.')
                                sig = self.getSignal(self.getSignalId(dev[0], dev[1]))
                                ans['latest'][device] = sig[1][-1]
                        if 'remove' in msg.keys():
                            ans['remove'] = 'Not implemented'
                        if 'plugin' in msg.keys():
                            ans['plugin'] = self.handleTcpPlugins(msg['plugin'])
                        if 'logger' in msg.keys():
                            ans['logger'] = self.handleTcpLogger(msg['logger'])
                        for key in msg.keys():
                            if key not in ans.keys():
                                ans[key] = msg[key]
                else:
                    ans['error'] = True
                    if True:
                        ans['password'] = 'RTOC-Server is password protected!'
                    else:
                        ans['password'] = 'Wrong password'
                self.tcp.send(ans)
            except OSError:
                #print("TCP Server idle")
                pass
            except KeyboardInterrupt:
                self.stop()
            except:
                tb = traceback.format_exc()
                print(tb)
                print("Error in TCP-Connection")
                ans['error'] = True
                # self.tcp.send(ans)

    def handleTcpPlugins(self, pluginDicts):
        if type(pluginDicts) == dict:
            for plugin in pluginDicts.keys():
                if type(pluginDicts[plugin]) == dict:
                    for call in pluginDicts[plugin].keys():
                        if call == "start" and type(pluginDicts[plugin][call]) == bool:
                            if pluginDicts[plugin][call]:
                                pluginDicts[plugin][call] = self.startPlugin(plugin, callback=None)
                            else:
                                pluginDicts[plugin][call] = self.stopPlugin(plugin)
                        elif '()' in call:
                            pluginDicts[plugin][call] = self.callPluginFunction(
                                plugin, call.replace('()', ''), *pluginDicts[plugin][call])
                        else:
                            pluginDicts[plugin][call] = self.getPluginParameter(
                                plugin, call, pluginDicts[plugin][call])
        return pluginDicts

    def handleTcpLogger(self, loggerDict):
        if type(loggerDict) == dict:
            for call in loggerDict.keys():
                if call == 'clear':
                    if loggerDict[call] == 'all':
                        self.clear()
                    elif type(loggerDict[call]) == list:
                        for idx, sig in enumerate(loggerDict[call]):
                            id = self.getSignalId(*sig.split('.'))
                            if id != -1:
                                loggerDict[call][idx] = self.removeSignal(id)
                            else:
                                loggerDict[call][idx] = False
                if call == 'resize':
                    if type(loggerDict[call]) == int:
                        self.resizeSignals(loggerDict[call])
                        loggerDict[call] = True
                if call == 'export':
                    if type(loggerDict[call]) == list:
                        if len(loggerDict[call]) <= 2:
                            self.exportData(*loggerDict[call])
                            loggerDict[call] = True
                if call == 'info':
                    loggerDict[call] = {}
                    loggerDict[call]['recordLength'] = self.maxLength
                    loggerDict[call]['signals'] = len(self.signals)
                    loggerDict[call]['recordLength'] = self.maxLength
                    loggerDict[call]['starttime'] = self.starttime
                    loggerDict[call]['telegram_token'] = self.config['telegram_token']
                    loggerDict[call]['telegram_bot'] = self.config['telegram_bot']
                    size, maxsize = self.getSignalSize()
                    loggerDict[call]['signal_memory'] = size
                    loggerDict[call]['signal_memory_limit'] = maxsize
        return loggerDict

    def getPluginDict(self):
        dict = {}
        for name in self.devicenames.keys():
            dict[name] = {}
            dict[name]['functions'] = []
            dict[name]['parameters'] = []
            dict[name]['status'] = False
            for fun in self.pluginFunctions.keys():
                if fun.startswith(name+".") and fun not in [name+".close", name+".loadGUI", name+".createTCPClient", name+".sendTCP", name+".plot", name+".setDeviceName", name+".event", name+".stream"]:
                    dict[name]['functions'].append(fun.replace(name+".", ''))
            for fun in self.pluginParameters.keys():
                if fun.startswith(name+".") and fun not in [name+".deviceName", name+".close", name+".run", name+".smallGUI", name+".sock", name+".widget"]:
                    dict[name]['parameters'].append(fun.replace(name+".", ''))
            for fun in self.pluginStatus.keys():
                if name == fun:
                    dict[name]['status'] = self.pluginStatus[fun]
        return dict
    # Plugin functions ############################################################

    def startPlugin(self, name, callback=None, remote=True):
        # Starts the specified plugin and connects callback if possible
        try:
            if name in self.devicenames.keys():
                fullname = self.devicenames[name]
                # if callback is None:
                print(fullname)
                self.pluginObjects[
                name] = importlib.import_module(
                    fullname).Plugin(self.addDataCallback, self.plot, self.addNewEvent)
                # else:
                #     self.pluginObjects[name] = importlib.import_module(
                #         fullname).Plugin(callback, self.addNewEvent)
                self.analysePlugin(self.pluginObjects[name], name)
                self.pluginStatus[name] = True
                print("PLUGIN: " + name+' connected\n')
                #self.addNewEvent(text=translate('RTLogger', "Plugin gestartet: ") +
                #                 name, sname="", dname="RTOC", priority=0)
                if self.startDeviceCallback and remote:
                    self.startDeviceCallback(name)
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

    def getPlugin(self, name):
        try:
            if name in self.pluginObjects.keys():
                return self.pluginObjects[name]
            else:
                print("Plugin "+name+" not found or started")
                return False
        except:
            tb = traceback.format_exc()
            print(tb)
            print("PLUGIN FAILURE\nCould not get Plugin '"+str(name)+"'\n")
            return False

    def getPluginParameter(self, plugin, parameter, *args):
        try:
            #print(args)
            if parameter == "get" and type(parameter) == str:
                if type(args[0]) == list:
                    rets = []
                    for param in args[0]:
                        exec('self.ret=self.pluginObjects[plugin].'+str(param))
                        rets.append(self.ret)
                    self.ret = rets
                    return self.ret
            elif plugin in self.pluginObjects.keys():
                exec('self.pluginObjects[plugin].'+parameter+" = " + str(args[0]))
                self.ret = args[0]
                return self.ret
            else:
                print("Plugin "+plugin+" not found or started")
                return False
        except:
            tb = traceback.format_exc()
            print(tb)
            print("PLUGIN FAILURE\nCould not get/set/call Plugin parameter/function'"+str(plugin)+"'\n")
            return False

    def callPluginFunction(self, plugin, function, *args, **kwargs):
        try:
            if plugin in self.pluginObjects.keys() and type(function) == str:
                exec('self.func = self.pluginObjects[plugin].'+function)
                return self.func(*args, **kwargs)
            else:
                print("Plugin "+plugin+" not found or started")
                return False
        except:
            tb = traceback.format_exc()
            print(tb)
            print("PLUGIN FAILURE\nCould not get/set/call Plugin parameter/function'"+str(plugin)+"'\n")
            return False

    def stopPlugin(self, name, remote=True):
        # Stops the specified plugin
        try:
            if name in self.pluginObjects.keys():
                #self.pluginObjects[name].run = False
                self.pluginStatus[name] = False
                self.pluginObjects[name].close()
                print("PLUGIN: " + name+' disconnected\n')
                #self.addNewEvent(text=translate('RTLogger', "Plugin gestoppt: ") +
                #                 name, sname="", dname="RTOC", priority=0)
            # else:
            #    print("Plugin "+name+" not loaded")
            if self.stopDeviceCallback and remote:
                self.stopDeviceCallback(name)
            return True
        except:
            tb = traceback.format_exc()
            print(tb)
            print("PLUGIN FAILURE\nCould not stop Plugin '"+str(name)+"'\n")
            return False

    def stop(self):
        # Stops all plugins
        self.run = False
        self.tcpRunning = False
        if self.tcp:
            self.tcp.close()
        print("TCPServer beendet")
        if self.config['telegram_bot']:
            if self.config['telegram_eventlevel'] <= 1:
                self.telegramBot.sendMessage(self.config['telegram_name'] + " wird beendet.")
        self.telegramBot.stop()
        if self.backupThread:
            self.backupThread.cancel()
        self.toggleHTMLPage(False)
        for name in self.devicenames.keys():
            self.stopPlugin(name)

    def analysePlugin(self, object, name):
        # Adds public Plugin-functions and parameters to local attributes pluginFunctions and pluginParameters
        all = dir(object)
        for element in all:
            if str(element)[0] != "_":
                if callable(getattr(object, element)):
                    self.pluginFunctions[name+"."+element] = "self.pluginObjects[" + \
                        name+"']."+getattr(object, element).__name__
                else:
                    self.pluginParameters[name+"." +
                                          element] = "self.pluginObjects["+name+"']."+str(element)

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
        if newLength is None:
            newLength = self.maxLength
        else:
            self.maxLength = newLength
            self.config["defaultRecordLength"] = self.maxLength
        self.signals = [[deque([], newLength), deque([], newLength)]
                        for _ in range(len(self.signalNames))]
        #self.signalUnits = [deque([], newLength) for _ in range(len(self.signalNames))]
        self.signalUnits = ['' for _ in range(len(self.signalNames))]
        self.events = [[deque([], newLength), deque([], newLength), deque([], newLength)]
                       for _ in range(len(self.signalNames))]

    def resizeSignals(self, newLength=None):
        if newLength is None:
            newLength = self.maxLength
        else:
            self.maxLength = newLength
            self.config["defaultRecordLength"] = self.maxLength

        self.signals = [[deque(list(self.signals[idx][0]), newLength), deque(list(self.signals[idx][1]), newLength)]
                        for idx in range(len(self.signalNames))]
        #self.signalUnits = [deque(list(self.signalUnits[idx]), newLength)
        #                    for idx in range(len(self.signalNames))]

        self.events = [[deque(list(self.events[idx][0]), newLength), deque(list(self.events[idx][1]), newLength), deque(list(self.events[idx][2]), newLength)]
                       for idx in range(len(self.signalNames))]

    def removeSignal(self, id):
        idx = self.signalIDs.index(id)
        if idx != -1:
            self.signalNames.pop(idx)
            self.signalIDs.pop(idx)
            self.signals.pop(idx)
            self.signalUnits.pop(idx)

        return idx

    def getNewID(self):
        newID = 0
        while newID in self.signalIDs or newID == 0:
            newID += 1
        return newID

    def __addNewSignal(self, dataY, dataunit, devicename, dataname, dataX=None, createCallback=True):
        # Add a new signal-stream
        if dataY != None:
            print("LOGGER: Adding signal: "+devicename+", "+dataname)
            newLength = self.maxLength
            self.signalNames += [[devicename, dataname]]
            newID = self.getNewID()
            self.signalIDs.append(newID)
            self.signals += [[deque([], newLength), deque([], newLength)]]
            self.events += [[deque([], newLength), deque([], newLength), deque([], self.maxLength)]]
            #self.signalUnits += [deque([], newLength)]
            self.signalUnits += ['']
            if self.newSignalCallback:
                #self.newSignal = [len(self.signalNames)-1, devicename, dataname, dataunit]
                self.newSignalCallback(newID, devicename, dataname, dataunit)
            #self.addNewEvent(text=translate('RTLogger', "Signal-Stream hinzugefügt: ") +
            #                 dataname+"."+devicename, sname="", dname="RTOC", priority=0)
            self.__addNewData(float(dataY), dataunit, devicename, dataname, dataX, createCallback)

    def __addNewData(self, dataY, dataunit, devicename, dataname, dataX=None, createCallback=True):
        if dataY != None:
            # Add new data to a signal-stream
            # self.latestSignal.append([devicename,dataname])
            self.latestSignal = [devicename, dataname]
            idx = self.signalNames.index([devicename, dataname])
            if dataX is None:
                self.signals[idx][0].append(time.time())
            else:
                self.signals[idx][0].append(dataX)
            self.signals[idx][1].append(float(dataY))
            #self.signalUnits[idx].append(dataunit)
            self.signalUnits[idx] = dataunit
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

        if priority not in [0, 1, 2]:
            priority = 0

        callback = False
        if [devicename, dataname] not in self.signalNames:
            self.signalNames += [[devicename, dataname]]
            self.signals += [[deque([], self.maxLength), deque([], self.maxLength)]]
            newID = self.getNewID()
            self.signalIDs.append(newID)
            self.events += [[deque([], self.maxLength),
                             deque([], self.maxLength), deque([], self.maxLength)]]
            #self.signalUnits += [deque([], self.maxLength)]
            self.signalUnits += ['']
            self.signals[self.signalNames.index([devicename, dataname])][0].append(time.time())
            self.signals[self.signalNames.index([devicename, dataname])][1].append(0)
            #self.signalUnits[self.signalNames.index([devicename, dataname])].append("")
            callback = True
        idx = self.signalNames.index([devicename, dataname])
        if x is None:
            self.events[idx][0].append(time.time())
            x = time.time()
        else:
            self.events[idx][0].append(float(x))
        self.events[idx][1].append(strung)
        self.events[idx][2].append(priority)
        if self.newEventCallback:
            self.newEventCallback(x, strung, devicename, dataname, priority)
        if self.newSignalCallback and callback and (devicename != "RTOC"):
            self.newSignalCallback(newID, devicename, dataname, "")
        # if self.callbackEvent:
        #    self.callbackEvent()
        if self.config['telegram_bot']:
            if priority >= self.config['telegram_eventlevel']:
                ptext = ['_Information_\n', '*Warnung*\n', '*_Fehler_*\n'][priority]
                self.telegramBot.sendMessage(
                    ptext+'Gerät: ' + devicename+'\nSignal: '+dataname+'\n'+strung)

    def tr(self, args):
        print('not translated')
        return args

    def __plotNewSignal(self, x, y, dataunit, devicename, dataname, createCallback=False, autoResize = False):
        # Add a new signal-stream
        print("LOGGER: Adding signalplot: "+devicename+", "+dataname)
        newLength = self.maxLength
        self.signalNames += [[devicename, dataname]]
        self.events += [[deque([], self.maxLength), deque([], self.maxLength),
                         deque([], self.maxLength)]]
        self.signalIDs.append(self.getNewID())
        self.signals += [[deque([], newLength), deque([], newLength)]]
        #self.signalUnits += [deque([], newLength)]
        self.signalUnits += ['']
        if autoResize and len(y)>=self.maxLength:
            self.resizeSignals(len(y))
            print('Your recording length was updated due to plotting a bigger signal')
            if self.recordingLengthChangedCallback:
                self.recordingLengthChangedCallback(devicename, dataname, len(y))
        self.__plotNewData(x, y, dataunit, devicename, dataname, createCallback, 'off', autoResize)
        if self.newSignalCallback:
            self.newSignalCallback(self.signalIDs[-1], devicename, dataname, dataunit)
        #self.addNewEvent(text=translate('RTLogger', "Signal-Plot hinzugefügt: ") +
        #                 dataname+"."+devicename, sname="", dname="RTOC", priority=0)

    def __plotNewData(self, x, y, dataunit, devicename, dataname, createCallback=False, hold='off', autoResize=False):
        # Add new data to a signal-stream
        self.latestSignal = [devicename, dataname]
        # get signal idx
        idx = self.signalNames.index([devicename, dataname])

        if autoResize:
            newsize = None
            # check size and make signals longer, if needed.
            if hold == 'on':
                if len(y)+len(self.signals[idx][1])>=self.maxLength:
                    newsize = len(y)+len(self.signals[idx][1])
            else:
                if len(y)>=self.maxLength:
                    newsize = len(y)

            if newsize:
                self.resizeSignals(newsize)
                print('Your recording length was updated due to plotting a bigger signal')
                if self.recordingLengthChangedCallback:
                    self.recordingLengthChangedCallback(devicename, dataname, newsize)

        # handle different holds: 'on', 'off', ''
        if hold == 'on':
            self.signals[idx][0] += x
            self.signals[idx][1] += y
        elif hold == 'mergeX':
            for val_idx, value in enumerate(x):
                if value not in self.signals[idx][0]:
                    if autoResize:
                        if len(self.signals[idx][0])>=self.maxLength:
                            self.resizeSignals(len(self.signals[idx][0])+50)
                    self.signals[idx][0].append(x[val_idx])
                    self.signals[idx][1].append(y[val_idx])
        elif hold == 'mergeY':
            for val_idx, value in enumerate(y):
                if value not in self.signals[idx][1]:
                    if autoResize:
                        if len(self.signals[idx][0])>=self.maxLength:
                            self.resizeSignals(len(self.signals[idx][0])+50)
                    self.signals[idx][0].append(x[val_idx])
                    self.signals[idx][1].append(y[val_idx])
        else:
            self.signals[idx][0].clear()
            self.signals[idx][1].clear()
            self.signals[idx][0] = deque(x, self.maxLength)
            self.signals[idx][1] = deque(y, self.maxLength)

        # data unit handling
        if type(dataunit) == str:
            # self.signalUnits[idx] = deque([dataunit]*len(x), self.maxLength)
            self.signalUnits[idx] = dataunit
        elif type(dataunit) == list:
            self.signalUnits[idx] = dataunit[-1]
        else:
            print("no unit specified")
            self.signalUnits[idx] = ''

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
            print("\nUnit: ")
            #for data in self.signalUnits[idx]:
            #    sys.stdout.write(str(data)+'\t\t')
            sys.stdout.write(str(self.signalUnits[idx])+'\t\t')
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
        units = kwargs.get('unit', "")
        datasX = kwargs.get('x', [None])
        createCallback = kwargs.get("c", True)
        for idx, arg in enumerate(args):
            if idx == 0:
                datanames = arg
            if idx == 1:
                devicename = arg
            if idx == 2:
                units = arg
            if idx == 3:
                datasX = arg
            if idx == 4:
                createCallback = arg

        if type(datasY) == float or type(datasY) == int:
            datasY = [datasY]
            print('Warning: You should stream a list of signals, not a single signal')

        if type(datasY) == list:
            if datasX == [None]:
                datasX = [None]*len(datasY)
            if units == [""] or units is None or type(units)== str:
                units = [""]*len(datasY)
            if len(units) < len(datasY):
                units += ['']*(len(datasY)-len(units))
            elif len(units) > len(datasY):
                units = units[0:len(datasY)]
            for idx, data in enumerate(datasY):
                if [devicename, datanames[idx]] in self.signalNames:
                    self.__addNewData(datasY[idx],
                                      units[idx], devicename, datanames[idx], datasX[idx], createCallback)
                else:
                    self.__addNewSignal(datasY[idx],
                                        units[idx], devicename, datanames[idx], datasX[idx], createCallback)
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

        # try:
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
        elif type(data) == int or type(data) == float:
            if [devicename, dataname] in self.signalNames:
                self.__addNewData(data,
                                  dataunit, devicename, dataname, None, createCallback)
            else:
                self.__addNewSignal(data,
                                    dataunit, devicename, dataname, None, createCallback)

    def plot(self, x=[], y=[], *args, **kwargs):
        dataname = kwargs.get('sname', "noName")
        devicename = kwargs.get('dname', "noDevice")
        dataunit = kwargs.get('unit', "")
        hold = kwargs.get('hold', "off")
        autoResize = kwargs.get('autoResize', False)
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
        if len(x) == len(y):
            if [devicename, dataname] in self.signalNames:
                self.__plotNewData(x, y,
                                   dataunit, devicename, dataname, createCallback, hold, autoResize)
            else:
                self.__plotNewSignal(x, y,
                                     dataunit, devicename, dataname, createCallback, autoResize)
        else:
            print("Plotting aborted. len(x)!=len(y)")

# Other functions #########################################################

    def exportData(self, *args, **kwargs):
        filename = kwargs.get('filename', None)
        filetype = kwargs.get('filetype', "json")
        scripts = kwargs.get('scripts', None)
        overwrite = kwargs.get('overwrite', False)
        for idx, arg in enumerate(args):
            if idx == 0:
                filename = arg
            if idx == 1:
                filetype = arg

        if filename is None:
            filename = self.generateFilename()
        if filetype == "xlsx":
            self.exportXLSX(filename)
        elif filetype == "json":
            self.exportJSON(filename, scripts, overwrite)
        else:
            self.exportCSV(filename)

    def generateFilename(self):
        minx = []
        maxx = []
        for signal in self.signals:
            minx.append(min(list(signal[0])))
        minx = max(minx)
        now = time.strftime("%d_%m_%y_%H_%M", time.localtime(minx))
        return self.config['documentfolder']+"/"+str(now)

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
            worksheet2.write(row, col, str(self.signalUnits[idx]))
            row += 1
            #for data in self.signalUnits[idx]:
            #    worksheet2.write(row, col, str(data))
            #    row += 1


        workbook.close()

    def exportJSON(self, filename, scripts=None, overwrite=False):
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
            # if len(self.signalUnits[idx]) == 0:
            #     self.signalUnits[idx].append("")
            jsonfile["data"][".".join(name)].append(y.tolist())
            #jsonfile["data"][".".join(name)].append(self.signalUnits[idx][0])
            jsonfile["data"][".".join(name)].append(self.signalUnits[idx])
            jsonfile["events"][".".join(name)].append(list(self.events[idx][0]))
            jsonfile["events"][".".join(name)].append(list(self.events[idx][1]))

        if scripts!=None:
            jsonfile["scripts"]=scripts

        if overwrite or not os.path.exists(filename):
            with open(filename, 'w') as fp:
                json.dump(jsonfile, fp, sort_keys=False, indent=4, separators=(',', ': '))

            return True
        else:
            try:
                with open(filename) as f:
                    data = json.load(f)

                for signal in jsonfile["data"].keys():
                    name = signal.split(".")
                    if len(jsonfile["data"][signal][0]) != 0:
                        if signal in data['data'].keys():
                            for idx, xvalue in enumerate(jsonfile["data"][signal][0]):
                                if xvalue not in data['data'][signal][0]:
                                    data['data'][signal][0].append(jsonfile['data'][signal][0][idx])
                                    data['data'][signal][1].append(jsonfile['data'][signal][1][idx])
                        else:
                            data['data'][signal] = jsonfile['data'][signal]
                for signal in jsonfile["events"].keys():
                    if signal != ".":
                        name = signal.split(".")
                        if signal in data['data'].keys():
                            if len(name) == 1:
                                name.append("")
                            for idx, event in enumerate(jsonfile["events"][signal][0]):
                                if xvalue not in data['events'][signal][0]:
                                    data['events'][signal][0].append(jsonfile['events'][signal][0][idx])
                                    data['events'][signal][1].append(jsonfile['events'][signal][1][idx])
                        else:
                            data['events'] = jsonfile['events']
                if 'scripts' in jsonfile.keys():
                    if 'scripts' not in data.keys():
                        data['scripts'] = None
                    data['scripts'] += jsonfile['scripts']
                with open(filename, 'w') as fp:
                    json.dump(data, fp, sort_keys=False, indent=4, separators=(',', ': '))

                return True
            except:
                return False

    def restoreJSON(self, filename=None, clear=True):
        # try:
        if filename == None:
            filename = self.config['documentfolder']+"/restore.json"
        if os.path.exists(filename):
            try:
                with open(filename) as f:
                    data = json.load(f)
                if clear:
                    self.clear()
                    self.maxLength = data["maxLength"]
                for signal in data["data"].keys():
                    name = signal.split(".")
                    if len(data["data"][signal][0]) != 0:
                        if clear == True:
                            holde = "off"
                        else:
                            holde = "mergeX"
                        self.plot(data["data"][signal][0], data["data"][signal][1],
                                  name[1], name[0], data["data"][signal][2], False, hold=holde, autoResize=True)
                for signal in data["events"].keys():
                    if signal != ".":
                        name = signal.split(".")
                        if len(name) == 1:
                            name.append("")
                        for idx, event in enumerate(data["events"][signal][0]):
                            self.addNewEvent(data["events"][signal][0][idx], name[1],
                                             name[0], event, data["events"][signal][1])
                if 'scripts' in data.keys():
                    return data['scripts']
                return True
            except:
                return False
        else:
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
        with open(filename+".csv", 'w', newline='') as myfile:
            wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
            wr.writerow(list(signal[0]))
            wr.writerow(list(signal[1]))

    def load_config(self):
        self.lastEditedList = []

        userpath = os.path.expanduser('~/.RTOC')
        if not os.path.exists(userpath):
            os.mkdir(userpath)

        if os.path.exists(userpath+"/config.json"):
            try:
                with open(userpath+"/config.json", encoding="UTF-8") as jsonfile:
                    self.config = json.load(jsonfile, encoding="UTF-8")
                newlist = []
                #self.config['documentfolder'] = userpath
                for path in self.config["lastSessions"]:
                    if os.path.exists(path):
                        newlist.append(path)
                self.config["lastSessions"] = newlist
                for lastpath in self.config["lastSessions"]:
                    self.lastEditedList.append(lastpath)
                for key in defaultconfig.keys():
                    if key not in self.config.keys():
                        self.config[key] = defaultconfig[key]
            except:
                print('Error loading config.json')
                self.config = defaultconfig
        else:
            print('No config-file found.')
            self.config = defaultconfig

        self.config['documentfolder'] = userpath
        # conf = dict(self.config)
        # conf['telegram_bot'] = False
        # conf['rtoc_web'] = False
        # with open(self.config['documentfolder']+"/config.json", 'w', encoding="utf-8") as fp:
        #     json.dump(conf, fp,  sort_keys=False, indent=4, separators=(',', ': '))

    def clearCache(self):
        self.config = defaultconfig
        self.save_config()
        filename = self.config['documentfolder']+"/plotStyles.json"
        if os.path.exists(filename):
            os.remove(filename)

    def save_config(self):
        self.config["deviceWidget"] = True
        self.config["pluginsWidget"] = False
        with open(self.config['documentfolder']+"/config.json", 'w', encoding="utf-8") as fp:
            json.dump(self.config, fp,  sort_keys=False, indent=4, separators=(',', ': '))

    def load_autorun_plugins(self):
        userpath = os.path.expanduser('~/.RTOC/autorun_devices')
        if not os.path.exists(userpath):
            with open(userpath, 'w', encoding="UTF-8") as f:
                f.write('')
        else:
            plugins = []
            try:
                with open(userpath, 'r', encoding="UTF-8") as f:
                    content = f.readlines()
                # you may also want to remove whitespace characters like `\n` at the end of each line
                plugins = [x.strip() for x in content]
            except:
                print('error in '+userpath)
            for p in plugins:
                self.startPlugin(p)

    def getSignal(self, id):
        if id in self.signalIDs:
            idx = self.signalIDs.index(id)
            return self.signals[idx]
        else:
            return [[], []]

    def getEvents(self, id):
        if id in self.signalIDs:
            idx = self.signalIDs.index(id)
            return self.events[idx]
        else:
            return [[], [], []]

    def getSignalUnits(self, id):
        if id in self.signalIDs:
            idx = self.signalIDs.index(id)
            return str(self.signalUnits[idx])
        else:
            return ''

    def getSignalNames(self, id):
        if id in self.signalIDs:
            idx = self.signalIDs.index(id)
            return self.signalNames[idx]
        else:
            return [[''], ['']]

    def getSignalSize(self):
        maxsize = len(self.signals)*(2*(self.maxLength*8+64)+16)
        outerlayer = sys.getsizeof(self.signals)
        innerlayer = 0
        for sig in self.signals:
            innerlayer += sys.getsizeof(sig)
            innerlayer += sys.getsizeof(sig[0])*2
            innerlayer += sys.getsizeof(list(sig[0]))*2
        size = outerlayer + innerlayer
        return size, maxsize

    def check_for_updates(self):
        import xmlrpc.client
        try:
            from pip._internal.utils.misc import get_installed_distributions
        except ImportError:  # pip<10
            from pip import get_installed_distributions

        pypi = xmlrpc.client.ServerProxy('http://pypi.python.org/pypi')
        available = pypi.package_releases('RTOC')

        current = None
        for pack in get_installed_distributions():
            if pack.project_name == 'RTOC':
                current = pack.version
                break
        if current != None:
            print('\nInstalled version: '+str(current))
        else:
            print('RTOC was not installed with PyPi. To enable version-checking, please install it with "pip3 install RTOC"')
        if not available:
            print("Sorry. Couldn't get version information from PyPi. Please visit 'https://pypi.org/project/RTOC/'")
        else:
            print('Newest version: '+str(available[0]))

        if current != None and available:
            if current == available[0]:
                print('RTOC is up to date.')
            else:
                print('New version available! Please update\n\npip3 install RTOC --upgrade\n')
        return current, available

    def setBackupIntervall(self, intervall):
        if self.backupThread:
            self.backupThread.cancel()
        if intervall>=0:
            self.config['backupIntervall']=intervall
            if intervall>0:
                self.backupThread = Timer(intervall, self.exportJSON,  args=[self.config['backupFile']])
            return True
        else:
            return False


if __name__ == "__main__":
    kl = RTLogger()
    time.sleep(1)
    kl.stop()
