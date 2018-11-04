from LoggerPlugin import LoggerPlugin

import time
import math
import random
from threading import Thread
from PyQt5 import uic
from PyQt5 import QtWidgets

devicename = "Generator2"


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        # Plugin setup
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)
        self.smallGUI = True

        self.samplerate = 10            # Function frequency in Hz (1/sec)
        self.gen_freq = 1
        self.gen_level = 1           # Gain of function
        self.datanames = ["Square"]
        self.offset = 0
        self.phase = 0
        self.__olddata = [0]

        # Data-logger thread
        self.run = True  # False -> stops thread
        self.__updater = Thread(target=self.__updateT)    # Actualize data
        self.__updater.start()

        self.createTCPClient()

    # THIS IS YOUR THREAD
    def __updateT(self):
        diff = 0
        self.gen_start = time.time()
        while self.run:  # All should be inside of this while-loop, because self.run == False should stops this plugin
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            if self.datanames[0] == "Square":
                self.__square()
            elif self.datanames[0] == "Sawtooth":
                self.__sawtooth()
            elif self.datanames[0] == "Random":
                self.__noise()
            elif self.datanames[0] == "Sinus":
                self.__sinus()
            elif self.datanames[0] == "AC":
                self.__ac()
            elif self.datanames[0] == "DC":
                self.__dc()
            diff = (time.time() - start_time)

    # loadGUI needs to return a QWidget, which will be implemented into the Plugins-Area
    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        uic.loadUi("plugins/Funktionsgenerator/gen_function.ui", self.widget)
        self.setCallbacks()
        self.setLabels()
        return self.widget

    # # # # # Plugin specific functions

    def __square(self):
        if time.time() - self.gen_start >= 1/self.gen_freq:
            self.gen_start = time.time()
        if time.time() - self.gen_start >= 0.5/self.gen_freq:
            if self.dataY[0] != self.gen_level:
                self.sendTCP(self.dataY, self.datanames, self.devicename, self.dataunits)
            self.dataY[0] = self.gen_level + self.offset
            self.sendTCP(self.dataY, self.datanames, self.devicename, self.dataunits)

        else:
            if self.dataY[0] != 0:
                self.sendTCP(self.dataY, self.datanames, self.devicename, self.dataunits)
            self.dataY[0] = 0 + self.offset
            self.sendTCP(self.dataY, self.datanames, self.devicename, self.dataunits)

    def __sawtooth(self):
        if time.time() - self.gen_start >= 1/self.gen_freq:
            self.gen_start = time.time()
            if self.dataY[0] != 0:
                self.dataY[0] = self.gen_level
                self.sendTCP(self.dataY, self.datanames, self.devicename, self.dataunits)
            self.dataY[0] = 0 + self.offset
            self.sendTCP(self.dataY, self.datanames, self.devicename, self.dataunits)
        else:
            self.dataY[0] = self.gen_level * \
                ((time.time() - self.gen_start*self.gen_freq)) + self.offset
            self.sendTCP(self.dataY, self.datanames, self.devicename, self.dataunits)

    def __sinus(self):
        self.dataY[0] = self.gen_level * \
            math.sin((time.time()*self.gen_freq)*(2*math.pi) + self.phase) + self.offset
        self.stream(self.dataY, self.datanames, self.devicename, self.dataunits)

    def __noise(self):
        self.dataY[0] = random.uniform(0, self.gen_level) + self.offset
        self.stream(self.dataY, self.datanames, self.devicename, self.dataunits)

    def __ac(self):
        if time.time() - self.gen_start >= 1/self.gen_freq:
            self.gen_start = time.time()
        if time.time() - self.gen_start >= 0.5/self.gen_freq:
            if self.dataY[0] != self.gen_level:
                self.stream(self.dataY, self.datanames, self.devicename, self.dataunits)
            self.dataY[0] = self.gen_level + self.offset
            self.stream(self.dataY, self.datanames, self.devicename, self.dataunits)

        else:
            if self.dataY[0] != 0:
                self.stream(self.dataY, self.datanames, self.devicename, self.dataunits)
            self.dataY[0] = -self.gen_level - self.offset
            self.stream(self.dataY, self.datanames, self.devicename, self.dataunits)

    def __dc(self):
        self.dataY[0] = self.gen_level + self.offset
        self.stream(self.dataY, self.datanames, self.devicename, self.dataunits)

    def setCallbacks(self):
        #self.connect(self.widget.samplerate, SIGNAL("valueChanged()",self.changeSamplerate))
        self.widget.samplerate.valueChanged.connect(self.__changeSamplerate)
        self.widget.frequency.valueChanged.connect(self.__changeFrequency)
        self.widget.gain.valueChanged.connect(self.__changeGain)
        self.widget.offset.valueChanged.connect(self.__changeOffset)
        self.widget.function.currentIndexChanged.connect(self.__changeSignal)
        self.widget.phase.valueChanged.connect(self.__changePhase)
        self.widget.fun.clicked.connect(self.__toggleFun)

    def __toggleFun(self):
        if self.widget.fun.isChecked():
            self.xy = True
        else:
            self.xy = False

    def __changeFrequency(self):
        self.gen_freq = self.widget.frequency.value()

    def __changeGain(self):
        self.gen_level = self.widget.gain.value()

    def __changeOffset(self):
        self.offset = self.widget.offset.value()

    def __changeSamplerate(self):
        self.samplerate = self.widget.samplerate.value()

    def __changePhase(self):
        self.phase = self.widget.phase.value()

    def __changeSignal(self):
        self.event(self.widget.function.currentText(),
                   self.widget.function.currentText(), self.devicename)
        self.datanames[0] = self.widget.function.currentText()

    def setLabels(self):
        self.widget.samplerate.setValue(self.samplerate)
        self.widget.frequency.setValue(self.gen_freq)
        self.widget.gain.setValue(self.gen_level)
        self.widget.offset.setValue(self.offset)
        self.widget.phase.setValue(self.phase)


#if __name__ == "__main__":
    #standalone = Plugin()
    #standalone.sendData([4])
    #standalone.sendTCP([4])
    #standalone.run = False
