import traceback
import time

from .importCode import importCode
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)


class ScriptFunctions:
    """
    This class contains all script-execution-specific functions of RTLogger
    """

    def generateCode(self, s, condition=False):
        s = self.replacePluginParameters(s)
        s = self.replacePluginMethods(s)
        s = self.replaceSignalNames(s)
        s = self.replaceLoggerFunctions(s)
        s = self.replaceTelegramFunctions(s)
        s, init = self.replaceGlobalVariables(s)
        s = s.replace('global.', 'self.')
        s = self.replaceLibraryFunctions(s)
        if condition:
            s = self.createConditionFunction(s)
        else:
            s = self.generateTriggerCode(s)
            s = self.printfunction() + s
            s = self.createFunction(s)
        s = "import math\nimport numpy as np\nimport sys\nimport os\nimport scipy as sp\ntry:\n\timport RTOC.RTLogger.scriptLibrary as rtoc\nexcept (ImportError,SystemError):\n\tfrom .RTLogger import scriptLibrary as rtoc\n\n" + init + "\n"+s
        return s

    def replacePluginParameters(self, s):
        for host in self.remote.devices.keys():
            for device in self.remote.devices[host].keys():
                for parameter in self.remote.devices[host][device]['parameters']:
                    #value = self.remote.getParam(self, host, device, parameter[0])
                    value = parameter[1]
                    s = s.replace(host+':'+device+'.'+parameter[0], str(value))

                    # self.remote.callFuncOrParam(self, host, device, parameter[], value)
        for parameter in self.pluginParameters.keys():
            s = s.replace(parameter, self.pluginParameters[parameter])
        return s

    def replacePluginMethods(self, s):
        for host in self.remote.devices.keys():
            for device in self.remote.devices[host].keys():
                for function in self.remote.devices[host][device]['functions']:
                    strung = "self.remote.callFuncOrParam2('" + \
                        host+"','"+device+"','"+function+"',None)"
                    s = s.replace(host+':'+device+'.'+function+"()", strung)
                    strung = "self.remote.callFuncOrParam2('"+host+"','"+device+"','"+function+"','"
                    s = s.replace(host+':'+device+'.'+function+"(", strung)
        for function in self.pluginFunctions.keys():
            s = s.replace(function, self.pluginFunctions[function][0])
        return s

    def replaceSignalNames(self, s):
        for name in self.database.signalNames():
            sigId = self.database.getSignalID(name[0], name[1])
            if sigId != -1:
                s = s.replace(
                    name[0]+"."+name[1]+".x", "np.array(self.database.signals()["+str(sigId)+"][2])")
                s = s.replace(
                    name[0]+"."+name[1]+".y", "np.array(self.database.signals()["+str(sigId)+"][3])")
                s = s.replace(
                    name[0]+"."+name[1]+".latest", "self.database.signals()["+str(sigId)+"][3][-1]")
                s = s.replace(
                    name[0]+"."+name[1], "np.array(self.database.signals()["+str(sigId)+"][2]), np.array(self.database.signals()["+str(sigId)+"][3])")
        return s

    def replaceLibraryFunctions(self, s):
        s = s.replace("rtoc.lsfit(", "rtoc.lsfit(self, ")
        s = s.replace("rtoc.resample(", "rtoc.resample(self, ")
        s = s.replace("rtoc.resampleFourier(", "rtoc.resampleFourier(self, ")
        s = s.replace("rtoc.combine(", "rtoc.combine(self, ")
        return s

    def replaceLoggerFunctions(self, s):
        s = s.replace("stream(", "self.database.addData(")

        s = s.replace("event(", "self.database.addNewEvent(")
        s = s.replace("plot(", "self.database.plot(")

        s = s.replace("print(", "prints += print(")

        s = s.replace("clearData()", "self.clearCB()")
        s = s.replace("exportData(", "self.exportData(")

        s = s.replace("while True:", "while self.run:")
        s = s.replace("sendWebsocket(", "self._sendWebsocket(")
        return s

    def replaceTelegramFunctions(self, s):
        s = s.replace("telegram.send_photo(", "self.telegramBot.send_photo(")

        s = s.replace("telegram.send_document(", "self.telegramBot.send_document(")
        s = s.replace("telegram.send_plot(", "self.telegramBot.send_plot(")

        s = s.replace("telegram.send_message_to_all(", "self.telegramBot.send_message_to_all(")
        return s

    def replaceGlobalVariables(self, s):
        globals = []
        for item in s.split("\n"):
            if item.startswith("global "):
                globals.append(item.strip())
        initdef = ""
        for idx, glob in enumerate(globals):
            s = s.replace(glob, "")
            globals[idx] = glob.replace("global ", "self.")

        initdef = "\n\t".join(globals)
        initdef = "def init(self):\n\t"+initdef+"\n\t"+"pass\n"
        # Replace trigger-events

        return s, initdef

    def printfunction(self):
        # Generate print function
        s = "prints = ''" + \
            "\ndef print(*args): \n\ttext = ''\n\tfor arg in args:\n\t\ttext += str(arg)\n\t\tsys.stdout.write(str(arg))\n\treturn text\n"
        return s

    def createFunction(self, s):
        s = "def test(self, clock):\n" + \
            "\n".join(["\t"+scriptline for scriptline in s.split("\n")]) + "\n\treturn prints\n"
        return s

    def createConditionFunction(self, s):
        s = "def test(self, clock):\n" + \
            "\n"+"\treturn "+s + "\n"
        return s

    def generateTriggerCode(self, scriptStr):
        triggered = False
        for item in scriptStr.split("\n"):
            if "trig " in item:
                line = item.strip()
                expression = line[5:-1]
                triggered = self.triggerExpressionHandler(expression)
                scriptStr = scriptStr.replace(
                    line, "if self.triggerExpressionHandler(\""+expression+"\"):")
        return scriptStr

    def triggerExpressionHandler(self, expression):
        try:
            boolean = importCode("def test(self):\n\tif "+expression +
                                 ":\n\t\treturn True\n\telse:\n\t\treturn False", "condition")
            result = boolean.test(self)
            if expression not in self.triggerExpressions:
                self.triggerExpressions.append(expression)
                self.triggerValues.append(result)
                return result
            else:
                idx = self.triggerExpressions.index(expression)
                if result == self.triggerValues[idx]:
                    return False
                else:
                    self.triggerValues[idx] = result
                    return result

        except Exception:
            tb = traceback.format_exc()
            logging.debug(tb)
            return False

    def checkCondition(self, conditionStr):
        try:
            code = self.generateCode(conditionStr, True)
        except Exception:
            tb = traceback.format_exc()
            tb = tb+'\n'+code+"\nERROR in code generation"
            logging.error(tb)
            if self.executedCallback:
                self.executedCallback(False, tb)
            return False, tb
        try:
            self.condition = importCode(code, "condition")
            #print(dir(self.condition))
        except Exception:
            tb = traceback.format_exc()
            tb = tb+'\n'+code+"\nSYNTAX ERROR in condition"
            logging.error(tb)
            logging.error(conditionStr)
            if self.executedCallback:
                self.executedCallback(False, tb)
            return False, tb
        try:
            self.condition.init(self)
            # return True
        except Exception:
            tb = traceback.format_exc()
            tb = tb+'\n'+code+"\nERROR in code initialization"
            logging.error(tb)
            if self.executedCallback:
                self.executedCallback(False, tb)
            return False, tb
        try:
            clock = time.time()
            prints = self.condition.test(self, clock)
            if self.executedCallback:
                self.executedCallback(True, prints)
            return True, prints
        except Exception:
            tb = traceback.format_exc()
            tb = tb+'\n'+code+"\nERROR in code execution"
            logging.error(tb)
            if self.executedCallback:
                self.executedCallback(False, tb)
            return False, tb

    def executeScript(self, scriptStr):
        try:
            code = self.generateCode(scriptStr, False)
        except Exception:
            tb = traceback.format_exc()
            tb = tb+'\n'+code+"\nERROR in code generation"
            logging.error(tb)
            if self.executedCallback:
                self.executedCallback(False, tb)
            return False, tb
        try:
            self.script = importCode(code, "script")
            #print(dir(self.script))
        except Exception:
            tb = traceback.format_exc()
            tb = tb+'\n'+code+"\nSYNTAX ERROR in script"
            logging.error(tb)
            if self.executedCallback:
                self.executedCallback(False, tb)
            return False, tb
        try:
            self.script.init(self)
            # return True
        except Exception:
            tb = traceback.format_exc()
            tb = tb+'\n'+code+"\nERROR in code initialization"
            logging.error(tb)
            if self.executedCallback:
                self.executedCallback(False, tb)
            return False, tb
        try:
            clock = time.time()
            prints = self.script.test(self, clock)
            if self.executedCallback:
                self.executedCallback(True, prints)
            return True, prints
        except Exception:
            tb = traceback.format_exc()
            tb = tb+'\n'+code+"\nERROR in code execution"
            logging.error(tb)
            if self.executedCallback:
                self.executedCallback(False, tb)
            return False, tb
