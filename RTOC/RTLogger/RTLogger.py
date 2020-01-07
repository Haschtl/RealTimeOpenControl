#!/usr/local/bin/python3
# coding: utf-8
import os
import time
import json
import sys
import traceback
import collections


from .ScriptFunctions import ScriptFunctions
from .NetworkFunctions import NetworkFunctions
from .DeviceFunctions import DeviceFunctions
from .EventActionFunctions import EventActionFunctions
from .RT_data import RT_data
from .RTWebsocketServer import RTWebsocketServer

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
        "xRelative": True,
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
        "default_eventlevel": 0,
        "default_permission": 'blocked', # or 'read' or 'write' or 'admin'
        # "chat_ids": {},
        "inlineMenu": False,
        "onlyAdmin": False
    },
    "tcp": {
        "active": False,
        "port": 5050,
        "password": '',
    },
    "websocket": {
        "active": False,
        "port": 5050,
        "password": None,
        "ssl": False,
        "keyfile": "",
        "certfile": "",
        "knownHosts": {},
        "host_whitelist": ['127.0.0.1', 'localhost'],
    },
    "backup": {
        "active": False,
        "path": '~/.RTOC/backup',
        "clear": False,
        "autoIfFull": True,
        "autoOnClose": True,
        "loadOnOpen": True,
        "intervall": 240,
        "resample": 0,
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
        try:
            with open(self['global']['documentfolder']+"/config.json", 'w', encoding="utf-8") as fp:
                json.dump(self, fp,  sort_keys=False, indent=4, separators=(',', ': '))
                logging.info('Config saved')
        except Exception as e:
            logging.error(e)
            logging.warning('Config could not be saved')

    def __delitem__(self, key):
        dict.__delitem__(self, key)

    def __iter__(self):
        return dict.__iter__(self)

    def __len__(self):
        return dict.__len__(self)

    def __contains__(self, x):
        return dict.__contains__(self, x)

    def deepcopy(self):
        copy = {}
        for outerkey in self.keys():
            if type(self[outerkey]) == dict:
                copy[outerkey] = {}
                for innerkey in self[outerkey].keys():
                    if type(self[outerkey][innerkey]) == dict:
                        copy[outerkey][innerkey] = {}
                        for innerinnerkey in self[outerkey][innerkey].keys():
                            copy[outerkey][innerkey][innerinnerkey] = self[outerkey][innerkey][innerinnerkey]
                    else:
                        copy[outerkey][innerkey] = self[outerkey][innerkey]
            else:
                copy[outerkey] = self[outerkey]
        return copy

    def reduced(self):
        reduced_config = self.deepcopy()
        reduced_config['postgresql'].pop('user')
        reduced_config['postgresql'].pop('password')
        reduced_config['postgresql'].pop('host')
        reduced_config['postgresql'].pop('port')
        reduced_config['postgresql'].pop('database')
        reduced_config.pop('GUI')
        reduced_config['telegram'].pop('token')
        reduced_config['tcp'].pop('password')
        reduced_config['websocket'].pop('password')
        return reduced_config


# , QObject):
class RTLogger(DeviceFunctions, EventActionFunctions, ScriptFunctions, NetworkFunctions):
    """
    This is the main backend-class.

    It combines data-storage, websocket-server, scripting, event/action-system and the telegram-bot.

    Check out the following modules for more information:
        DeviceFunctions
        EventActionFunctions
        NetworkFunctions
        ScriptFunctions
        RTRemote
        RT_data
        telegramBot
    """
    def __init__(self, enableWebsocket=None, websocketPort=None, isGUI=False, forceLocal=False, customConfigPath=None):
        self.run = True
        self.forceLocal = forceLocal
        self.isGUI = isGUI
        self.__config = _Config({})
        self._load_config(customConfigPath)
        self.pluginObjects = {}  # dict with all plugins
        self.pluginFunctions = {}
        self.pluginParameters = {}
        self.pluginParameterDocstrings = {}
        self.pluginInfos = {}
        self.pluginStatus = {}
        self.persistentVariables = {}
        self.autorunPlugins = []
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
        if websocketPort is not None and type(websocketPort) in [int, float]:
            self.config['websocket']['port'] = int(websocketPort)
        if enableWebsocket is not None and type(enableWebsocket == bool):
            self.config['websocket']['active'] = enableWebsocket

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
        self.websocketDevice_callback = None 
        self.loadSystemActions()
        # self.tcpclient = LoggerPlugin(None, None, None)
        self.__tcpserver = None
        self.database = RT_data(self)
        self.initPersistentVariables()
        self.toggleTcpServer(self.config['tcp']['active'])
        if self.config['websocket']['active']:
            self.websocket = RTWebsocketServer(self, port=self.config['websocket']['port'],  password=self.config['websocket']['password'])
        else:
            logging.info('Websocket server disabled')
            self.websocket = None
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

    def loadSystemActions(self):
        self.userActions = {}
        userpath = self.config['global']['documentfolder']
        if os.path.exists(userpath+"/telegramActions.json"):
            try:
                with open(userpath+"/telegramActions.json", encoding="UTF-8") as jsonfile:
                    self.userActions = json.load(jsonfile, encoding="UTF-8")
            except:
                # print(traceback.print_exc())
                logging.error('Error in Telegram-UserActions-JSON-File')

    def executeUserAction(self, strung):
        if strung in self.userActions.keys():
            action = self.userActions[strung]
            return self.executeScript(action)
        else:
            return False, 'Cannot find action "'+strung+'"'

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
        Stops everything (Websocket-Server, Telegram-Bot, Plugins)
        """
        # Stops all plugins
        self.run = False
        self.tcpRunning = False
        if self.tcp:
            self.tcp.close()
            logging.info("TCP-Server beendet")
        if self.websocket:
            self.websocket.stop()
            logging.info("WebsocketServer beendet")
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

    def exportData(self, filename=None, filetype="json", overwrite=False):
        """
        Export all local data to file

        Args:
            filename (str)
            filetype ('xlsx','json','csv')
            overwrite (bool): If True, existing file will be overwritten
        """
        if filename is None:
            filename = self._generateFilename()
        if filetype == "xlsx":
            self.database.exportXLSX(filename)
        elif filetype == "json":
            self.database.exportJSON(filename, overwrite)
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

    def _load_config(self, customPath=None):
        # self.lastEditedList = []
        if customPath is None:
            userpath = os.path.expanduser('~/.RTOC')
            if not os.path.exists(userpath):
                os.mkdir(userpath)
            if not os.path.exists(userpath+'/backup'):
                os.mkdir(userpath+'/backup')
            configpath = userpath+"/config.json"
        else:
            userpath = os.path.expanduser(customPath)
            if not os.path.exists(userpath):
                os.mkdir(userpath)
            if not os.path.exists(userpath+'/backup'):
                os.mkdir(userpath+'/backup')
            configpath = userpath+"/config.json"

        if os.path.exists(configpath):
            try:
                with open(configpath, encoding="UTF-8") as jsonfile:
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

            except Exception as error:
                logging.debug(traceback.format_exc())
                logging.error('Error loading config.json\n{}'.format(error))
                self.__config = _Config(defaultconfig)
        else:
            logging.warning('No config-file found.')
            self.__config = _Config(defaultconfig)
            self.__config['backup']['path'] = userpath+'/backup'
            self.__config['global']['documentfolder'] = userpath
            if not os.path.exists(configpath):

                with open(configpath, 'w+', encoding="utf-8") as fp:
                    json.dump(self.__config, fp,  sort_keys=False, indent=4, separators=(',', ': '))
            # self.save_config()

        self.__config['global']['documentfolder'] = userpath

        if 'chat_ids' in self.__config.keys():
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

        if type(self.__config['websocket']['knownHosts']) == list:
            newdict = {}
            for id in self.__config['websocket']['knownHosts']:
                newdict[id] = ['RenameDevice', '']
            self.__config['websocket']['knownHosts'] = newdict
        # conf = dict(self.config)
        # conf['telegram_bot'] = False
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
        userpath = os.path.expanduser(self.config['global']['documentfolder']+'/autorun_devices')
        if not os.path.exists(userpath):
            with open(userpath, 'w', encoding="UTF-8") as f:
                f.write('')
        else:
            plugins = self.getAutorunPlugins()
            for p in plugins:
                self.startPlugin(p)

    def setAutorunPlugins(self, plugins):
        userpath = os.path.expanduser(self.config['global']['documentfolder']+'/autorun_devices')

        with open(userpath, 'w', encoding="UTF-8") as f:
            for p in plugins:
                f.write(p+'\n')
        self.autorunPlugins = plugins

    def addAutorunPlugin(self, plugin):
        plugins = self.getAutorunPlugins()
        if plugin not in plugins:
            plugins.append(plugin)
            self.autorunPlugins = plugins
            self.setAutorunPlugins(plugins)
            if self.websocketDevice_callback:
                self.websocketDevice_callback(plugin)
            return True
        else:
            return False
    
    def removeAutorunPlugin(self, plugin):
        plugins = self.getAutorunPlugins()
        if plugin in plugins:
            plugins.pop(plugins.index(plugin))
            self.autorunPlugins = plugins
            self.setAutorunPlugins(plugins)
            if self.websocketDevice_callback:
                self.websocketDevice_callback(plugin)
            return False
        else:
            return True
    
    def getAutorunPlugins(self):
        userpath = os.path.expanduser(self.config['global']['documentfolder']+'/autorun_devices')
        if not os.path.exists(userpath):
            self.autorunPlugins = []
            return []
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
            self.autorunPlugins = plugins
            return plugins

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
