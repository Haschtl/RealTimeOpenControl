#!/usr/local/bin/python3
# coding: utf-8
import os
import traceback
from threading import Thread
# import sys
# import subprocess

from .. import jsonsocket

import logging as log
log.basicConfig(level=log.DEBUG)
logging = log.getLogger(__name__)

# try:
#     from .RTOC_Web import RTOC_Web
# except ImportError:
#     logging.warning(
#         'Dash (Plotly) for python not installed. Please install with "pip3 install dash"')
#     RTOC_Web = None
try:
    from .telegramBot import telegramBot
except ImportError:
    logging.warning(
        'Telegram for python not installed. Please install with "pip3 install python-telegram-bot"')
    telegramBot = None


class NetworkFunctions:
    """
    This class contains all tcp-specific functions of RTLogger
    """
    def toggleTelegramBot(self, value=None):
        """
        Toggles telegram bot on/off and sets value ['telegram']['active'] in config.

        Args:
            value (bool): True to enable telegram bot, False to disable telegram bot.

        Returns:
            bool: True, if toggling was successfully
        """
        if telegramBot is not None:
            if value is None:
                value = not bool(self.config['telegram']['active'])
            self.config['telegram']['active'] = value
            if value:
                self.telegramBot = telegramBot(self)
                ok = self.telegramBot.connect()
                if not ok:
                    self.config['telegram']['active'] = False
                    self.telegramBot.stop()
                    return False
                return True
            else:
                if self.telegramBot:
                    self.telegramBot.stop()
                return True
        else:
            logging.error(
                'Telegram for python not installed. Please install with "pip3 install python-telegram-bot"')
            return False

    def toggleTcpServer(self, value=None):
        """
        Toggles tcp-server on/off and sets value ['tcp']['active'] in config.

        Args:
            value (bool): True to enable tcp server, False to disable tcp server.

        Returns:
            bool: True, if toggling was successfully
        """
        if value is None:
            value = self.config['tcp']['active']
        self.config['tcp']['active'] = value
        if value:
            try:
                password = None
                if self.config['tcp']['password'] != "":
                    password = self.config['tcp']['password']
                self.tcp = jsonsocket.Server("0.0.0.0", self.config['tcp']['port'], password)
                self.tcpRunning = True
                self.__tcpserver = Thread(target=self._tcpListener)
                self.__tcpserver.start()
                logging.info("TCPServer gestartet")
                return True
            except OSError:
                logging.error("Port already in use. Cannot start TCP-Server")
                self.tcpRunning = False
                # self.config['tcp']['active'] = False
                return False
        else:
            self.tcpRunning = False
            logging.info("TCPServer beendet")
            if self.tcp:
                self.tcp.close()
            return True

    def setTCPPassword(self, strung):
        """
        Sets the tcp password for tcp-server

        Args:
            strung (str): Your password-string.
        """
        self.config['tcp']['password'] = strung
        if self.tcp:
            if strung == '' or strung is None:
                self.tcp.setKeyword(None)
            elif type(strung) == str:
                self.tcp.setKeyword(strung)

    def setTCPPort(self, port):
        """
        Sets the tcp port for tcp-server in config

        Args:
            port (int): Your desired tcp-port.
        """
        self.config['tcp']['port'] = port

    def sendTCP(self, hostname="localhost", *args, **kwargs):
        """
        See :func:`RTOC.LoggerPlugin.LoggerPlugin._sendTCP` for more information
        """
        self.tcpclient.createTCPClient(hostname)
        return self.tcpclient._sendTCP(*args, **kwargs)

    def getThread(self):
        """
        Returns the :mod:`threading.Thread` object of :meth:`._tcpListener`
        """
        return self.__tcpserver

    def _tcpListener(self):
        while self.tcpRunning:
            ans = {'error': False}
            try:
                self.tcp.accept()
                msg = self.tcp.recv()
                if type(msg) == dict and msg != {}:
                    if 'y' in msg.keys():
                        plot = msg.get('plot', False)
                        y = msg.get('y', [])
                        sname = msg.get('sname', [""])
                        dname = msg.get('dname', "noDevice")
                        unit = msg.get('unit', [""])
                        x = msg.get('x', None)
                        if dname is None:
                            dname = "noDevice"
                        if plot:
                            self.database.plot(x, y, sname, dname, unit)
                        else:
                            self.database.addDataCallback(y, sname, dname, unit, x, True)
                        ans['sent'] = True
                    if 'getSignalList' in msg.keys():
                        ans['signalList'] = self.getSignalList()
                    if 'getPluginList' in msg.keys():
                        ans['pluginList'] = self.getPluginDict()
                    if 'event' in msg.keys():
                        self.database.addNewEvent(*msg['event'])
                    if 'getEventList' in msg.keys():
                        ans['events'] = self.getEventList()
                    if 'getEvent' in msg.keys():
                        ans['events'] = self.getEvent(msg['getEvent'])
                    if 'getSignal' in msg.keys():
                        ans['signals'] = self.getSignal(msg['getSignal'])
                    if 'getLatest' in msg.keys():
                        ans['latest'] = self.getLatest(msg['getLatest'])
                    if 'getSession' in msg.keys():
                        ans['session'] = self.database.generateSessionJSON(scripts=None)
                    if 'remove' in msg.keys():
                        ans['remove'] = self.remove(msg['remove'])
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
                # print(ans)
                self.tcp.send(ans)
            except OSError:
                logging.debug("TCP Server idle")
                # self.tcp.send({'error':True})
                pass
            except KeyboardInterrupt:
                logging.info("TCP Server stopped by user input.")
                self.stop()
            except Exception:
                tb = traceback.format_exc()
                logging.debug(tb)
                print(tb)
                logging.warning("Error in TCP-Connection")
                ans['error'] = True
                # password = self.config['tcp']['password']
                # self.tcp.close()
                # self.tcp = jsonsocket.Server("0.0.0.0", self.config['tcp']['port'], password)
                self.tcp.send({'error':True})
            finally:
                if self.tcp.client:
                    self.tcp.client.close()
                    self.tcp.client = None
            #     self.tcp.close()

    def createTcpSignal(self, name):
        """
        Returns signal for :meth:`.getSignal`, which is used in tcp-requests

        Args:
            name (str): Device.Signalname of signal

        Returns:
            list: [x, y, unit]
        """
        dev = name.split('.')
        sig = self.database.getSignal_byName(dev[0], dev[1])
        unit = sig[4]
        ans = [list(sig[2]), list(sig[3]), unit]
        # if self.config['postgresql']['active'] and len(ans[0]) > self.config['global']['recordLength']:
        #     start = len(ans[0]) - self.logger.config['global']['recordLength']
        #     ans[0] = ans[0][start:-1]
        #     ans[1] = ans[1][start:-1]
        return ans

    def handleTcpPlugins(self, pluginDicts):
        """
        Calls plugin function, returns plugin parameter or sets plugin parameter, depending on pluginDicts. (used in tcp-requests)

        Args:
            pluginDicts (dict): {'pluginName':{'start':True/False}} to start/stop plugin

            pluginDicts (dict): {'pluginName':{'parameter':'get'}} to get a parameter

            pluginDicts (dict): {'pluginName':{'parameter': value}} to set a parameter

            pluginDicts (dict): {'pluginName':{'function': params}} to call a function

        Returns:
            dict
        """
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
        """
        Calls some RTOC-functions, depending on loggerDict. (used in tcp-requests)

        Args:
            loggerDict (dict): {'clear':'all'/['dname.sname',...]} to clear all data or to clear signals specified in list

            loggerDict (dict): {'resize': int} to resize the local recordingLength

            loggerDict (dict): {'export':['dname.sname',...]} to export a signal

            loggerDict (dict): {'info':None} to get informations about RTOC 

            loggerDict (dict): {'reboot':None} to reboot RTOC-server

        Returns:
            dict
        """
        if type(loggerDict) == dict:
            for call in loggerDict.keys():
                if call == 'clear':
                    if loggerDict[call] == 'all':
                        self.clear()
                    elif type(loggerDict[call]) == list:
                        for idx, sig in enumerate(loggerDict[call]):
                            id = self.database.getSignalID(*sig.split('.'))
                            if id != -1:
                                loggerDict[call][idx] = self.database.removeSignal(id)
                            else:
                                loggerDict[call][idx] = False
                elif call == 'resize':
                    if type(loggerDict[call]) == int:
                        self.database.resizeSignals(loggerDict[call])
                        loggerDict[call] = True
                elif call == 'export':
                    if type(loggerDict[call]) == list:
                        if len(loggerDict[call]) <= 2:
                            self.exportData(*loggerDict[call])
                            loggerDict[call] = True
                elif call == 'info':
                    loggerDict[call] = {}
                    loggerDict[call]['recordLength'] = self.config['global']['recordLength']
                    loggerDict[call]['signals'] = len(self.database.signals())
                    loggerDict[call]['recordLength'] = self.config['global']['recordLength']
                    loggerDict[call]['starttime'] = self.starttime
                    loggerDict[call]['telegram_token'] = self.config['telegram']['token']
                    loggerDict[call]['telegram_bot'] = self.config['telegram']['active']
                    size, maxsize, databaseSize = self.database.getSignalSize()
                    loggerDict[call]['signal_memory'] = size
                    loggerDict[call]['signal_memory_limit'] = maxsize
                elif call == 'reboot':
                    self.database.database.exportJSON(self.config['global']
                                    ['documentfolder']+"/restore.json", None, True)
                    self.save_config()
                    os.system('sudo reboot')
        return loggerDict

    def getSignalList(self):
        """
        Returns signallist, which is used in tcp-requests

        Returns:
            :func:`RTOC.RTLogger.RT_data.signalNames`
        """
        signalNames = self.database.signalNames()
        if ['RTOC', ''] in signalNames:
            signalNames.pop(signalNames.index(['RTOC', '']))
        return signalNames

    def getPluginDict(self):
        """
        Returns a dictonary containing all plugin information, which is used in tcp-requests

        Returns:
            dict: {'functions':[], 'parameters':[], 'status':bool}
        """
        dict = {}
        for name in self.devicenames.keys():
            dict[name] = {}
            dict[name]['functions'] = []
            dict[name]['parameters'] = []
            dict[name]['status'] = False
            for fun in self.pluginFunctions.keys():
                if fun.startswith(name+".") and fun not in [name+".close", name+".loadGUI", name+".createTCPClient", name+".sendTCP", name+".plot", name+".setDeviceName", name+".event", name+".stream", name+".cancel", name+".start", name+".setPerpetualTimer", name+".setSamplerate", name+".getDir"]:
                    dict[name]['functions'].append(fun.replace(name+".", ''))
            for fun in self.pluginParameters.keys():
                if fun.startswith(name+".") and fun not in [name+".run", name+".smallGUI", name+".widget", name+".samplerate"]:
                    value = self.getPluginParameter(name, "get", fun.replace(name+".", ''))
                    if type(value) not in [str, int, float, list, bool]:
                        value = "Unknown datatype"
                    dict[name]['parameters'].append([fun.replace(name+".", ''), value])
            for fun in self.pluginStatus.keys():
                if name == fun:
                    dict[name]['status'] = self.pluginStatus[fun]
        return dict

    def getEventList(self):
        """
        Returns eventlist, which is used in tcp-requests

        Returns:
            :func:`RTOC.RTLogger.RT_data.events`
        """
        return self.database.events()

    def getEvent(self, nameList):
        """
        Returns events for given signalnames, which is used in tcp-requests

        Args:
            nameList (list): List of device.signalnames

        Returns:
            list: [:func:`RTOC.RTLogger.RT_data.getEvents`,...]
        """
        ans = {}
        for device in nameList:
            dev = device.split('.')
            sig = self.database.getEvents(self.database.getSignalID(dev[0], dev[1]))
            # ans['events'][device] = [list(sig[0]), list(sig[1]), list(sig[2])]

            if sig != [[], [], [], [], []]:
                ans[device] = []
                if len(sig[0]) > 0:
                    for idx, s in enumerate(sig[0]):
                        ans[device].append(
                            [sig[0][idx], sig[1][idx], sig[2][idx], sig[3][idx], sig[4][idx]])
        return ans

    def getSignal(self, sigList):
        """
        Returns signal for given signalnames, which is used in tcp-requests

        Args:
            sigList (list): List of device.signalnames

            sigList (str): If sigList== 'all', all signals are returned

        Returns:
            dict: {'signalname': :meth:`.createTcpSignal`,...}
        """
        ans = {}
        if type(sigList) == list:
            for device in sigList:
                if type(device) == str:
                    ans[device] = self.createTcpSignal(device)
        elif sigList == 'all':
            for dev in self.database.signalNames():
                device = '.'.join(dev)
                ans[device] = self.createTcpSignal(device)
        return ans

    def getLatest(self, latList):
        """
        Returns latest xy-pairs for given signalnames, which is used in tcp-requests

        Args:
            latList (list): List of device.signalnames

            latList (bool): If latList== True, all latest xy-pairs are returned

        Returns:
            dict: {'signalname': [x[-1], y[-1]],...}
        """
        ans = {}
        if type(latList) == list:
            for device in latList:
                dev = device.split('.')
                sig = self.database.getSignal_byName(dev[0], dev[1])
                if len(sig[0]) > 0:
                    ans[device] = [sig[0][-1], sig[1][-1]]
        elif latList is True:
            latest = self.database.getLatest()
            ans = latest
        return ans

    def remove(self, remList):
        """
        Removes latest xy-pairs for given signalnames, which is used in tcp-requests

        Args:
            remList (list): List of device.signalnames


        **THIS IS NOT IMPLEMENTED YET**
        """
        return 'Not implemented'
