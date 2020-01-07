import time
# from threading import Thread
import traceback
import json
import socket
import logging as log
from .RTWebsocketClient import RTWebsocketClient

log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

try:
    import nmap
except ImportError:
    logging.warning('nmap for python not installed! Install with "pip3 install python-nmap"')
    nmap = None


class _SingleConnection():
    def __init__(self, parent, host='127.0.0.1', port=5050, name='RemoteDevice', password='', logger=None, ssl=False):
        # Plugin setup
        self.logger = logger
        self.parent = parent
        self.host = host
        self.name = name
        self.port = port
        self.__password = password
        self.ssl = ssl

        self.getPlugins = True
        self.getSignals = True
        self.getEvents = True

        self.connected = False

        self.pause = False
        self.maxLength = 0
        self.status = 'connecting...'
        self.siglist = []
        self._sigSelectList = []
        self.pluglist = []
        self.eventlist = {}

        self.xmax = time.time() + 60*60
        self.xmin = self.xmax - 60*60*24
        self.maxN = 1000
        self.__password = password
        self.updateRemoteCallback = None

        self.connect()

    def connect(self, host=None, port=None, password=None, ssl=None):
        if host != None and type(host)==str:
            self.host = host
        if port != None and type(port)==int:
            self.port = port
        if password != None and type(password)==str:
            self.__password = password
        if self.port == 443:
            self.ssl = True
        if ssl != None and type(ssl)==bool:
            self.ssl = ssl
        self.RTwebsocket = RTWebsocketClient()
        self.RTwebsocket.on_open = self.initAfterConnection
        self.RTwebsocket.on_error = self.connectionError
        self.RTwebsocket.on_close = self.connectionClosed
        self.RTwebsocket.handle_signal = self.handle_signal
        self.RTwebsocket.handle_event = self.handle_event
        self.RTwebsocket.handle_pluginList = self.handle_pluginList
        self.RTwebsocket.handle_signalList = self.handle_signalList
        self.RTwebsocket.handle_events = self.handle_events
        self.RTwebsocket.handle_logger = self.handle_logger
        self.RTwebsocket.handle_authorize = self.handle_authorize
        self.RTwebsocket.handle_RTOCError = self.handle_RTOCError
        print('Connecting to {}:{} with {} and ssl: {}'.format(self.host, self.port, self.__password, self.ssl))
        self.RTwebsocket.connect(self.host, self.port, self.__password, self.ssl)

    def initAfterConnection(self):
        # print('Successfully connected')
        self.status = 'connecting...'
        # self.RTwebsocket.send(subscribeAll='signal')
        self.RTwebsocket.send(getPluginList=True)
        self.RTwebsocket.send(logger={'info':True})
        self.RTwebsocket.send(getSignalList=True)
        self.RTwebsocket.send(getEventList=10)

        if self.updateRemoteCallback is not None:
            self.updateRemoteCallback()

    def handle_RTOCError(self):
        print('Protection error')
        self.status = 'protected'
        self.connected = False

    def connectionError(self, error):
        print('Connection error')
        self.status = "error"
        self.connected = False

    def connectionClosed(self):
        print('Connection has been closed')
        self.status = "closed"
        self.connected = False

    def handle_authorize(self, value):
        if value:
            print('Connection has been establlished')
            self.status = "connected"
            self.connected = True
        else:
            print('Connection is password protected')
            self.status = "protected"
            self.connected = False



    def handle_signal(self, signal):
        self.connected = True
        self.status = 'connected'
        # self.logger.database.plot(signal['x'], signal['y'], sname=signal['sname'],
        #             dname=self.name+":"+signal['dname'], unit=signal['unit'])
        if signal['dname'].startswith(self.name+':'):
            return
        if signal['dname']+'.'+signal['sname'] not in self.siglist:
            self.siglist.append(signal['dname']+'.'+signal['sname'])
            if self.updateRemoteCallback is not None:
                self.updateRemoteCallback()
        if signal['dname']+'.'+signal['sname'] not in self.sigSelectList:
            return
        self.logger.database.plot(signal['x'], signal['y'], sname=signal['sname'],
                    dname=self.name+":"+signal['dname'], unit=signal['unit'], hold="on")
        # if self.updateRemoteCallback is not None:
        #     self.updateRemoteCallback()

    def handle_event(self, event):
        print('Remote got event')
        self.connected = True
        self.status = 'connected'
        self.logger.database.addNewEvent(event['text'], event['sname'], self.name+":"+str(event['dname']), x=event['x'], priority=event['priority'], id=event['eventId'], value=event['value'])
        # if self.updateRemoteCallback is not None:
        #     self.updateRemoteCallback()

    def handle_pluginList(self, pluginList):
        print('Remote got pluginlist')
        self.connected = True
        self.status = 'connected'
        if pluginList != self.pluglist:
            self.pluglist = pluginList
            self.parent.getRemoteDeviceList()
        # if self.updateRemoteCallback is not None:
        #     self.updateRemoteCallback()
    
    def handle_signalList(self, signalList):
        print('Remote got signallist')
        # signalList = ['.'.join(sig) for sig in signalList]
        self.connected = True
        self.status = 'connected'
        if signalList != [sig.split('.') for sig in self.siglist]:
            # self.siglist = []
            for sig in signalList: 
                if not sig[0].startswith(self.name+':'):
                    self.siglist.append('.'.join(sig))
            # self.siglist = ['.'.join(i) for i in signalList]
            # if self.siglist != []:
            #     selection = []  # self.siglist
            #     #selection = [".".join(i) for i in selection]
            #     for i in self.siglist:
            #         if i in self.sigSelectList and len(i[0].split(':')) == 1:
            #             selection.append(".".join(i))
            if self.updateRemoteCallback is not None:
                self.updateRemoteCallback()

    @property
    def sigSelectList(self):
        return self._sigSelectList

    @sigSelectList.setter
    def sigSelectList(self, newList):
        oldList = list(self._sigSelectList)
        for sig in newList:
            if sig not in oldList:
                self.RTwebsocket.send(subscribe=['signal', sig])
        for sig in oldList:
            if sig not in newList:
                self.RTwebsocket.send(unsubscribe=['signal', sig])
        # if newList != oldList:
        #     if self.updateRemoteCallback is not None:
        #         self.updateRemoteCallback()
        self._sigSelectList = newList


    def handle_events(self, events):
        print('handle events')
        self.status = 'connected'
        pass

    def handle_logger(self, logger):
        print('handle logger')
        self.connected = True
        self.status = 'connected'
        maxLength = logger['info']['config']['global']['recordLength']
        if maxLength != self.maxLength:
            self.maxLength = maxLength
            # if self.updateRemoteCallback is not None:
            #     self.updateRemoteCallback()

    def getSignal(self, dname, sname):
        self.connected = True
        self.status = 'connected'
        self.RTwebsocket.send(getSignal={'dname':dname, 'sname':sname, 'xmin': self.xmin, 'xmax': self.xmax, 'maxN': self.maxN})

    def resizeLogger(self, newsize):
        self.RTwebsocket.send(logger={'resize': newsize})
        self.maxLength = newsize

    def toggleDevice(self, plugin, state):
        self.RTwebsocket.send(plugin={plugin: {'start': state}})

    def clear(self, signals=[]):
        if signals == []:
            signals = 'all'
        self.RTwebsocket.send(logger={'clear': signals})
        # logging.debug(ans)

    def stop(self):
        self.RTwebsocket.disconnect()
        self.siglist = []
        self.pluglist = []
        self.eventlist = {}
        logging.info('Remote-Connection to {} stopped'.format(self.host))

    def getSession(self):
        self.RTwebsocket.send(getSession=True)

    def callPluginFunction(self, device, function, parameter):
        self.RTwebsocket.send(plugin={device: {function: parameter}})

    def saveSettings(self, host, port, name, password):
        for c in self.logger.config['websocket']['knownHosts'].keys():
            if c == self.host+":"+str(self.port):
                self.logger.config['websocket']['knownHosts'].pop(c)
                break
        self.logger.config['websocket']['knownHosts'][host+':'+str(port)] = [name, password]
        self.host = host
        self.port = port
        self.name = name
        self.__password = password


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

    def connect(self, hostname=None, port=None, name=None, password=None, ssl=None):
        if len(hostname.split(':')) == 2:
            port = int(hostname.split(':')[1])
            hostname = hostname.split(':')[0]
        for c in self.connections:
            if c.host == hostname and c.port == port:
                # c.__password = password
                # c.ssl = ssl
                if not c.connected:
                    c.connect(hostname, port, password, ssl)
                    self.getRemoteDeviceList()
                return

        newConnection = _SingleConnection(self, hostname, port, name, password, self.logger, ssl)
            # self.logger.database.addDataCallback, self.logger.database.plot, self.logger.database.addNewEvent, 
        # if newConnection.run:
        self.connections.append(newConnection)
        self.getRemoteDeviceList()

    def disconnect(self, hostname, port):
        if len(hostname.split(':')) == 2:
            hostname = hostname.split(':')[0]

        index = -1
        for idx, c in enumerate(self.connections):
            if c.host == hostname and c.port ==port:
                self.connections[idx].stop()
                self.devices.pop(c.name)
                # self.devicenames.pop(c.name)
                # self.pluginStatus.pop(c.name)
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
                index = idx
                break
        if index != -1:
            self.connections.pop(index)
            return True
        else:
            return False

    def getConnection(self, host, port):
        for idx, c in enumerate(self.connections):
            if host == c.host and port == c.port:
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

    def searchWebsocketHosts(self, port=5050, emitter=None):
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
