import traceback

from .importCode import importCode


class ScriptFunctions:
    def generateCode(self, s):
        s = self.replacePluginParameters(s)
        s = self.replacePluginMethods(s)
        s = self.replaceSignalNames(s)
        s = self.replaceLoggerFunctions(s)
        s, init = self.replaceGlobalVariables(s)
        s = s.replace('global.', 'self.')
        s = self.replaceLibraryFunctions(s)

        s = self.generateTriggerCode(s)
        s = self.printfunction() + s
        s = self.createFunction(s)
        s = "import math\nimport numpy as np\nimport sys\nimport scipy as sp\ntry:\n\timport RTOC.RTLogger.scriptLibrary as rtoc\nexcept (ImportError,SystemError):\n\tfrom .RTLogger import scriptLibrary as rtoc\n\n" + init + "\n"+s
        return s

    def replacePluginParameters(self, s):
        for parameter in self.pluginParameters.keys():
            s = s.replace(parameter, self.pluginParameters[parameter])
        for host in self.remote.devices.keys():
            for device in self.remote.devices[host].keys():
                for parameter in self.remote.devices[host][device]['parameters']:
                    # wenn Parameter zugewiesen wird
                    #value = self.remote.getParam(self, host, device, parameter[0])
                    value = parameter[1]
                    s = s.replace(host+':'+device+'.'+parameter[0], str(value))

                    # wenn Parameter verändert werden soll
                    # self.remote.callFuncOrParam(self, host, device, parameter[], value)
        return s

    def replacePluginMethods(self, s):
        for function in self.pluginFunctions.keys():
            s = s.replace(function, self.pluginFunctions[function])
        for host in self.remote.devices.keys():
            for device in self.remote.devices[host].keys():
                for function in self.remote.devices[host][device]['functions']:
                    strung = "self.remote.callFuncOrParam2('" + \
                        host+"','"+device+"','"+function+"',None)"
                    s = s.replace(host+':'+device+'.'+function+"()", strung)
                    strung = "self.remote.callFuncOrParam2('"+host+"','"+device+"','"+function+"','"
                    s = s.replace(host+':'+device+'.'+function+"(", strung)
        return s

    def replaceSignalNames(self, s):
        for signal in self.signalNames:
            sigIdx = self.getSignalId(signal[0], signal[1])
            sigIdx = self.signalIDs.index(sigIdx)
            if sigIdx != -1:
                s = s.replace(
                    signal[0]+"."+signal[1]+".x", "np.array(self.signals["+str(sigIdx)+"][0])")
                s = s.replace(
                    signal[0]+"."+signal[1]+".y", "np.array(self.signals["+str(sigIdx)+"][1])")
                s = s.replace(
                    signal[0]+"."+signal[1]+".latest", "self.signals["+str(sigIdx)+"][1][-1]")
                s = s.replace(
                    signal[0]+"."+signal[1], "np.array(self.signals["+str(sigIdx)+"][0]), np.array(self.signals["+str(sigIdx)+"][1])")
        return s

    def replaceLibraryFunctions(self, s):
        s = s.replace("rtoc.lsfit(", "rtoc.lsfit(self, ")
        s = s.replace("rtoc.resample(", "rtoc.resample(self, ")
        s = s.replace("rtoc.resampleFourier(", "rtoc.resampleFourier(self, ")
        s = s.replace("rtoc.combine(", "rtoc.combine(self, ")
        return s

    def replaceLoggerFunctions(self, s):
        s = s.replace("stream(", "self.addData(")

        s = s.replace("event(", "self.addNewEvent(")
        s = s.replace("plot(", "self.plot(")

        s = s.replace("print(", "prints += print(")

        s = s.replace("clearData()", "self.clearCB()")
        s = s.replace("exportData(", "self.exportData(")

        s = s.replace("while True:", "while self.run:")
        s = s.replace("sendTCP(", "self._sendTCP(")
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

        except:
            tb = traceback.format_exc()
            print(tb)
            return False
