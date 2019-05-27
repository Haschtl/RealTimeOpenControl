# LoggerPlugin v2.1
import traceback
import time
import sys
import os
from threading import Thread, Timer, Lock
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

try:
    from . import jsonsocket
except (SystemError, ImportError):
    import jsonsocket

lock = Lock()


class LoggerPlugin:
    """
    This class is imported by any plugin written for RTOC.

    It includes all functions to interact with RTOC. Every plugin must inherit this class! Your plugin must look like this:

    ..  code-block:

    ::

        from RTOC.LoggerPlugin import LoggerPlugin

        class Plugin(LoggerPlugin):
            def __init__(self, stream=None, plot=None, event=None):
                LoggerPlugin.__init__(self, stream, plot, event)
                ...
            ...

    Args:
        stream (method): The callback-method for the stream-method
        plot (method): The callback-method for the plot-method
        event (method): The callback-method for the event-method

    """
    def __init__(self, stream=None, plot=None, event=None):
        # Plugin setup
        # self.setDeviceName()
        self._deviceName = "noDevice"
        self.__cb = stream
        self.__ev = event
        self.__plt = plot
        self._sock = None
        self._tcppassword = ''
        self._tcpport = 5050
        self._tcpaddress = ''
        self._tcpthread = False
        self._pluginThread = None
        self.__oldPerpetualTimer = False
        self.lockPerpetialTimer = Lock()
        # -------------
        self.run = False  # False -> stops thread
        """ Use this parameter to start/stop threads. This makes sure, RTOC can close your plugin correctly."""
        self.smallGUI = False
        """ If this is True, the plugin-GUI will be shown in a dropdown menu (GUI related)"""
        self.widget = None
        """ Replace this with your QWidget to enable the plugin-GUI"""
        self.__samplerate = 1

    def getDir(self, dir=None):
        """
        Returns:
            Path of your plugin
        """
        if dir is None:
            dir = __file__
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/plugins'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(dir))

        return packagedir

    def stream(self, **kwargs):
        """
        Use this function to send new measurements to RTOC. You can send multiple signals at once.

        This function is a wrapper for :py:meth:`.RT_data.addData`


        You can choose one of three ways to send measurements.

        **dict**

        Args:
            list (dict): A dict containing keys like this: `{'Temperature':[28,'°C'], 'Voltage':[12,'V']}`
            dname (str): The devicename of this signal, e.g: `'Freezer'`

        **list**

        Args:
            list (list): A list containing these lists: `[y, dname, unit]`. E.g: `[[28,'Temperature','°C'],[12,'Voltage','V']]`
            dname (str): The devicename of this signal, e.g: `'Freezer'`

        **seperate**

        Args:
            y (list): A list containing all measured values, e.g: `[28, 12]`
            snames (list): A list containing all signalnames, e.g: `['Temperature','Voltage']`
            dname (str): The devicename of this signal, e.g: `'Freezer'`
            unit [optional] (list): A list containing all units, e.g: `['°C', 'V']`
            x [optional] (list): A list containing all x-data. In a normal dataseries x is always set to time.time().

        Returns:
            bool: True, if data was sent successfully, False, if not.

        """
        if 'units' in kwargs:
            kwargs['unit'] = kwargs['units']
            kwargs.pop('units')
        if self.__cb:
            now = time.time()
            signallist = kwargs.get('list', None)
            if 'dname' not in kwargs:
                kwargs['dname'] = self._deviceName
            if signallist is None:
                y = kwargs.get('y', [0])
                if type(y) == list:
                    kwargs['x'] = [now]*len(y)
                else:
                    kwargs['x'] = [now]


                self.__cb(**kwargs)
                return True
            elif type(signallist) == list:
                kwargs.pop('list')
                kwargs['y'] = []
                kwargs['x'] = []
                kwargs['unit'] = []
                kwargs['snames'] = []
                for sig in signallist:
                    if type(sig) == list:
                        if len(sig) == 3:
                            kwargs['y'].append(sig[0])
                            kwargs['snames'].append(sig[1])
                            kwargs['unit'].append(sig[2])
                            kwargs['x'].append(now)
                self.__cb(**kwargs)
                return True
            elif type(signallist) == dict:
                kwargs.pop('list')
                for dev in signallist.keys():
                    kwargs = {}
                    kwargs['dname'] = dev
                    kwargs['y'] = []
                    kwargs['x'] = []
                    kwargs['unit'] = []
                    kwargs['snames'] = []
                    if type(signallist[dev]) == dict:
                        for sig in signallist[dev].keys():
                            if type(signallist[dev][sig]) == list:
                                if len(signallist[dev][sig]) == 2:
                                    kwargs['y'].append(signallist[dev][sig][0])
                                    kwargs['snames'].append(sig)
                                    kwargs['unit'].append(signallist[dev][sig][1])
                                    kwargs['x'].append(now)
                                else:
                                    logging.error('STREAM ERROR, signal has not this format: [y, "unit"]')
                            else:
                                logging.error('STREAM_ERROR: One signal was malformed')
                        # logging.debug(kwargs)
                        self.__cb(**kwargs)
                    else:
                        logging.error('STREAM_ERROR: One device was malformed')
                return True
            else:
                logging.error('STREAM_ERROR: The data you provided with in your plugin was wrong."')
        else:
            logging.error('STREAM_ERROR: cannot stream signals. No callback connected')
        return False

    def plot(self, x=[], y=[], sname='noName', dname=None, unit='', hold='off', autoResize=False):
        """
        Use this function to send a signal to RTOC. You can send multiple x-y-pairs for one signal.
        You can either replace the data, which is currently stored in RTOC, if the parameter `hold` is `off` (default).

        Or you can append the data to the existing data with `hold ='on'`.

        `hold='mergeX'` will only add xy-pairs, if the x-value is not in the existing data.

        `hold='mergeY'` will only add xy-pairs, if the y-value is not in the existing data.


        This function is a wrapper for :py:meth:`.RT_data.plot`

        Args:
            x (list): A list containing all x values, e.g: `[1, 2, 3, 4, 5, 6, 7, 8]`
            y (list): A list containing all y values, e.g: `[28,26,25,24,23,22,22,21]`
            sname (str): The devicename of this signal, e.g: `'Temperature'`
            dname (str): The devicename of this signal, e.g: `'Freezer'`
            unit (str): The signal unit, e.g: `'°C'`
            hold ('off','on','mergeX' or 'mergeY'): Defines, how RTOC handles the data. (Default: 'off')
            autoResize (bool): Tell RTOC, to resize the recordLength, if data is too long. (Default: False)

        Returns:
            bool: True, if data was sent successfully, False, if not.

        """
        if y == []:
            y = x
            x = list(range(len(x)))
        if dname is None:
            dname = self._deviceName
        if self.__plt:
            self.__plt(x, y, sname, dname, unit, hold=hold, autoResize=autoResize)
            return True
        else:
            logging.warning("No event connected")
            return False

    def event(self, text='', sname=None, dname=None, priority=0, id=None, value=None, x=None):
        """
        Use this function to send an event to RTOC.

        This function is a wrapper for :py:meth:`.RT_data.addNewEvent`

        Args:
            text (str): A description of this event, e.g: `'Freezer door opened'`
            sname (str): The devicename of this event, e.g: `'Temperature'`
            dname (str): The devicename of this event, e.g: `'Freezer'`
            priority (int): 0: Information, 1: Warning, 2: Error
            id (str): Apply an id to this event. This id is used to trigger **Actions**
            value (any): Unused
            x (float): Set a custom timestamp (Default: time.time())

        Returns:
            bool: True, if data was sent successfully, False, if not.

        """

        if sname is None:
            sname = "unknownEvent"
        if dname is None:
            dname = self._deviceName
        if self.__ev:
            self.__ev(text, sname, dname, x, priority, value=value, id=id)
            return True
        else:
            logging.warning("No event connected")
            return False

    def createTCPClient(self, address="localhost", password=None, tcpport=5050, threaded=False):
        '''
        Creates a TCP client. Used to talk to RTOC via TCP. Read :doc:`TCP` for more information.
        You need to call this once, before you can use `sendTCP()`

        Args:
            address (str): address of RTOC-server. (Default: localhost)
            password (str or None): Provide a encryption-password, if RTOC server is password protected.
            tcpport (int): TCP-Port of RTOC-server. (Default: 5050)
            threaded (bool): If you want to transmit the data in a seperate thread, set `threaded=True`. If you need the tcp-response, set `threaded=False`.
        '''
        if threaded:
            self._tcpthread = True
        else:
            self._tcpthread = False

        self._tcpaddress = address
        self._tcpport = tcpport
        self._sock = jsonsocket.Client()
        if password is not None:
            self._tcppassword = password
            self._sock.setKeyword(password)

    def sendTCP(self, *args, **kwargs):
        """
        Use any of the arguments described in :doc:`TCP`.

        Before you can use this function, you need to connect to a server with `createTCPClient()`.

        Args:
            x (list): A list containing x-values
            y (list): A list containing y-values
            sname (list or str): list, if plot is False. str, if plot is True.
            dname (str): Devicename of signal/event
            unit (list or str): Signal-unit
            plot (bool): False: xy-pairs are interpreted as different signals, True: xy-pairs are one signal
            event ([text, id, value]): Submit an event
            remove: :py:meth:`.NetworkFunctions.remove`
            plugin: :py:meth:`.NetworkFunctions.handleTcpPlugins`
            logger: :py:meth:`.NetworkFunctions.handleTcpLogger`
            getSignal: :py:meth:`.NetworkFunctions.getSignal`
            getLatest: :py:meth:`.NetworkFunctions.getLatest`
            getEvent: :py:meth:`.NetworkFunctions.getEvent`
            getSignalList: :py:meth:`.NetworkFunctions.getSignalList`
            getEventList: :py:meth:`.NetworkFunctions.getEventList`
            getPluginList: :py:meth:`.NetworkFunctions.getPluginList`
            getSession: :py:meth:`.RT_data.generateSessionJSON`

        Returns:
            tcp_response (dict), if createTCPClient(threaded=False)

            None, if createTCPClient(threaded=True)

        """
        if self._tcpthread:
            t = Thread(target=self._sendTCP, args=(args, kwargs,))
            t.start()
        else:
            return self._sendTCP(*args, **kwargs)

    def _sendTCP(self, *args, **kwargs):
        with lock:
            y = kwargs.get('y', None)
            sname = kwargs.get('sname', None)
            dname = kwargs.get('dname', self._deviceName)
            unit = kwargs.get('unit', None)
            x = kwargs.get('x', None)
            getsignals = kwargs.get('getSignal', None)
            latest = kwargs.get('getLatest', None)
            events = kwargs.get('getEvent', None)
            signallist = kwargs.get('getSignalList', False)
            eventlist = kwargs.get('getEventList', False)
            pluginlist = kwargs.get('getPluginList', False)
            session = kwargs.get('getSession', False)
            plot = kwargs.get('plot', False)
            event = kwargs.get('event', None)
            remove = kwargs.get('remove', None)
            plugin = kwargs.get('plugin', None)
            logger = kwargs.get('logger', None)
            signals = kwargs.get('stream', None)

            for idx, arg in enumerate(args):
                if idx == 0:
                    y = arg
                if idx == 1:
                    sname = arg
                if idx == 2:
                    dname = arg
                if idx == 3:
                    unit = arg
                if idx == 4:
                    x = arg

            if x is None and y is not None and not plot:
                x = [time.time()]*len(y)
            dicti = {}
            if y is not None:
                dicti['plot'] = plot
                dicti['y'] = y
                dicti['x'] = x
                dicti['sname'] = sname
                dicti['dname'] = dname
                dicti['unit'] = unit
            if signallist:
                dicti['getSignalList'] = True
            if eventlist:
                dicti['getEventList'] = True
            if event is not None:
                dicti['event'] = event
            if events is not None:
                dicti['getEvent'] = events
            if getsignals is not None:
                dicti['getSignal'] = getsignals
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
            if session:
                dicti['getSession'] = True
            # if self._tcppassword != '' and self._tcppassword is not None:
                # hash_object = hashlib.sha256(self._tcppassword.encode('utf-8'))
                # hex_dig = hash_object.hexdigest()
                # dicti['password'] = hex_dig
            if self._sock:
                try:
                    self._sock.connect(self._tcpaddress, self._tcpport, self._tcppassword)
                    self._sock.send(dicti)
                    response = self._sock.recv()
                    # self._sock.close()
                    if response is None:
                        # if 'password' in response.keys():
                        logging.error('passwordprotected')
                        return None
                    else:
                        return response
                except ConnectionRefusedError:
                    logging.error('TCP Connection refused')
                    try:
                        self._sock.close()
                    except Exception:
                        logging.debug(traceback.format_exc())
                    return False
                except Exception:
                    tb = traceback.format_exc()
                    logging.debug(tb)
                    logging.error("Error sending over TCP")
                    try:
                        self._sock.close()
                    except Exception:
                        logging.debug(traceback.format_exc())
                    self._sock = jsonsocket.Client()
                    return False
                finally:
                    self._sock.close()
            else:
                logging.error("Please createTCPClient first")
                self.createTCPClient()
                return False

    def setDeviceName(self, devicename="noDevice"):
        """
        Use this function to set a default devicename. If you do this, you don't need to submit the devicename with any call of any function

        Args:
            devicename (str): Default: `'noDevice'`

        Returns:
            None
        """
        self._deviceName = devicename    # Is shown in GUI

    def close(self):
        """
        This function stops threads using `self.run`. It also closes the QWidget.

        Normally this function is only called by RTOC, when disconnecting plugins, but you can also call it.
        """
        self.run = False
        if self.widget:
            self.widget.hide()
            self.widget.close()
        if self._pluginThread and not self.__oldPerpetualTimer:
            self._pluginThread.cancel()

        # if self._sock:
            # self._sock.close()

    def setSamplerate(self, rate):
        """
        Sets the samplerate [Hz] of the defined perpetual timer.

        Args:
            rate (float)

        Returns:
            bool: True, if perpetual timer was already configured, False, if not.

        """
        if self._pluginThread is not None:
            self.samplerate = rate
            return True
        else:
            return False

    def setInterval(self, interval):
        """
        Sets the interval [s] of the defined perpetual timer.

        Args:
            interval (float)

        Returns:
            bool: True, if perpetual timer was already configured, False, if not.

        """
        if self._pluginThread is not None:
            self.samplerate = 1/interval
            return True
        else:
            return False

    @property
    def samplerate(self):
        return self.__samplerate

    @samplerate.setter
    def samplerate(self, samplerate):
        self.__samplerate = samplerate
        if self._pluginThread and not self.__oldPerpetualTimer:
            self._pluginThread.setSamplerate(samplerate)

    def setPerpetualTimer(self, fun, samplerate=None, interval = None, old = False):
        """
        Configures a perpetual timer. A perpetual timer is a thread, which is repeated infinitly in a specified time-interval or samplerate.

        Args:
            fun (function): The function to be called periodically.
            samplerate (float): The desired samplerate.
            interval (float): The desired time-delay interval.
            old (bool): If True, an old method for perpetual timer is used (based on :mod:`threading.Thread`). If False, the new method will be used (based on :mod:`threading.Timer`).

        Returns:
            bool: True, if perpetual timer could be configured, False, if not.

        """
        if old:
            self.__oldPerpetualTimer = True
        else:
            self.__oldPerpetualTimer = False

        if samplerate is None and interval is None:
            samplerate = self.samplerate
        elif samplerate is None:
            samplerate = 1/interval

        if not self.__oldPerpetualTimer:
            try:
                self.__samplerate = samplerate
                self._pluginThread = _perpetualTimer(fun, samplerate, self.lockPerpetialTimer)
                return True
            except Exception:
                self._pluginThread = None
                return False
        else:
            try:
                self.__samplerate = samplerate
                self._pluginThread = Thread(target=self.__updateT, args=(fun,))
                return True
            except Exception:
                self._pluginThread = None
                return False

    def start(self):
        """
        Starts the perpetual timer

        Returns:
            bool: True, if perpetual timer was already configured, False, if not.

        """
        if self._pluginThread:
            self.run = True
            self._pluginThread.start()
            return True
        else:
            self.run = False
            return False

    def cancel(self):
        """
        Stops the perpetual timer

        Returns:
            bool: True, if perpetual timer was already configured, False, if not.

        """
        if self._pluginThread:
            if not self.__oldPerpetualTimer:
                self._pluginThread.cancel()
            self.run = False
            return True
        else:
            self.run = False
            return False

    def __updateT(self, func):
        diff = 0
        while self.run:
            if diff < 1/self.__samplerate:
                time.sleep(1/self.__samplerate-diff)
            start_time = time.time()
            func()
            diff = (time.time() - start_time)



class _perpetualTimer():
    def __init__(self, hFunction, samplerate=1, lock=None):
        self._samplerate = samplerate
        self._lock = lock
        self._hFunction = hFunction
        self._thread = None

    def _handle_function(self):
        start = time.time()
        with self._lock:
            self._hFunction()
        diff = time.time() - start
        timedelta = 1/self._samplerate - diff
        if timedelta < 0:
            timedelta = 0
        self._thread = Timer(timedelta, self._handle_function)
        self._thread.start()

    def setSamplerate(self, rate):
        if rate != self._samplerate:
            self._samplerate = rate
            if self._thread is not None:
                self.cancel()
            self._thread = Timer(1/self._samplerate, self._handle_function)
            self._thread.start()

    def getSamplerate(self):
        return self._samplerate

    def start(self):
        self._thread = Timer(0, self._handle_function)
        self._thread.start()

    def cancel(self):
        if self._thread is not None:
            self._thread.cancel()
            self._thread = None
