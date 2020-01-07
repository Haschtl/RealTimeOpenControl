from ...LoggerPlugin import LoggerPlugin

import time
import math
import random
from PyQt5 import uic
from PyQt5 import QtWidgets
devicename = "Generator"


class Plugin(LoggerPlugin):
    """
This is an example Plugin, which generates some signals.
    """
    def __init__(self, *args, **kwargs):
        # Plugin setup
        super(Plugin, self).__init__(*args, **kwargs)
        self.setDeviceName(devicename)
        self.smallGUI = True

        self.gen_freq = self.initPersistentVariable('gen_freq', 1)
        self.gen_level = self.initPersistentVariable('gen_level', 1)           # Gain of function
        self._sname = self.initPersistentVariable('_sname', "Square")
        self.offset = self.initPersistentVariable('offset', 1)
        self.phase = self.initPersistentVariable('phase', 1)
        self._lastValue = 0
        self.exampleString = self.initPersistentVariable('exampleString', "Hello")
        self.exampleBoolean = self.initPersistentVariable('exampleBoolean', True)
        self.__doc_exampleBoolean__ = "Beispiel-Boolean"
        self.__doc_exampleString__ = "Beispiel-Text"
        self.__doc_offset__ = "Y-Offset of selected signal"
        self.__doc_phase__ = "X-Phase of selected signal"
        self.__doc_gen_freq__ = "Frequency of selected signal"
        self.__doc_gen_level__ = "Amplitude of selected signal"

        self.setPerpetualTimer(self.__updateT, samplerate=10)
        self.gen_start = time.time()
        self.start()
        self._test = 2
        self.info('Generator started')

    @property
    def test(self):
        """
        Getter für test
        """
        return self._test

    @test.setter
    def test(self, value):
        """
        Setter für test
        """
        self._test = value

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

    def setFrequency(self, freq: float, inverse:bool=False):
        """
Set frequency of this signal. 
Args:
            freq (float): Frequency [1/s]
            inverse (bool): If true, 'freq' will be the samplerate
        """
        if type(freq) not in [int, float]:
            self.info('Generator: freq-Type wrong')
            return False

        if inverse is True:
            freq = 1/freq
            self.info('Generator: inverse freq')

        self.info('Setting frequency')
        self.gen_freq = freq
        return True

    # loadGUI needs to return a QWidget, which will be implemented into the Plugins-Area
    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir = self.getDir(__file__)
        uic.loadUi(packagedir+"/Funktionsgenerator/gen_function.ui", self.widget)
        self._setCallbacks()
        self._setLabels()
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

    def _setCallbacks(self):
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

    def changeExampleString(self, name:str):
        self.exampleString = name
        
    def changeType(self, stype:str='Square'):
        """
Change signal-type. 
Args:
            type (string): Choose one: 'Square','Sawtooth','Random','Sinus','AC','DC'
        """
        if stype == "Square":
            self._sname = stype
        elif stype == "Sawtooth":
            self._sname = stype
        elif stype == "Random":
            self._sname = stype
        elif stype == "Sinus":
            self._sname = stype
        elif stype == "AC":
            self._sname = stype
        elif stype == "DC":
            self._sname = stype

        self.savePersistentVariable('_sname', self._sname)

    def _setLabels(self):
        self.widget.samplerate.setValue(self.samplerate)
        self.widget.frequency.setValue(self.gen_freq)
        self.widget.gain.setValue(self.gen_level)
        self.widget.offset.setValue(self.offset)
        self.widget.phase.setValue(self.phase)

    def setAlphaColor(self, red=0, green=255, blue=0, alpha=255):
        """
{"type": "RGBA_Color", "red": {"min": 0, "max":255}, "green": {"min": 0, "max":255}, "blue": {"min": 0, "max":255}, "alpha": {"min": 0, "max":255}}
Set Color, each from 0-255
        """
        self.info("R: {}, G: {}, B: {}, A: {}".format(red, green, blue, alpha))


    def setColor(self, red=0, green=255, blue=0):
        """
{"type": "RGB_Color", "red": {"min": 0, "max":255}, "green": {"min": 0, "max":255}, "blue": {"min": 0, "max":255}}
Set Color, each from 0-255
        """
        self.info("R: {}, G: {}, B: {}, A: {}".format(red, green, blue))



if __name__ == "__main__":
    standalone = Plugin()
    standalone.sendData([4])
    standalone.run = False
