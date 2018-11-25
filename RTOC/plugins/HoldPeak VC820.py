try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from ..LoggerPlugin import LoggerPlugin

from plugins.holdPeak_VC820.vc820py.vc820 import MultimeterMessage
import serial
import sys
from threading import Thread
import traceback
import os

from PyQt5 import uic
from PyQt5 import QtWidgets

devicename = "HoldPeak"


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        # Plugin setup
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)
        self.smallGUI = True

        # Data-logger thread
        self.run = False  # False -> stops thread
        self.__updater = Thread(target=self.updateT)    # Actualize data
        # self.updater.start()

    def __openPort(self, portname="COM7"):
        self.datanames = ['Data']     # Names for every data-stream

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
            self.serial_port = serial.Serial(
                self.portname, baudrate=2400, parity='N', bytesize=8, timeout=1, rtscts=1, dsrdtr=1)
            # dtr and rts settings required for adapter
            self.serial_port.dtr = True
            self.serial_port.rts = False
            # -------------
            return True
        except:
            tb = traceback.format_exc()
            print(tb)
            return False

    # THIS IS YOUR THREAD
    def updateT(self):
        while self.run:
            valid, value, unit = self.get_data()
            if unit == "V":
                datanames = ["Spannung"]
            elif unit == "A":
                datanames = ["Strom"]
            elif unit == "Ohm":
                datanames = ["Widerstand"]
            elif unit == "°C":
                datanames = ["Temperatur"]
            elif unit == "F":
                datanames = ["Kapazität"]
            elif unit == "Hz":
                datanames = ["Frequenz"]
            else:
                datanames = [unit]
            if valid:
                self.stream(value,  datanames,  self.devicename, unit)

    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir, file = os.path.split(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/holdPeak_VC820/portSelectWidget.ui", self.widget)
        # self.setCallbacks()
        self.widget.pushButton.clicked.connect(self.__openPortCallback)
        self.__openPortCallback()
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
        test = self.serial_port.read(1)
        if len(test) != 1:
            print("recieved incomplete data, skipping...", file=sys.stderr)
            return False, None, None
        if MultimeterMessage.check_first_byte(test[0]):
            data = test + self.serial_port.read(MultimeterMessage.MESSAGE_LENGTH-1)
        else:
            print("received incorrect data (%s), skipping..." % test.hex(), file=sys.stderr)
            return False, None, None
        if len(data) != MultimeterMessage.MESSAGE_LENGTH:
            print("received incomplete message (%s), skipping..." % data.hex(), file=sys.stderr)
            return False, None, None
        try:
            message = MultimeterMessage(data)
            #message.value = message.get_base_reading()
        except ValueError as e:
            print(e)
            print("Error decoding: %s on message %s" % (str(e), data.hex()))
            return False, None, None
        # print(str(message))
        # return True, message.value, message.unit
        return True, round(message.value*message.multiplier, 10), message.base_unit


if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
