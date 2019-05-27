#!/usr/local/bin/python3
# coding: utf-8
import os
import time
import json
import sys
import traceback
import collections

try:
    from PyQt5.QtCore import QCoreApplication
    translate = QCoreApplication.translate
except ImportError:
    def translate(id, text):
        return text

from .ScriptFunctions import ScriptFunctions
from .NetworkFunctions import NetworkFunctions
from .DeviceFunctions import DeviceFunctions
from .EventActionFunctions import EventActionFunctions
from .RT_data import RT_data

from ..LoggerPlugin import LoggerPlugin
from . import RTRemote

import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

try:
    from .telegramBot import telegramBot
except ImportError:
    logging.warning(
        'Telegram for python not installed. Please install with "pip3 install python-telegram-bot"')
    telegramBot = None
    # logging.warning(traceback.format_exc())

defaultconfig = {
    "global": {
        "language": "en",
        "recordLength": 500000,
        "name": "RTOC-Remote",
        "documentfolder": "~/.RTOC",
        "webserver_port": 8050,
        "globalActionsActivated": False,
        "globalEventsActivated": False
    },
    "postgresql": {
        "active": False,
        "user": "postgres",
        "password": "",
        "host": "127.0.0.1",
        "port": "5432",
        "database": "postgres",
        "onlyPush": True,
    },
    "GUI": {
        "darkmode": True,  # nicht richtig implementiert
        "scriptWidget": True,
        "deviceWidget": True,
        "deviceRAWWidget": True,
        "pluginsWidget": False,
        "eventWidget": True,
        "restoreWidgetPosition": False,
        "newSignalSymbols": True,
        "plotLabelsEnabled": True,
        "plotGridEnabled": True,
        "showEvents": True,
        "grid": [
            True,
            True,
            1.0
        ],
        "plotLegendEnabled": False,
        "blinkingIdentifier": False,
        "plotRate": 8,
        "plotInverted": False,
        "xTimeBase": True,
        "timeAxis": True,
        "systemTray": False,
        "signalInactivityTimeout": 2,
        "autoShowGraph": False,
        "antiAliasing": True,
        "openGL": True,
        "useWeave": True,
        "csv_profiles": {},
    },
    "telegram": {
        "active": False,
        "token": "",
        "eventlevel": 0,
        "chat_ids": {},
        "inlineMenu": False
    },
    "tcp": {
        "active": False,
        "port": 5050,
        "password": '',
        "knownHosts": {},
        "remoteRefreshRate": 1,
    },
    "backup": {
        "active": False,
        "path": '~/.RTOC/backup',
        "clear": False,
        "autoIfFull": True,
        "autoOnClose": True,
        "loadOnOpen": True,
        "intervall": 240,
    },
}


class _Config(collections.MutableMapping, dict):
    # def __init__(self, default):
    #     for key in default.keys():
    #         value = default[key]
    #         dict.__setitem__(self,key,value)
    def __getitem__(self, key):
        return dict.__getitem__(self, key)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        with open(self['documentfolder']+"/config.json", 'w', encoding="utf-8") as fp:
            json.dump(self, fp,  sort_keys=False, indent=4, separators=(',', ': '))
        logging.info('Config saved')

    def __delitem__(self, key):
        dict.__delitem__(self, key)

    def __iter__(self):
        return dict.__iter__(self)

    def __len__(self):
        return dict.__len__(self)

    def __contains__(self, x):
        return dict.__contains__(self, x)


# , QObject):
class RTLogger(DeviceFunctions, EventActionFunctions, ScriptFunctions, NetworkFunctions):
    """
    This is the main backend-class.

    It combines data-storage, tcp-server, scripting, event/action-system and the telegram-bot.

    Check out the following modules for more information:
        DeviceFunctions
        EventActionFunctions
        NetworkFunctions
        ScriptFunctions
        RTRemote
        RT_data
        telegramBot
    """
    def __init__(self, enableTCP=None, tcpport=None, isGUI=False, forceLocal=False):
        self.run = True
        self.forceLocal = forceLocal
        self.isGUI = isGUI
        self.__config = _Config({})
        self._load_config()
        self.pluginObjects = {}  # dict with all plugins
        self.pluginFunctions = {}
        self.pluginParameters = {}
        self.pluginStatus = {}
        self.starttime = time.time()
        # self.maxLength = self.config['global']['recordLength']
        self.__latestSignal = []
        self.devicenames = {}
        self.triggerExpressions = []
        self.triggerValues = []
        self.telegramBot = None
        self.globalEvents = {}
        self.activeGlobalEvents = {}
        self.globalActions = {}
        self.getDeviceList()
        self.tcp = None
        if enableTCP is not None:
            self.config['tcp']['active'] = enableTCP
        if tcpport is not None:
            self.config['tcp']['port'] = int(tcpport)

        # self.clearSignals()
        self.callback = None
        self.newSignalCallback = None
        self.scriptExecutedCallback = None
        self.handleScriptCallback = None
        self.clearCallback = None
        self.newEventCallback = None
        self.startDeviceCallback = None
        self.stopDeviceCallback = None
        self.recordingLengthChangedCallback = None
        self.reloadDevicesCallback = None
        self.reloadDevicesRAWCallback = None
        self.reloadSignalsGUICallback = None
        self.executedCallback = None

        self.tcpclient = LoggerPlugin(None, None, None)
        self.rtoc_web = None
        self.__tcpserver = None
        self.database = RT_data(self)

        self.toggleTcpServer(self.config['tcp']['active'])
        self.remote = RTRemote.RTRemote(self)
        # if telegramBot is not None:
        #     self.telegramBot = telegramBot(self)
        self.toggleTelegramBot(self.config['telegram']['active'])
        self._load_autorun_plugins()
        # self.check_for_updates()


        self.loadGlobalActions()
        self.loadGlobalEvents()

        # if self.config['backup']['active'] and not self.forceLocal:  # or self.config['postgresql']['active']:
        #     self.database.start()

    def getDir(self, dir=None):
        """
        Returns directory of this module
        """
        if dir is None:
            dir = __file__
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(dir))

        return packagedir

    def getThread(self):
        """
        Returns the :mod:`threading.Thread` object of :meth:`._tcpListener`
        """
        return self.__tcpserver

    def stop(self):
        """
        Stops everything (TCP-Server, Telegram-Bot, Plugins)
        """
        # Stops all plugins
        self.run = False
        self.tcpRunning = False
        if self.tcp:
            self.tcp.close()
        logging.info("TCPServer beendet")
        self.remote.stop()

        for name in self.devicenames.keys():
            self.stopPlugin(name)

        self.database.close()

        self.save_config()
        self.saveGlobalActions()
        self.saveGlobalEvents()
        if self.telegramBot:
            self.telegramBot.stop()

# Signal functions ############################################################

    def clearCB(self, database=False):
        """
        GUI-callback to clear data.
        """
        if self.clearCallback:
            self.clearCallback()

        self.clear(database)
        # time.sleep(1)

    def clear(self, database=False):
        """
        Clear all data from local (and database)
        """
        self.selectedTriggerSignals = []
        self.database.clear( dev=True, sig=True, ev=True, database=database)

# Other functions #########################################################

    def exportData(self, filename=None, filetype="json", scripts=None, overwrite=False):
        """
        Export all local data to file

        Args:
            filename (str)
            filetype ('xlsx','json','csv')
            scripts (list): List of scripts to be saved
            overwrite (bool): If True, existing file will be overwritten
        """
        if filename is None:
            filename = self._generateFilename()
        if filetype == "xlsx":
            self.database.exportXLSX(filename)
        elif filetype == "json":
            self.database.exportJSON(filename, scripts, overwrite)
        else:
            self.database.exportCSV(filename)

    def _generateFilename(self):
        minx = []
        # maxx = []
        for signal in self.database.signals():
            minx.append(min(list(signal[2])))
        minx = max(minx)
        now = time.strftime("%d_%m_%y_%H_%M", time.localtime(minx))
        return self.config['global']['documentfolder']+"/"+str(now)

    @property
    def config(self):
        """
        Global configuration dict
        """
        return self.__config

    @config.setter
    def config(self, config):
        self.__config = config
        logging.info('Config changed and saved!')
        self.save_config()

    def _load_config(self):
        # self.lastEditedList = []

        userpath = os.path.expanduser('~/.RTOC')
        if not os.path.exists(userpath):
            os.mkdir(userpath)
        if not os.path.exists(userpath+'/backup'):
            os.mkdir(userpath+'/backup')
        if os.path.exists(userpath+"/config.json"):
            try:
                with open(userpath+"/config.json", encoding="UTF-8") as jsonfile:
                    self.__config = _Config(json.load(jsonfile, encoding="UTF-8"))
                # newlist = []
                # self.config['global']['documentfolder'] = userpath
                # for path in self.__config["lastSessions"]:
                #     if os.path.exists(path):
                #         newlist.append(path)
                # self.__config["lastSessions"] = newlist
                # for lastpath in self.__config["lastSessions"]:
                #     self.lastEditedList.append(lastpath)
                for key in defaultconfig.keys():
                    if key not in self.__config.keys():
                        self.__config[key] = defaultconfig[key]
                    elif type(defaultconfig[key])==dict:
                        for key2 in defaultconfig[key].keys():
                            if key2 not in self.__config[key].keys():
                                self.__config[key][key2] = defaultconfig[key][key2]

            except Exception:
                logging.debug(traceback.format_exc())
                logging.error('Error loading config.json')
                self.__config = _Config(defaultconfig)
        else:
            logging.warning('No config-file found.')
            self.__config = _Config(defaultconfig)
            self.__config['backup']['path'] = userpath+'/backup'

        self.__config['global']['documentfolder'] = userpath

        if type(self.__config['telegram']['chat_ids']) == list:
            newdict = {}
            for id in self.__config['telegram']['chat_ids']:
                newdict[id] = self.__config['telegram']['eventlevel']
            self.__config['telegram']['chat_ids'] = newdict
            logging.warning('Telegram chat ids were saved as list, changed to dict.')
        elif type(self.__config['telegram']['chat_ids']) == dict:
            for id in self.__config['telegram']['chat_ids'].keys():
                if type(self.__config['telegram']['chat_ids'][id]) == int:
                    self.__config['telegram']['chat_ids'][id] = [
                        self.__config['telegram']['chat_ids'][id], [[], []]]
                    logging.warning(
                        'Telegram chat ids were saved without shortcuts. Empty list added')
                elif len(self.__config['telegram']['chat_ids'][id]) != 2:
                    self.__config['telegram']['chat_ids'][id] = [
                        self.__config['telegram']['eventlevel'], [[], []]]
                    logging.warning('Telegram chat ids had strange format. Has been resetted.')

        if type(self.__config['tcp']['knownHosts']) == list:
            newdict = {}
            for id in self.__config['tcp']['knownHosts']:
                newdict[id] = ['RenameDevice', '']
            self.__config['tcp']['knownHosts'] = newdict
        # conf = dict(self.config)
        # conf['telegram_bot'] = False
        # conf['rtoc_web'] = False
        # with open(self.config['global']['documentfolder']+"/config.json", 'w', encoding="utf-8") as fp:
        #     json.dump(conf, fp,  sort_keys=False, indent=4, separators=(',', ': '))

    def clearCache(self):
        self.__config = _Config(defaultconfig)
        # self.save_config()
        filename = self.config['global']['documentfolder']+"/plotStyles.json"
        if os.path.exists(filename):
            os.remove(filename)

    def save_config(self):
        """
        DEPRECATED. Saves config to file.
        """
        # self.config['GUI']['deviceWidget'] = True
        # self.config['GUI']['pluginsWidget'] = False
        with open(self.config['global']['documentfolder']+"/config.json", 'w', encoding="utf-8") as fp:
            json.dump(self.config, fp,  sort_keys=False, indent=4, separators=(',', ': '))

    def _load_autorun_plugins(self):
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
            except Exception:
                logging.debug(traceback.format_exc())
                logging.error('error in '+userpath)
            for p in plugins:
                self.startPlugin(p)

    def check_for_updates(self):
        """
        Checks for updates from pypi.

        Returns:
            str: Current installed version

            str: Newest available version
        """
        import xmlrpc.client
        try:
            from pip._internal.utils.misc import get_installed_distributions
        except (ImportError, SystemError):  # pip<10
            from pip import get_installed_distributions

        pypi = xmlrpc.client.ServerProxy('http://pypi.python.org/pypi')
        available = pypi.package_releases('RTOC')

        current = None
        for pack in get_installed_distributions():
            if pack.project_name == 'RTOC':
                current = pack.version
                break
        if current is not None:
            logging.info('\nInstalled version: '+str(current))
        else:
            logging.info(
                'RTOC was not installed with PyPi. To enable version-checking, please install it with "pip3 install RTOC"')
        if not available:
            logging.info(
                "Sorry. Couldn't get version information from PyPi. Please visit 'https://pypi.org/project/RTOC/'")
        else:
            logging.info('Newest version: '+str(available[0]))

        if current is not None and available:
            if current == available[0]:
                logging.info('RTOC is up to date.')
            else:
                logging.info('New version available! Please update\n\npip3 install RTOC --upgrade\n')
        return current, available





# if __name__ == "__main__":
#     kl = RTLogger()
#     time.sleep(1)
#     kl.stop()
