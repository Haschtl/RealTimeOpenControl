from ...LoggerPlugin import LoggerPlugin

import time
import math
import random
from PyQt5 import uic
from PyQt5 import QtWidgets
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)
devicename = "Generator"


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot=None, event=None):
        # Plugin setup
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)
        self.smallGUI = True

        self.gen_freq = 1
        self.gen_level = 1           # Gain of function
        self._sname = "Square"
        self.offset = 0
        self.phase = 0
        self._lastValue = 0

        self.setPerpetualTimer(self.__updateT, samplerate=10)
        self.gen_start = time.time()
        self.start()

    def __updateT(self):
        if self._sname == "Square":
            self.__square()
        elif self._sname == "Sawtooth":
            self.__sawtooth()
        elif self._sname == "Random":
            self.__noise()
        elif self._sname == "Sinus":
            self.__sinus()
        elif self._sname == "AC":
            self.__ac()
        elif self._sname == "DC":
            self.__dc()

    # loadGUI needs to return a QWidget, which will be implemented into the Plugins-Area
    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir = self.getDir(__file__)
        uic.loadUi(packagedir+"/Funktionsgenerator/gen_function.ui", self.widget)
        self.setCallbacks()
        self.setLabels()
        return self.widget

    # # # # # Plugin specific functions

    def __square(self):
        if time.time() - self.gen_start >= 1/self.gen_freq:
            self.gen_start = time.time()
        if time.time() - self.gen_start >= 0.5/self.gen_freq:
            if self._lastValue != self.gen_level:
                self.stream(self._lastValue, self._sname, unit=[""])
            self._lastValue = self.gen_level + self.offset
            self.stream(self._lastValue, self._sname, unit=[""])

        else:
            if self._lastValue != 0:
                self.stream(self._lastValue, self._sname, unit=[""])
            self._lastValue = 0 + self.offset
            self.stream(self._lastValue, self._sname, unit=[""])

    def __sawtooth(self):
        if time.time() - self.gen_start >= 1/self.gen_freq:
            self.gen_start = time.time()
            if self._lastValue != 0:
                #self._lastValue += self.gen_level*(self.gen_freq)/self.samplerate
                self._lastValue = self.gen_level
                self.stream(self._lastValue, self._sname, unit=[""])
            self._lastValue = 0 + self.offset
            self.stream(self._lastValue, self._sname, unit=[""])
        else:
            self._lastValue = self.gen_level * \
                ((time.time() - self.gen_start*self.gen_freq)) + self.offset
            self.stream(self._lastValue, self._sname, unit=[""])

    def __sinus(self):
        self._lastValue = self.gen_level * \
            math.sin((time.time()*self.gen_freq)*(2*math.pi) + self.phase) + self.offset
        self.stream(self._lastValue, self._sname, unit=[""])

    def __noise(self):
        self._lastValue = random.uniform(0, self.gen_level) + self.offset
        self.stream(self._lastValue, self._sname, unit=[""])

    def __ac(self):
        if time.time() - self.gen_start >= 1/self.gen_freq:
            self.gen_start = time.time()
        if time.time() - self.gen_start >= 0.5/self.gen_freq:
            if self._lastValue != self.gen_level:
                self.stream(self._lastValue, self._sname, unit=[""])
            self._lastValue = self.gen_level + self.offset
            self.stream(self._lastValue, self._sname, unit=[""])

        else:
            if self._lastValue != 0:
                self.stream(self._lastValue, self._sname, unit=[""])
            self._lastValue = -self.gen_level - self.offset
            self.stream(self._lastValue, self._sname, unit=[""])

    def __dc(self):
        self._lastValue = self.gen_level + self.offset
        self.stream(self._lastValue, self._sname, unit=[""])

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
        # self.event(self.widget.function.currentText(),
        #           self.widget.function.currentText())
        self._sname = self.widget.function.currentText()

    def setLabels(self):
        self.widget.samplerate.setValue(self.samplerate)
        self.widget.frequency.setValue(self.gen_freq)
        self.widget.gain.setValue(self.gen_level)
        self.widget.offset.setValue(self.offset)
        self.widget.phase.setValue(self.phase)


if __name__ == "__main__":
    standalone = Plugin()
    standalone.sendData([4])
    standalone.run = False
