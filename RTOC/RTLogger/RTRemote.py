import time
from threading import Thread
import traceback
import json

from ..LoggerPlugin import LoggerPlugin

try:
    from PyQt5.QtCore import QCoreApplication
    translate = QCoreApplication.translate
except ImportError:
    def translate(id, text):
        return text

import socket
try:
    import nmap
except ImportError:
    print('nmap for python not installed! Install with "pip3 install python-nmap"')
    nmap = None


class SingleConnection(LoggerPlugin):
    def __init__(self, stream=None, plot=None, event=None, host='127.0.0.1', port=5050):
        # Plugin setup
        super(SingleConnection, self).__init__(stream, plot, event)
        self.setDeviceName(host)
        self.host = host
        self.port = port
        self.run = False  # False -> stops thread
        self.pause = False
        self.samplerate = 1
        self.maxLength = 0
        self.status = 'disconnected'
        self.siglist = []
        self.pluglist = []
        self.eventlist = {}
        #self.createTCPClient(host, None, port)
        self.tcppassword = None
        self.updateRemoteCallback = None
        self.start()


    # THIS IS YOUR THREAD
    def updateT(self):
        diff = 0
        while self.run:
            if self.samplerate > 0:
                if diff < 1/self.samplerate:
                    time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            if not self.pause:
                self.getAll()
            diff = time.time() - start_time

    def getAll(self):
        ans = self._sendTCP(getSignalList=True, getPluginList=True,
                            logger={'info': True}, getEventList=True)
        # print(ans)
        if ans:
            if self.updateRemoteCallback is not None and self.status != "connected":
                self.status = "connected"
                self.updateRemoteCallback()
            if 'signalList' in ans.keys():
                if ans['signalList'] != self.siglist:
                    self.siglist = ans['signalList']
                    if self.updateRemoteCallback is not None:
                        self.updateRemoteCallback()
                    # self.updateList()
            if 'pluginList' in ans.keys():
                if ans['pluginList'] != self.pluglist:
                    self.pluglist = ans['pluginList']
                    # self.widget.updateDevices.emit(self.pluglist)
            # if self.widget.streamButton.isChecked():
                # self.plotSignals()
            if 'logger' in ans.keys():
                maxLength = ans['logger']['info']['recordLength']
                if maxLength != self.maxLength:
                    self.maxLength = maxLength
                    if self.updateRemoteCallback is not None:
                        self.updateRemoteCallback()
                    # self.widget.maxLengthSpinBox.setValue(self.maxLength)
            if 'events' in ans.keys():
                if ans['events'] != self.eventlist:
                    # self.widget.updateDevices.emit(self.eventlist)
                    self.updateEvents(ans['events'])
            if self.siglist != []:
                selection = self.siglist
                selection = [".".join(i) for i in selection]
                ans = self._sendTCP(getSignal=selection)

                if ans != False:
                    if 'signals' in ans.keys():
                        for sig in ans['signals'].keys():
                            signame = sig.split('.')
                            s = ans['signals'][sig]
                            u = s[2]
                            self.plot(s[0], s[1], sname=signame[1],
                                      dname=self.host+":"+signame[0], unit=u)
        else:
            self.status = "error"
            if self.updateRemoteCallback is not None:
                self.updateRemoteCallback()

    def updateEvents(self, newEventList):
        for dev in newEventList.keys():
            if dev not in self.eventlist.keys():
                self.eventlist[dev] = [[], []]
            # print(newEventList)
            if newEventList[dev] != []:
                for idx, ev in enumerate(newEventList[dev]):
                    if ev not in self.eventlist[dev]:
                        device = dev.split('.')
                        self.event(x=ev[0], text=ev[1], sname=device[1],
                                   dname=self.host+":"+device[0], priority=ev[2])
        self.eventlist = newEventList

    def resizeLogger(self, newsize):
        ans = self._sendTCP(logger={'resize': newsize})
        if ans:
            self.maxLength = newsize
        return ans

    def toggleDevice(self, plugin, state):
        ans = self._sendTCP(plugin={plugin: {'start': state}})
        return ans

    def clear(self, signals=[]):
        if signals == []:
            signals = 'all'
        ans = self._sendTCP(logger={'clear': signals})
        # print(ans)

    def stop(self):
        self.run = False
        self.siglist = []
        self.pluglist = []
        self.eventlist = {}

    def start(self):
        if self.run:
            self.run = False
        else:
            self.createTCPClient(self.host, self.tcppassword, self.port)
            #self.run = True
            try:
                ok = self._sendTCP()
                # print(ok)
                if ok is None:
                    self.status = 'protected'
                elif ok != False:
                    ok = True
            except:
                tb = traceback.format_exc()
                print(tb)
                ok = False
            if ok:
                self.getAll()
                self.run = True
                self.__updater = Thread(target=self.updateT)
                self.__updater.start()
                self.status = 'connected'
            elif ok is False:
                self.__base_address = ""
                self.run = False
                self.status = "error"
            else:
                self.__base_address = ""
                self.run = False
                self.status = "wrongPassword"

    def getSession(self):
        ans = self._sendTCP(getSession=True)
        if ans:
            # print(ans)
            return ans['session']

    def callPluginFunction(self, device, function, parameter):
        ans = self._sendTCP(plugin={device: {function: parameter}})
        return ans


class RTRemote():
    def __init__(self, parent=None):
        # Data-logger thread

        # self.__updater = Thread(target=self.updateT)    # Actualize data
        # self.updater.start()
        self.logger = parent
        self.config = parent.config

        self.connections = []

        self.devices = {}
        self.devicenames = {}
        self.pluginStatus = {}

    def stop(self):
        for c in self.connections:
            c.stop()
        self.connections = []

    def setSamplerate(self, samplerate=1):
        self.logger.config["remoteRefreshRate"] = samplerate
        for c in self.connections:
            c.samplerate = samplerate

    def connect(self, hostname='127.0.0.1', port=5050):
        if len(hostname.split(':')) == 2:
            port = int(hostname.split(':')[1])
            hostname = hostname.split(':')[0]

        for c in self.connections:
            if c.host == hostname and c.port == port:
                if not c.run:
                    c.start()
                    self.getRemoteDeviceList()
                return

        newConnection = SingleConnection(
            self.logger.addDataCallback, self.logger.plot, self.logger.addNewEvent, hostname, port)
        # if newConnection.run:
        newConnection.samplerate = self.logger.config["remoteRefreshRate"]
        self.connections.append(newConnection)
        self.getRemoteDeviceList()

    def disconnect(self, hostname):
        if len(hostname.split(':')) == 2:
            hostname = hostname.split(':')[0]

        for idx, c in enumerate(self.connections):
            if c.host == hostname:
                self.connections[idx].stop()
                self.connections.pop(idx)
                self.devices.pop(hostname)
                devs = []
                for dev in self.devicenames.keys():
                    namesplit = dev.split(':')
                    if hostname == namesplit[0]:
                        devs.append(dev)
                for dev in devs:
                    self.devicenames.pop(dev)
                    self.pluginStatus.pop(dev)
                if self.logger.reloadDevicesCallback is not None:
                    self.logger.reloadDevicesCallback()
                return True
        return False

    def getConnection(self, host):
        for idx, c in enumerate(self.connections):
            if host == c.host:
                return self.connections[idx]
        return None

    def getDevices(self):
        devices = {}
        for c in self.connections:
            devices[c.host] = c.pluglist
        self.devices = devices
        return devices

    def getRemoteDeviceList(self):
        devices = self.getDevices()
        # print(devices)
        for host in devices.keys():
            for device in devices[host]:
                self.devicenames[host+":"+device] = host+":"+device
                self.pluginStatus[host+":"+device] = devices[host][device]['status']
        if self.logger.reloadDevicesCallback is not None:
            self.logger.reloadDevicesCallback()
        return devices

    def getParam(self, host, device, param):
        # for c in self.connections:
        #     if host == c.host:
        #         pass
        current_value = None
        if host in self.devices.keys():
            devices = self.devices[host]
            if device in devices.keys():
                parameters = devices[device]['parameters']
                for par in parameters:
                    if par[0] == param:
                        current_value = par[1]
                        break
        return current_value

    def callFuncOrParam(self, host, device, function, value):
        for c in self.connections:
            if host == c.host:
                return c.callPluginFunction(device, function, value)

    def callFuncOrParam2(self, host, device, function, *args):
        value = list(args)
        return self.callFuncOrParam(host, device, function, value)

    def resize(self, host, newsize):
        for c in self.connections:
            if host == c.host:
                c.resizeLogger(newsize)

    def clearHost(self, host, signals='all'):
        for c in self.connections:
            if host == c.host:
                c.clear(signals=signals)
                print('cleared')

    def toggleDevice(self, host, device, state=None):
        if state == None:
            state = True
        elif type(state) == bool:
            pass
        else:
            state = state.isChecked()
        for c in self.connections:
            if host == c.host:
                c.toggleDevice(device, state)
                time.sleep(0.1)
                if self.logger.reloadDevicesRAWCallback is not None:
                    self.logger.reloadDevicesRAWCallback()

    def downloadSession(self, host, savedir='~/RTOC-RemoteSession.json'):
        for c in self.connections:
            if host == c.host:
                jsonfile = c.getSession()
                with open(savedir, 'w') as fp:
                    json.dump(jsonfile, fp, sort_keys=False, indent=4, separators=(',', ': '))

                return True

    def activeConnections(self):
        return [c.host for c in self.connections]

    def pauseHost(self, host, value):
        for c in self.connections:
            if host == c.host:
                c.pause = value

    def searchTCPHosts(self, port=5050, emitter=None):
        hostlist = []
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        ip_parts = ip.split('.')
        base_ip = ip_parts[0] + '.' + ip_parts[1] + '.' + ip_parts[2] + '.'
        if nmap is not None:
            nm = nmap.PortScanner()
            ans = nm.scan(base_ip+'0-255', str(port))
            for ip in ans['scan'].keys():
                if ans['scan'][ip]['tcp'][port]['state'] != 'closed':
                    if len(ans['scan'][ip]['hostnames']) > 0:
                        for hostname in ans['scan'][ip]['hostnames']:
                            if hostname['name'] != '':
                                hostlist.append(hostname['name'])
                    else:
                        hostlist.append(ip)
        if emitter != None:
            emitter.emit(hostlist)
        return hostlist
