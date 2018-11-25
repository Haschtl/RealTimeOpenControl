try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from ..LoggerPlugin import LoggerPlugin

import time
from threading import Thread
from PyQt5 import uic
from PyQt5 import QtWidgets
import os

from plugins.Octotouch.OctoprintApi import OctoprintAPI

devicename = "Kellerdrucker"
apikey = "04B64F291D4B4F7BA276344ED7A973A2"


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        # Plugin setup
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)
        self.smallGUI = True

        self.smallGUI = True
        self.dataY = [0, 0, 0, 0, 0, 0]
        self.datanames = ["Hotend0", "Hotend0Des", "Hotend1", "Hotend1Des", "Heatbed", "HeatbedDes"]
        self.dataunits = ["°C", "°C", "°C", "°C", "°C", "°C"]

        self.samplerate = 1

        # Data-logger thread
        self.run = False  # False -> stops thread
        self.__updater = Thread(target=self.updateT)    # Actualize data
        # self.updater.start()

    # THIS IS YOUR THREAD
    def updateT(self):
        diff = 0
        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            valid, values = self.__get_data()
            if valid:
                self.dataY = values
                self.widget.spinBox0.setValue(values[1])
                self.widget.spinBox1.setValue(values[3])
                self.widget.spinBoxB.setValue(values[5])
                self.stream(self.dataY,  self.datanames,  self.devicename, self.dataunits)

            diff = (time.time() - start_time)

    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir, file = os.path.split(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/Octotouch/octotouch.ui", self.widget)
        # self.setCallbacks()
        self.widget.pushButton.clicked.connect(self.__openConnectionCallback)
        self.widget.spinBox0.valueChanged.connect(self.__setTempDes0)
        self.widget.spinBox1.valueChanged.connect(self.__setTempDes1)
        self.widget.spinBoxB.valueChanged.connect(self.__setTempDesB)
        self.widget.samplerateSpinBox.valueChanged.connect(self.__changeSamplerate)
        self.widget.comboBox.setCurrentText("kellerdrucker")
        self.__openConnectionCallback()
        return self.widget

    def __openConnection(self):
        self.__api = OctoprintAPI(self.widget.comboBox.currentText(), apikey)
        ok, test = self.__api.getStatus()
        return ok

    def __openConnectionCallback(self):
        if self.run:
            self.run = False
            self.widget.pushButton.setText("Verbinden")
        else:
            if self.__openConnection():
                self.run = True
                self.__updater.start()
                self.widget.pushButton.setText("Beenden")
            else:
                self.run = False
                self.widget.pushButton.setText("Fehler")

    def __get_data(self):
        ok, data = self.__api.getStatus()
        hotend0 = float(data["temperature"]["tool0"]["actual"])
        hotend1 = float(data["temperature"]["tool1"]["actual"])
        bed = float(data["temperature"]["bed"]["actual"])

        hotend0des = float(data["temperature"]["tool0"]["target"])
        hotend1des = float(data["temperature"]["tool1"]["target"])
        bedDes = float(data["temperature"]["bed"]["target"])

        return ok, [hotend0, hotend0des, hotend1, hotend1des, bed, bedDes]

    def __changeSamplerate(self):
        self.samplerate = self.widget.samplerateSpinBox.value()

    def __setTempDes0(self):
        if self.dataY[1] != self.widget.spinBox0.value():
            self.__api.setNozzleTemp(self.widget.spinBox0.value(), 0)

    def __setTempDes1(self):
        if self.dataY[3] != self.widget.spinBox1.value():
            self.__api.setNozzleTemp(self.widget.spinBox1.value(), 1)

    def __setTempDesB(self):
        if self.dataY[5] != self.widget.spinBoxB.value():
            self.__api.setBedTemp(self.widget.spinBoxB.value())


if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
