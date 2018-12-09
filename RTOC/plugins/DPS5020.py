try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from ..LoggerPlugin import LoggerPlugin

import sys
from threading import Thread, Lock
import traceback
import os

from PyQt5 import uic
from PyQt5 import QtWidgets

try:
    import minimalmodbus
except ImportError:
    sys.exit("\nERROR\nminimalmodbus for Python3 not found!\nPlease install with 'pip3 install minimalmodbus'")

devicename = "DPS5020"


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        # Plugin setup
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)
        self.smallGUI = True

        self.__lock = Lock()
        self.__data = None
        self.smallGUI = True
        self.locked = False
        self.power = False
        self.__serialBaudrate = 9600
        self.__serialByteSize = 8
        self.__serialTimeOut = 2
        self.CV = True  # False = CC

        # Data-logger thread
        self.run = False  # False -> stops thread
        self.__updater = Thread(target=self.updateT)    # Actualize data
        # self.updater.start()

    def __openPort(self, portname="/dev/ttyUSB0"):
        self.__datanames = ['VOut', 'IOut', "POut", "VIn",
                            "VSet", "ISet"]     # Names for every data-stream
        self.__dataY = [0, 0, 0, 0, 0, 0]
        # Represents the unit of the current
        self.__dataunits = ['V', 'A', 'W', 'V', 'V', 'V']
        # Communication setup
        #self.portname = "/dev/ttyUSB0"
        #self.portname = "COM7"
        self.portname = portname
        #################################################################################
        # os.system("sudo chmod a+rw /dev/ttyUSB0")
        # #######
        # uncomment this line if you do not set device rules:
        # > sudo nano /etc/udev/rules.d/50-myusb.rules
        # > * SUBSYSTEMS=="usb", ATTRS{idVendor}=="067b", ATTRS{idProduct}=="2303", GROUP="users", MODE="0666"
        # > [Strg+O, Strg+X]
        # > sudo udevadm control --reload
        # Ref: http://ask.xmodulo.com/change-usb-device-permission-linux.html
        #################################################################################
        try:
            self.__powerSupply = minimalmodbus.Instrument(self.portname, 1)
            self.__powerSupply.serial.baudrate = self.__serialBaudrate
            self.__powerSupply.serial.bytesize = self.__serialByteSize
            self.__powerSupply.serial.timeout = self.__serialTimeOut
            self.__powerSupply.mode = minimalmodbus.MODE_RTU
            # -------------
            return True
        except:
            tb = traceback.format_exc()
            print(tb)
            return False

    # THIS IS YOUR THREAD
    def updateT(self):
        while self.run:
            valid, values = self.get_data()
            self.__dataY = values
            if valid:
                self.stream(self.__dataY,  self.__datanames,  self.devicename, self.__dataunits)

    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir = self.getDir(__file__)
        uic.loadUi(packagedir+"/DPS5020/dps5020.ui", self.widget)
        # self.setCallbacks()
        self.widget.pushButton.clicked.connect(self.__openPortCallback)
        self.widget.currBox.editingFinished.connect(self.setCurrAction)
        self.widget.voltBox.editingFinished.connect(self.setVoltAction)
        self.widget.maxCurrBox.editingFinished.connect(self.setMaxCurrAction)
        self.widget.maxVoltBox.editingFinished.connect(self.setMaxVoltAction)
        self.widget.maxPowBox.editingFinished.connect(self.setMaxPowAction)
        self.__openPortCallback()
        self.setLabels()
        return self.widget

    def __openPortCallback(self):
        if self.run:
            self.run = False
            self.widget.pushButton.setText("Verbinden")
        else:
            port = self.widget.comboBox.currentText()
            if self.__openPort(port):
                self.run = True
                self.__updater = Thread(target=self.updateT)    # Actualize data
                self.__updater.start()
                self.widget.pushButton.setText("Beenden")
            else:
                self.run = False
                self.widget.pushButton.setText("Fehler")

    def get_data(self):
        try:
            self.__lock.acquire()
            self.__data = self.__powerSupply.read_registers(0, 11)
            self.__lock.release()
            # data[0] U-set x100 (R/W)
            # data[1] I-set x100 (R/W)
            # data[2] U-out x100
            # data[3] I-out x100
            # data[4] P-out x100
            # data[5] U-in x100
            # data[6] lock/unlock 1/0 (R/W)
            # data[7] Protected 1/0
            # data[8] operating mode CC/CV 1/0
            # data[9] on/off 1/0 (R/W)
            # data[10] display intensity 1..5 (R/W)
            if self.__data[6] == 1:
                self.locked = True
            else:
                self.locked = False
            if self.__data[8] == 1:
                self.CV = False
            else:
                self.CV = True
            if self.__data[9] == 1:
                self.power = True
            else:
                self.power = False
                ['VOut', 'IOut', "POut", "VIn", "VSet", "ISet"]
            self.setLabels()
            return True, [self.__data[2]/100, self.__data[3]/100, self.__data[4]/100, self.__data[5]/100, self.__data[0]/100, self.__data[1]/100]
        except:
            tb = traceback.format_exc()
            print(tb)
            return False, []

    def setPower(self, value=False):
        if self.run:
            print("Changing power-state")
            # onoff=self.__powerSupply.read_register(9)
            # self.powerButton.setChecked(bool(onoff))
            self.__lock.acquire()
            if value:
                self.__powerSupply.write_register(9, 1)
                self.__event("Power on")
            else:
                self.__powerSupply.write_register(9, 0)
                self.__event("Power off")
            self.__lock.release()
            self.power = value

    def setLocked(self, value=True):
        if self.run:
            print("Changing locked-state")
            # onoff=self.__powerSupply.read_register(6)
            # self.powerButton.setChecked(bool(onoff))
            self.__lock.acquire()
            if value:
                self.__powerSupply.write_register(6, 1)
            else:
                self.__powerSupply.write_register(6, 0)
            self.locked = value
            self.__lock.release()

    def setVoltage(self, value=0):
        if self.run:
            self.__lock.acquire()
            self.__powerSupply.write_register(0, int(value*100))
            self.__lock.release()

    def setCurrent(self, value=0):
        self.__lock.acquire()
        self.__powerSupply.write_register(1, int(value*100))
        self.__lock.release()

    def setCurrAction(self):
        value = self.widget.currBox.value()
        self.setCurrent(value)

    def setVoltAction(self):
        value = self.widget.voltBox.value()
        self.setCurrent(value)

    def setMaxCurrAction(self):
        value = self.widget.maxCurrBox.value()

    def setMaxVoltAction(self):
        value = self.widget.maxVoltBox.value()

    def setMaxPowAction(self):
        value = self.widget.maxPowBox.value()

    def setLabels(self):
        # if self.__data:
            #    if self.widget.currBox.value()!=self.__data[1]/100:
            #        self.widget.currBox.setValue(self.__data[1]/100)
            #    if self.widget.voltBox.value()!=self.__data[0]/100:
            #        self.widget.voltBox.setValue(self.__data[0]/100)
        pass
        # self.widget.maxCurrBox.setValue(self.gen_level)
        # self.widget.maxVoltBox.setValue(self.offset)
        # self.widget.maxPowBox.setValue(self.phase)


if __name__ == "__main__":
    standalone = Plugin()
