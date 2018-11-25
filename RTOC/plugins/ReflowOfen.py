try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from ..LoggerPlugin import LoggerPlugin

import os
import time
from threading import Thread
import traceback
import requests
from PyQt5 import uic
from PyQt5 import QtWidgets
import os

devicename = "ReflowOfen"


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        # Plugin setup
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)
        self.smallGUI = True

        self.dataY = [0, 0]
        self.datanames = ["Temperatur", "SollTemp"]
        self.dataunits = ["°C", "°C"]

        self.__base_address = ""
        self.samplerate = 1
        self.temp_des = 0
        self.__s = requests.Session()

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
                self.temp_des = values[1]
                self.widget.spinBox.setValue(self.temp_des)
                self.stream(self.dataY,  self.datanames,  self.devicename, self.dataunits)

            diff = (time.time() - start_time)

    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir, file = os.path.split(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/Reflow/reflow.ui", self.widget)
        # self.setCallbacks()
        self.widget.pushButton.clicked.connect(self.__openConnectionCallback)
        self.widget.spinBox.valueChanged.connect(self.__setTempDes)
        self.widget.samplerateSpinBox.valueChanged.connect(self.__changeSamplerate)
        self.widget.comboBox.setCurrentText("reflowofen")
        self.__openConnectionCallback()
        return self.widget

    def __openConnection(self, address):
        ok, test = self.__get("getTemp")
        return ok

    def __openConnectionCallback(self):
        if self.run:
            self.run = False
            self.widget.pushButton.setText("Verbinden")
            self.__base_address = ""
        else:
            address = self.widget.comboBox.currentText()
            self.__base_address = "http://"+address+"/"
            if self.__openConnection(address):
                self.run = True
                self.__updater.start()
                self.widget.pushButton.setText("Beenden")
            else:
                self.__base_address = ""
                self.run = False
                self.widget.pushButton.setText("Fehler")

    def __get_data(self):
        ok, temp = self.__get("getTemp")
        ok2, tempDes = self.__get("getTempDes")
        if temp != "<70":
            temp = float(temp)
        else:
            temp = 0
        tempDes = float(tempDes)
        return ok and ok2, [temp, tempDes]

    def __post(self, data, adress="", noerror=204):
        try:
            r = self.__s.post(self.__base_address + adress, json=data)
            if r.status_code != noerror:
                raise Exception(
                    "Error: {code} - {content}".format(code=r.status_code, content=r.content.decode('utf-8')))
            return True, r
        except:
            tb = traceback.format_exc()
            print(tb)
            print("TRACEBACK HAS BEEN IGNORED. HTTP-POST FAILED")
            return False, "Error posting "+str(adress)
            return False, r

    def __get(self, path=""):
        try:
            r = self.__s.get(self.__base_address + str(path))
            data = r.content.decode('utf-8')
            #io = StringIO(data)
            io = data
            #io = json.load(io)
            #io = json.loads(data)
            return True, io
        except:
            tb = traceback.format_exc()
            print(tb)
            print("TRACEBACK HAS BEEN IGNORED. HTTP-GET FAILED")
            return False, "Error getting "+str(path)

    def __changeSamplerate(self):
        self.samplerate = self.widget.samplerateSpinBox.value()

    def __setTempDes(self):
        if self.temp_des != self.widget.spinBox.value():
            self.temp_des = self.widget.spinBox.value()
            self.__get("?manual=1&temp_des="+str(self.temp_des))


if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
