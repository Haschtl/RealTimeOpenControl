#!/usr/local/bin/python3
# coding: utf-8
import os
import traceback
import importlib
import sys

from . import loggerlib as loggerlib
from . import plugins
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

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


class DeviceFunctions:
    """
    This class contains all plugin-specific functions of RTLogger
    """

    def getDeviceList(self):
        self.devicenames = {}
        self.pluginStatus = {}
        logging.info("Default plugins:")
        for finder, name, ispkg in loggerlib.iter_namespace(plugins):
            namesplit = name.split('.')
            logging.info(namesplit[-1])
            devname = namesplit[-1].replace('.', 'Dot').replace(':', 'DDot')
            if devname not in ["LoggerPlugin"]:
                self.devicenames[devname] = name
                self.pluginStatus[devname] = False
        logging.info('User plugins:')
        # logging.info(loggerlib.list_submodules(devices))
        subfolders = [f.name for f in os.scandir(list(devices.__path__)[0]) if f.is_dir()]
        for folder in subfolders:
            if folder not in ['', '__pycache__', '.git']:
                a = __import__(devices.__name__+"." + folder)
                # for finder, name, ispkg in loggerlib.iter_namespace(devices):
                #fullpath = pkgutil.extend_path(list(devices.__path__)[0], folder)
                # logging.debug(fullpath)
                # for finder, name, ispkg in pkgutil.iter_modules(fullpath,devices.__name__+'.'+folder+ "."):
                # for root, dirs, files in os.walklevel(list(devices.__path__)[0], level=1):
                for files in os.listdir(list(devices.__path__)[0]+"/"+folder):
                    if files.endswith('.py'):
                        file = ''
                        with open(list(devices.__path__)[0]+"/"+folder+'/'+files, mode='r') as f:
                            file = f.readlines()
                        if 'class Plugin(' in ''.join(file):
                            name = devices.__name__+'.'+folder+"."+files.replace('.py', '')
                            logging.info(name)

                            devname = files.replace('.py', '').replace('.', 'Dot').replace(':', 'DDot')
                            if devname not in ["LoggerPlugin"]:
                                self.devicenames[devname] = name
                                self.pluginStatus[devname] = False

    # Plugin functions ############################################################

    def startPlugin(self, name, remote=True):
        '''
        This function starts a plugin.

        Args:
            name (str): This is the name of the plugin you want to start.
            remote (bool): If true, this function trigger a callback to update GUI

        Returns:
            bool: True, if sucessfully started

            error (str): Error message, if errors occured
        '''
        # Starts the specified plugin and connects callback if possible
        try:
            if name in self.devicenames.keys():
                fullname = self.devicenames[name]
                # if callback is None:
                self.pluginObjects[
                    name] = importlib.import_module(
                    fullname).Plugin(stream=self.database.addDataCallback, plot=self.database.plot, event=self.database.addNewEvent, telegramBot=self.telegramBot)
                # else:
                #     self.pluginObjects[name] = importlib.import_module(
                #         fullname).Plugin(callback, self.addNewEvent)
                self.analysePlugin(self.pluginObjects[name], name)
                self.pluginStatus[name] = True
                logging.info("PLUGIN: " + name+' connected\n')
                if self.startDeviceCallback and remote:
                    self.startDeviceCallback(name)
                return True, ""
            else:
                logging.warning("PLUGIN not found: '"+str(name)+"'\n")
                return False, "PLUGIN not found: '"+str(name)+"'\n"
        except Exception:
            tb = traceback.format_exc()
            self.pluginStatus[name] = tb
            logging.debug(tb)
            logging.warning("PLUGIN FAILURE\nCould not load Plugin '"+str(name)+"'\n")
            return False, tb

    def getPlugin(self, name):
        '''
        This function returns an object of the 'Plugin' class of given plugin-name.

        Args:
            name (str): This is the name of the plugin you want to get.

        Returns:
            bool: False, if the object did not exist

            object: Object of plugin-class of given plugin
        '''
        try:
            if name in self.pluginObjects.keys():
                return self.pluginObjects[name]
            else:
                logging.warning("Plugin "+name+" not found or started")
                return False
        except Exception:
            tb = traceback.format_exc()
            logging.debug(tb)
            logging.warning("PLUGIN FAILURE\nCould not get Plugin '"+str(name)+"'\n")
            return False

    def setPluginSamplerate(self, name, samplerate):
        '''
        Sets the samplerate of a given plugin. This will ONLY work, if the plugin uses the integrated PerpetualTimer.

        Args:
            name (str): This is the name of the plugin you want to start.
            samplerate (float): The desired samplerate in Hz.

        Returns:
            bool: True, if sucessfully set
        '''
        if name in self.pluginObjects.keys():
            try:
                self.pluginObjects[name].samplerate = samplerate
                return True
            except Exception:
                tb = traceback.format_exc()
                logging.debug(tb)
                return False
        else:
            return False

    def setAllSamplerates(self, samplerate):
        '''
        Sets the samplerate of a all plugin. This will ONLY work, if the plugins use the integrated PerpetualTimer.

        Args:
            samplerate (float): The desired samplerate in Hz.
        '''
        for plugin in self.pluginObjects.keys():
            self.setPluginSamplerate(plugin, samplerate)

    def getPluginSamplerate(self, name):
        '''
        Returns the samplerate of a given plugin.

        Args:
            name (str): This is the name of the plugin.

        Returns:
            samplerate (float): The actual samplerate in Hz.
        '''
        if name in self.pluginObjects.keys():
            try:
                return self.pluginObjects[name].samplerate
            except Exception:
                tb = traceback.format_exc()
                logging.debug(tb)
                return 0
        else:
            return 0

    def getPluginParameter(self, name, parameter, *args):
        '''
        This function is used to get and also set parameters from a given plugin.

        You can **get** multiple parameters at once. To get a parameter, use the following parameter mapping:

        Args:
            name (str): This is the name of the plugin.
            parameter (str): If == 'get', this call is understood as a get-request
            args (\*str): Can be multiple names of plugin-parameters


        You can **set** a single parameter. To set a parameter, use the following parameter mapping:

        Args:
            name (str): This is the name of the plugin.
            parameter (str): The parameter-name you want to change.
            args (any): Desired value of the parameter.

        Returns:
            parameter (any): The value of the requested/setted parameter(s).

            False, if any error occured, while trying to get/set parameter
        '''
        try:
            if parameter == "get" and type(parameter) == str:
                if type(args[0]) == list:
                    rets = []
                    for param in args[0]:
                        exec('self.ret=self.pluginObjects[name].'+str(param))
                        rets.append(self.ret)
                    self.ret = rets
                    return self.ret
                elif type(args[0]) == str:
                    exec('self.ret=self.pluginObjects[name].'+str(args[0]))
                    return self.ret
            elif name in self.pluginObjects.keys():
                if type(args[0]) == str:
                    strung = "'"+args[0]+"'"
                else:
                    strung = str(args[0])
                exec('self.pluginObjects["' +
                     name+'"].'+parameter+" = " + strung)
                self.ret = args[0]
                return self.ret
            else:
                logging.warning("Plugin "+name+" not found or started")
                return False
        except Exception:
            tb = traceback.format_exc()
            logging.error(tb)
            logging.warning(
                "PLUGIN FAILURE\nCould not get/set/call Plugin parameter/function'"+str(name)+"'\n")
            return False

    def callPluginFunction(self, name, function, *args, **kwargs):
        '''
        This function is used to call a function from a given plugin.

        You can **get** multiple parameters at once. To get a parameter, use the following parameter mapping:

        Args:
            name (str): This is the name of the plugin.
            function (str): The function-name, you want to call
            args (\*any): Parameters transmitted to the function
            kwargs (\*any): Keyworded parameters transmitted to the function

        Returns:
            bool: True, if call was successfull

            parameter (any): The value of the requested/setted parameter(s).
        '''
        try:
            if name in self.pluginObjects.keys() and type(function) == str:
                logging.debug(function)
                logging.debug(name)
                # logging.debug(*args)
                # logging.debug(*kwargs)
                exec('self.func = self.pluginObjects["' +
                     name+'"].'+function)

                ans = self.func(*args, **kwargs)
                return True, ans
            else:
                logging.warning("Plugin "+name+" not found or started")
                return False, "Plugin "+name+" not found or started"
        except Exception:
            tb = traceback.format_exc()
            logging.error(tb)
            logging.warning(
                "PLUGIN FAILURE\nCould not get/set/call Plugin parameter/function'"+str(name)+"'\n")
            return False, tb

    def stopPlugin(self, name, remote=True):
        '''
        This function stops a plugin.

        Args:
            name (str): This is the name of the plugin you want to stop.
            remote (bool): If true, this function trigger a callback to update GUI

        Returns:
            bool: True, if sucessfully stopped
        '''
        # Stops the specified plugin
        try:
            if name in self.pluginObjects.keys():
                #self.pluginObjects[name].run = False
                self.pluginStatus[name] = False
                self.pluginObjects[name].close()
                logging.info("PLUGIN: " + name+' disconnected\n')
            # else:
            #    logging.debug("Plugin "+name+" not loaded")
            if self.stopDeviceCallback and remote:
                self.stopDeviceCallback(name)
            return True
        except Exception:
            tb = traceback.format_exc()
            logging.info(tb)
            logging.warning("PLUGIN FAILURE\nCould not stop Plugin '"+str(name)+"'\n")
            return False

    def analysePlugin(self, object, name):
        '''
        Collects all necessary information about a specific plugin (function names and parameter names) and stores them in parameter 'pluginFunctions' and 'pluginParameters'

        '''
        # Adds public Plugin-functions and parameters to local attributes pluginFunctions and pluginParameters
        all = dir(object)
        for element in all:
            if str(element)[0] != "_":
                if callable(getattr(object, element)):
                    origFunName = "self.pluginObjects[" + name+"']."+getattr(object, element).__name__
                    argCount = getattr(object, element).__code__.co_argcount-1
                    varnames = getattr(object, element).__code__.co_varnames
                    argNames = varnames[1:argCount+1]
                    self.pluginFunctions[name+"."+element] = [origFunName, argNames, argCount, varnames]
                else:
                    origParName = "self.pluginObjects['"+name+"']."+str(element)

                    self.pluginParameters[name+"." +element] = origParName

        # print(self.pluginFunctions)
