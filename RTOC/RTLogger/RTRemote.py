import time
# from threading import Thread
import traceback
import json
import socket
from ..LoggerPlugin import LoggerPlugin
import logging as log


log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

try:
    import nmap
except ImportError:
    logging.warning('nmap for python not installed! Install with "pip3 install python-nmap"')
    nmap = None


class _SingleConnection(LoggerPlugin):
    def __init__(self, stream=None, plot=None, event=None, host='127.0.0.1', port=5050, name='RemoteDevice', password='', logger=None):
        # Plugin setup
        super(_SingleConnection, self).__init__(stream, plot, event)
        self.setDeviceName(name)
        self.logger = logger
        self.host = host
        self.name = name
        self.port = port

        self.getPlugins = True
        self.getSignals = True
        self.getEvents = True

        self.pause = False
        self.maxLength = 0
        self.status = 'connecting...'
        self.siglist = []
        self.sigSelectList = []
        self.pluglist = []
        self.eventlist = {}

        self.xmax = time.time() + 60*60
        self.xmin = self.xmax - 60*60*24
        self.maxN = 1000
        #self.createTCPClient(host, None, port)
        self.tcppassword = password
        self.updateRemoteCallback = None
        self.setPerpetualTimer(self.updateT, samplerate=1)
        self.startTCPLogging()

    # THIS IS YOUR THREAD

    def updateT(self):
        if not self.pause:
            self.getAll(self.getSignals, self.getEvents, self.getPlugins)

    def getAll(self, signals=True, events=True,plugins=True):
        self.status = 'connecting...'
        if signals:
            ans1 = self.getAllSignals()
        else:
            ans1 = True
        if events:
            ans2 = self.getAllEvents()
        else:
            ans2 = True
        ans3 = self.getAllInfo()
        if plugins:
            ans4 = self.getAllPlugins()
        else:
            ans4 = True
        ans = [ans1, ans2, ans3, ans4]
        logging.debug(ans)
        if any(ans) == True:
            if self.updateRemoteCallback is not None and self.status != "connected":
                self.status = "connected"
                self.updateRemoteCallback()
        else:
            self.status = "error"
            if self.updateRemoteCallback is not None:
                self.updateRemoteCallback()

    def getAllSignals(self):
        ans = self._sendTCP(getSignalList=True)
        if ans:
            if 'signalList' in ans.keys():
                if ans['signalList'] != self.siglist:
                    self.siglist = ans['signalList']
                    if self.updateRemoteCallback is not None:
                        self.updateRemoteCallback()
                    # self.updateList()
                if self.siglist != []:
                    selection = []  # self.siglist
                    #selection = [".".join(i) for i in selection]
                    for i in self.siglist:
                        if i in self.sigSelectList and len(i[0].split(':')) == 1:
                            selection.append(".".join(i))
                    for s in selection:
                        ssplit = s.split('.')
                        ans = self._sendTCP(getSignal={'dname':ssplit[0], 'sname':ssplit[1], 'xmin': self.xmin, 'xmax': self.xmax, 'maxN': self.maxN})
                        if ans != False:
                            if 'signals' in ans.keys():
                                for sig in ans['signals'].keys():
                                    signame = sig.split('.')
                                    s = ans['signals'][sig]
                                    u = s[2]
                                    self.logger.database.plot(s[0], s[1], sname=signame[1],
                                              dname=self.name+":"+signame[0], unit=u)
                return True
        return False

    def getAllEvents(self):
        ans = self._sendTCP(getEventList=True)
        if ans:
            if 'events' in ans.keys():
                if ans['events'] != self.eventlist:
                    selection = {}
                    for evID in ans['events'].keys():
                        name = ans['events'][evID][0:2]
                        if name in self.sigSelectList and len(name[0].split(':')) == 1:
                            selection[evID] = ans['events'][evID]
                    self.updateEvents(selection)
                return True
        return False

    def getAllInfo(self):
        ans = self._sendTCP(logger={'info': True})
        if ans:
            if 'logger' in ans.keys():
                maxLength = ans['logger']['info']['recordLength']
                if maxLength != self.maxLength:
                    self.maxLength = maxLength
                    if self.updateRemoteCallback is not None:
                        self.updateRemoteCallback()
                return True
        return False

    def getAllPlugins(self):
        ans = self._sendTCP(getPluginList=True)
        if ans:
            if 'pluginList' in ans.keys():
                if ans['pluginList'] != self.pluglist:
                    self.pluglist = ans['pluginList']
                return True
        return False

    def updateEvents(self, newEventList):
        # {ID: [DEVICE_ID,SIGNAL_ID,EVENT_ID,TEXT,TIME,VALUE,PRIORITY], ...}
        for evID in newEventList.keys():
            if evID not in self.eventlist.keys():
                # self.eventlist[evID] = newEventList[evID]
                ev = newEventList[evID]
                self.event(x=ev[4], text=ev[3], sname=str(ev[1]),
                           dname=self.name+":"+str(ev[0]), priority=ev[6])

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
        # logging.debug(ans)

    def stop(self):
        self.close()
        self.siglist = []
        self.pluglist = []
        self.eventlist = {}
        logging.info('Remote-Connection to {} stopped'.format(self.host))

    def startTCPLogging(self):
        if self.run:
            self.cancel()
        else:
            self.createTCPClient(self.host, self.tcppassword, self.port)
            try:
                ok = self._sendTCP()
                # logging.debug(ok)
                if ok is None:
                    self.status = 'protected'
                elif ok != False:
                    ok = True
            except Exception:
                tb = traceback.format_exc()
                logging.debug(tb)
                ok = False
            if ok:
                self.getAll()
                self.start()
                self.status = 'connected'
            elif ok is False:
                self.__base_address = ""
                self.cancel()
                self.status = "error"
            else:
                self.__base_address = ""
                self.cancel()
                self.status = "wrongPassword"

    def getSession(self):
        ans = self._sendTCP(getSession=True)
        if ans:
            # logging.debug(ans)
            return ans['session']

    def callPluginFunction(self, device, function, parameter):
        ans = self._sendTCP(plugin={device: {function: parameter}})
        return ans

    def saveSettings(self, host, port, name, password):
        for c in self.logger.config['tcp']['knownHosts'].keys():
            if c == self.host+":"+str(self.port):
                self.logger.config['tcp']['knownHosts'].pop(c)
                break
        self.logger.config['tcp']['knownHosts'][host+':'+str(port)] = [name, password]
        self.host = host
        self.port = port
        self.name = name
        self.tcppassword = password
        self.stop()
        self.start()


class RTRemote():
    """
    This class handles connections to other RTOC-servers.
    """
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
        self.logger.config['tcp']['remoteRefreshRate'] = samplerate
        for c in self.connections:
            c.samplerate = samplerate

    def connect(self, hostname='127.0.0.1', port=5050, name='RemoteDevice', password=''):
        if len(hostname.split(':')) == 2:
            port = int(hostname.split(':')[1])
            hostname = hostname.split(':')[0]

        for c in self.connections:
            if c.host == hostname and c.port == port:
                c.tcppassword = password
                if not c.run:
                    c.start()
                    self.getRemoteDeviceList()
                return

        newConnection = _SingleConnection(
            self.logger.database.addDataCallback, self.logger.database.plot, self.logger.database.addNewEvent, hostname, port, name, password, self.logger)
        #newConnection.tcppassword = password
        # if newConnection.run:
        newConnection.samplerate = self.logger.config['tcp']['remoteRefreshRate']
        self.connections.append(newConnection)
        self.getRemoteDeviceList()

    def disconnect(self, hostname):
        if len(hostname.split(':')) == 2:
            hostname = hostname.split(':')[0]

        for idx, c in enumerate(self.connections):
            if c.host == hostname:
                self.connections[idx].stop()
                self.connections.pop(idx)
                self.devices.pop(c.name)
                devs = []
                for dev in self.devicenames.keys():
                    namesplit = dev.split(':')
                    if c.name == namesplit[0]:
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

    def getConnectionName(self, name):
        for idx, c in enumerate(self.connections):
            if name == c.name:
                return self.connections[idx]
        return None

    def getDevices(self):
        devices = {}
        for c in self.connections:
            devices[c.name] = c.pluglist
        self.devices = devices
        return devices

    def getRemoteDeviceList(self):
        devices = self.getDevices()
        # logging.debug(devices)
        for name in devices.keys():
            for device in devices[name]:
                self.devicenames[name+":"+device] = name+":"+device
                self.pluginStatus[name+":"+device] = devices[name][device]['status']
        if self.logger.reloadDevicesCallback is not None:
            self.logger.reloadDevicesCallback()
        return devices

    def getParam(self, name, device, param):
        # for c in self.connections:
        #     if name == c.name:
        #         pass
        current_value = None
        if name in self.devices.keys():
            devices = self.devices[name]
            if device in devices.keys():
                parameters = devices[device]['parameters']
                for par in parameters:
                    if par[0] == param:
                        current_value = par[1]
                        break
        return current_value

    def callFuncOrParam(self, name, device, function, value):
        for c in self.connections:
            if name == c.name:
                return c.callPluginFunction(device, function, value)

    def callFuncOrParam2(self, name, device, function, *args):
        value = list(args)
        return self.callFuncOrParam(name, device, function, value)

    def resize(self, name, newsize):
        for c in self.connections:
            if name == c.name:
                c.resizeLogger(newsize)

    def clearHost(self, name, signals='all'):
        for c in self.connections:
            if name == c.name:
                c.clear(signals=signals)
                logging.debug('Remote hosts cleared')

    def toggleDevice(self, name, device, state=None):
        if state is None:
            state = True
        elif type(state) == bool:
            pass
        else:
            state = state.isChecked()
        for c in self.connections:
            if name == c.name:
                c.toggleDevice(device, state)
                time.sleep(0.1)
                if self.logger.reloadDevicesRAWCallback is not None:
                    self.logger.reloadDevicesRAWCallback()

    def downloadSession(self, name, savedir='~/RTOC-RemoteSession.json'):
        for c in self.connections:
            if name == c.name:
                jsonfile = c.getSession()
                with open(savedir, 'w') as fp:
                    json.dump(jsonfile, fp, sort_keys=False, indent=4, separators=(',', ': '))

                return True

    def activeConnections(self):
        return [c.name for c in self.connections]

    def pauseHost(self, name, value):
        for c in self.connections:
            if name == c.name:
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
        if emitter is not None:
            emitter.emit(hostlist)
        return hostlist
