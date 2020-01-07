# LoggerPlugin v3.0
import traceback
import time
import sys
import os
from threading import Thread, Timer, Lock
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)
from functools import partial
from collections import deque
import datetime


try:
    from .RTLogger import scriptLibrary as rtoc
except (SystemError, ImportError):
    import RTLogger.scriptLibrary as rtoc

lock = Lock()


class LoggerPlugin:
    """
    Args:
        logger (RTLogger): The parent RTLogger-instance
    """
    def __init__(self, logger=None, *args, **kwargs):
        # Plugin setup
        # self.setDeviceName()
        self._devicename = "noDevice"
        self.rtoc = rtoc
        if logger is not None:
            self.logger = logger
            self._cb = logger.database.addDataCallback
            self._ev = logger.database.addNewEvent
            self._plt = logger.database.plot
            self._bot = logger.telegramBot
        else:
            self._logger = None
            self._cb = None
            self._ev = None
            self._plt = None
            self._bot = None
        self.widget = None
        self._pluginThread = None
        self._oldPerpetualTimer = False
        self.lockPerpetialTimer = Lock()
        self._log = deque([], 100)
        # -------------
        self.run = False  # False -> stops thread
        """ Use this parameter to start/stop threads. This makes sure, RTOC can close your plugin correctly."""
        self.smallGUI = False
        """ If this is True, the plugin-GUI will be shown in a dropdown menu (GUI related)"""
        self.widget = None
        """ Replace this with your QWidget to enable the plugin-GUI"""
        self._samplerate = 1

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

    def updateInfo(self):
        self.logger.analysePlugins()

    def stream(self, y=[], snames=[], dname=None, unit=None, x=None, slist=None, sdict=None):
        """
        Use this function to send new measurements to RTOC. You can send multiple signals at once.

        This function is a wrapper for :py:meth:`.RT_data.addData`


        You can choose one of three ways to send measurements.

        **dict**

        Args:
            sdict (dict): A dict containing keys like this: `{'Temperature':[28,'°C'], 'Voltage':[12,'V']}`
            dname (str): The devicename of this signal, e.g: `'Freezer'`

        **list**

        Args:
            slist (list): A list containing these lists: `[y, dname, unit]`. E.g: `[[28,'Temperature','°C'],[12,'Voltage','V']]`
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

        if self._cb:
            now = time.time()
            if dname is None:
                dname = self._devicename
            if slist is None and sdict is None:
                if type(y) == int or type(y) == float:
                    y = [y]
                if type(x) != list:
                    x = [now]*len(y)
                if len(y) != len(x):
                    x = [now]*len(y)

                self._cb(y=y, snames=snames, dname=dname, unit=unit, x=x)
                return True
            elif slist is not None:
                y = []
                x = []
                unit = []
                snames = []
                for sig in slist:
                    if type(sig) == list:
                        if len(sig) == 3:
                            y.append(sig[0])
                            snames.append(sig[1])
                            unit.append(sig[2])
                            x.append(now)
                self._cb(y=y, snames=snames, dname=dname, unit=unit, x=x)
                return True
            elif sdict is not None:
                for dev in sdict.keys():
                    dname = dev
                    y = []
                    x = []
                    unit = []
                    snames = []
                    if type(sdict[dev]) == dict:
                        for sig in sdict[dev].keys():
                            if type(sdict[dev][sig]) == list:
                                if len(sdict[dev][sig]) == 2:
                                    y.append(sdict[dev][sig][0])
                                    snames.append(sig)
                                    unit.append(sdict[dev][sig][1])
                                    x.append(now)
                                else:
                                    logging.error('STREAM ERROR, signal {}.{} has not this format: [y, "unit"]'.format(dname, sig))
                            else:
                                logging.error('STREAM_ERROR:signal {}.{} was malformed.'.format(dname, sig))
                        self._cb(y=y, snames=snames, dname=dname, unit=unit, x=x)
                    else:
                        logging.error('STREAM_ERROR: device {} was malformed.'.format(dname))
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
            dname = self._devicename
        if self._plt:
            self._plt(x, y, sname, dname, unit, hold=hold, autoResize=autoResize)
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
            dname = self._devicename
        if self._ev:
            self._ev(text, sname, dname, x, priority, value=value, id=id)
            return True
        else:
            logging.warning("No event connected")
            return False

    def setDeviceName(self, devicename="noDevice"):
        """
        Use this function to set a default devicename. If you do this, you don't need to submit the devicename with any call of any function

        Args:
            devicename (str): Default: `'noDevice'`

        Returns:
            None
        """
        self._devicename = devicename    # Is shown in GUI

    def close(self):
        """
        This function stops threads using `self.run`. It also closes the QWidget.

        Normally this function is only called by RTOC, when disconnecting plugins, but you can also call it.
        """
        self.run = False
        if self.widget:
            self.widget.hide()
            self.widget.close()
        if self._pluginThread and not self._oldPerpetualTimer:
            self._pluginThread.cancel()

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
        return self._samplerate

    @samplerate.setter
    def samplerate(self, samplerate):
        self._samplerate = samplerate
        if self._pluginThread is not None and not self._oldPerpetualTimer:
            self._pluginThread.setSamplerate(samplerate)

    def info(self, msg):
        date = str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        message = [date, 0, str(msg)]
        self._log.append(message)
        logging.info(msg)

    def warning(self, msg):
        date = str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        message = [date, 1, str(msg)]
        self._log.append(message)
        logging.warning(msg)

    def error(self, msg):
        date = str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        message = [date, 2, str(msg)]
        self._log.append(message)
        logging.error(msg)

    def debug(self, msg):
        date = str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        message = [date, -1, str(msg)]
        self._log.append(message)
        logging.debug(msg)

    def createPersistentVariable(self, name, fallback=None, dname=None, docs=None):
        """
        Creates a persistent variable, which can be edited and will be restored after restart/reboot.
        You can create it like this:
        self.createPersistentVariable('perVar', 5)

        After this, you can access it's value with 'self.perVar' and edit it in the same way.

        Args:
            name (str): Name of the parameter,
            fallback (any): Alternative value, if parname is not available (for initialization),
            dname (str): Devicename, selected by default

        Returns:
            PersistentVariable: Parameter to be used in Logger.

        """
        # if dname == None:
        #     dname = self._devicename
        # return PersistentVariable(self.logger, parname, fallback, dname)
        
        # Create 'private' parameter with _ in front: self._name
        if self.logger.isPersistentVariable(name, dname):
            fallback = self.logger.loadPersistentVariable(name, None, dname)
        
        setattr(self.__class__, '_'+name, fallback)

        # This intermediate function handles the strange double self arguments
        def setter(self, name, dname, selfself, value):
            self._setPersistentAttribute(name, value, dname)

        # Make sure, that the parameters are "the values, which would be represented at this point with print(...)"
        setpart = partial(setter, self, name, dname)
        getpart = partial(getattr, self, '_'+name)

        # Create an attribute with the actual name. The getter refers to it's self._name attribute. The setter function to self._setGroupAttribute(name, value, parameter)
        setattr(self.__class__, name, property(getpart, setpart))
        
        # If contains docs, create a third attribute at self.__doc_PARNAME__
        if docs != None:
            setattr(self, '__doc_'+name+'__', docs)
    
    def _setPersistentAttribute(self, name, value, dname):
        setattr(self.__class__, '_'+name, value)
        self.logger.savePersistentVariable(name, value, dname)


    def initPersistentVariable(self, parname, value=None, dname=None):
        if dname == None:
            dname = self._devicename
        return self.logger.initPersistentVariable(parname, value, dname)

    def loadPersistentVariable(self, parname, fallback=None, dname=None):
        """
        Loads a persistent variable, which can be edited and will be restored after restart/reboot.

        Args:
            parname (str): Name of the parameter,
            fallback (any): Alternative value, if parname is not available (for initialization),
            dname (str): Devicename, selected by default

        Returns:
            any: Parameter-value

        """
        if dname == None:
            dname = self._devicename
        return self.logger.loadPersistentVariable(parname, fallback, dname)

    def savePersistentVariable(self, parname, value, dname=None):
        """
        Saves a persistent variable to a file in RTOC-directory.

        Args:
            parname (str): Name of the parameter,
            fallback (any): Alternative value, if parname is not available (for initialization),
            dname (str): Devicename, selected by default

        Returns:
            bool: True, if variable successfully saved.

        """
        if dname == None:
            dname = self._devicename
        return self.logger.savePersistentVariable(parname, value, dname)
        

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
            self._oldPerpetualTimer = True
        else:
            self._oldPerpetualTimer = False

        if samplerate is None and interval is None:
            samplerate = self.samplerate
        elif samplerate is None:
            samplerate = 1/interval

        if not self._oldPerpetualTimer:
            try:
                self._samplerate = samplerate
                self._pluginThread = _perpetualTimer(fun, samplerate, self.lockPerpetialTimer)
                return True
            except Exception:
                self._pluginThread = None
                return False
        else:
            try:
                self._samplerate = samplerate
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
            if not self._oldPerpetualTimer:
                self._pluginThread.cancel()
            self.run = False
            return True
        else:
            self.run = False
            return False

    def __updateT(self, func):
        diff = 0
        while self.run:
            if diff < 1/self._samplerate:
                time.sleep(1/self._samplerate-diff)
            start_time = time.time()
            func()
            diff = (time.time() - start_time)

    def telegram_send_message(self, text, priority=0, permission='write'):
        """
        Sends a message to all clients with given permission and higher permission.

        Args:
            text (str): Text to be send to the clients.
            priority (int): Priority to decide, which allow each client to disable notifications (0: Information, 1: Warning, 2: Error)
            permission (str): Choose user-permission (blocked, read, write, admin)
        """
        if self._bot is not None:
            self._bot.send_message_to_all(self._devicename+': '+str(text), priority, permission)
        else:
            logging.warning('TelegramBot is not enabled or wrong configured! Can not send message "{}"'.format(text))

    def telegram_send_photo(self, path, priority=0, permission='write'):
        """
        Sends the picture at a given path to all clients with given permission and higher permission.

        Args:
            path (str): Path to the picture to send.
            priority (int): Priority to decide, which allow each client to disable notifications (0: Information, 1: Warning, 2: Error)
            permission (str): Choose user-permission (blocked, read, write, admin)
        """
        if self._bot is not None:
            self._bot.send_photo(path, priority, permission)
        else:
            logging.warning('TelegramBot is not enabled or wrong configured! Can not send photo "{}"'.format(path))

    def telegram_send_document(self, path, priority=0, permission='write'):
        """
        Sends any document at a given path to all clients with given permission and higher permission.

        Args:
            path (str): Path to the file to send.
            priority (int): Priority to decide, which allow each client to disable notifications (0: Information, 1: Warning, 2: Error)
            permission (str): Choose user-permission (blocked, read, write, admin)
        """
        if self._bot is not None:
            self._bot.send_document(path, priority, permission)
        else:
            logging.warning('TelegramBot is not enabled or wrong configured! Can not send file "{}"'.format(path))

    def telegram_send_plot(self, signals={}, title='', text='', events=[], dpi=300, priority=0, permission='write'):
        """
        Sends any document at a given path to all clients with given permission and higher permission.

        Args:
            signals (dict): Contains multiple sets of x-y data, e.g. ``{'signal1':[1,2,3,4,5],[4,3,6,5,7]}``
            title (str): The title displayed above the graph.
            text (str): The plot-description text
            events (list): A list containing pseudo-events (text+vertical-line), e.g. ``[[10, 'Hello world at x=10']]``
            dpi (int): Resolution of plot.
            priority (int): Priority to decide, which allow each client to disable notifications (0: Information, 1: Warning, 2: Error)
            permission (str): Choose user-permission (blocked, read, write, admin)
        """
        if self._bot is not None:
            self._bot.send_plot(signals, title, text, events, dpi, priority, permission)
        else:
            logging.warning('TelegramBot is not enabled or wrong configured! Can not send plot')

class PersistentVariable(object):
    def __init__(self, logger, parname, fallback, dname):
        self._default = fallback
        self._value = fallback
        self._dname = dname
        self._parname = parname
        self._logger = logger
        self.loadValue()

    def loadValue(self):
        self._value = self._logger.loadPersistentVariable(self._parname, self._default, self._dname)
        return self._value

    def saveValue(self):
        return self._logger.savePersistentVariable(self._parname, self._value, self._dname)

    def resetValue(self):
        self._value = self._default

    @property
    def dname(self): 
        return self._dname 

    @dname.setter
    def dname(self, dname):
        self._dname = dname

    @property
    def value(self): 
        return self._value 

    @value.setter
    def value(self, value):
        self._value = value
        self.saveValue()


class _perpetualTimer():

    def __init__(self, hFunction, samplerate=1, lock=None):
        # self.thread_counter = 0
        self._samplerate = samplerate
        self._lock = lock
        self._cancel = True
        self._hFunction = hFunction
        self._thread = None
        self._correction = -0.006
        self._lastStart = 0

    def _handle_function(self):
        start = time.time()
        self._lastStart = time.perf_counter()

        if not self._cancel:
            with self._lock:
                self._hFunction()
                diff = time.time() - start  # self._lastStart  # - start
                diff2 = time.perf_counter()-self._lastStart
                timedelta = 1/self._samplerate - diff2
                timedelta = timedelta + self._correction
                if timedelta < 0:
                    timedelta = 0
        if not self._cancel and not self._lock.locked():
            # with self._lock:
            self._thread = Timer(timedelta, self._handle_function)
            # self.thread_counter += 1
            self._thread.start()

    def setSamplerate(self, rate):
        if rate != self._samplerate and not self._cancel:
            self._samplerate = rate
            # self.start(1/self._samplerate)
            if not self._lock.locked():
                self.start(0)
            # else:
            #     print('Samplerate changed, but not restarted')

    def getSamplerate(self):
        return self._samplerate

    def start(self, delayed=0):
        logging.info('Starting perpetual timer')
        self.cancel()
        self._cancel = False
        with self._lock:
            #if self.thread_counter <= 0:
            if self._thread is None:
                self._thread = Timer(delayed, self._handle_function)
                #self.thread_counter += 1
                self._thread.start()
                # if self.thread_counter<0:
                #     logging.warning('Something is not right...')
            else:
                logging.warning('You cannot start a second perpetual timer.')
                # print(self.thread_counter)


    def cancel(self):
        self._cancel = True
        if self._thread is not None:
            with self._lock:
                self._thread.cancel()
                # self.thread_counter -= 1
                self._thread = None
