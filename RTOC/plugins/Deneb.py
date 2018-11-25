try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from ..LoggerPlugin import LoggerPlugin

import time
from threading import Thread
import traceback
import requests
from PyQt5 import uic
from PyQt5 import QtWidgets
import socket
import threading
import os

devicename = "Deneb"

socket_timeout = 3
HOST, PORT = "192.168.178.71", 1991


def communicate(data, host, port):
    global response
    try:
        response = 'error: received no response'

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(socket_timeout)
        sock.connect((host, port))
        sock.sendall(bytes(data + "\n", "utf-8"))

        response = str(sock.recv(1024), "utf-8")
    except ConnectionRefusedError:
        response = 'error: connection refused by remote host'
    except socket.timeout:
        response = 'error: connection timed out'
    finally:
        sock.close()
    return 1


def C_client(data, host=HOST, port=PORT):
    start_t = time.time()
    request_thread = threading.Thread(target=communicate, args=(data, host, port))
    request_thread.start()
    while time.time()-start_t < socket_timeout*1.1:
        time.sleep(0.001)
        if not request_thread.isAlive():
            return response
    return "error: connection timed out"

############################# DO NOT EDIT FROM HERE ################################################


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

        self.__base_address = ""
        self.samplerate = 1
        self.temp_des = 0
        self.__s = requests.Session()

    # THIS IS YOUR THREAD
    def updateT(self):
        diff = 0
        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            name, y = self.deneb_get_all()
            name0, y0, devname0 = [],[],"Engine0"
            name1, y1, devname1 = [],[],"Engine1"
            nameX, yX, devnameX = [],[], "Deneb"
            for idx, n in enumerate(name):
                if "engine0" in n:
                    name0.append(n.replace("engine0:",""))
                    y0.append(y[idx])
                elif "engine1" in n:
                    name1.append(n.replace("engine1:",""))
                    y1.append(y[idx])
                else:
                    nameX.append(n)
                    yX.append(y[idx])
            if len(y0)>0:
                self.stream(y0, name0, devname0, [""]*len(y0))
            if len(y1)>0:
                self.stream(y1, name1, devname1, [""]*len(y1))
            if len(yX)>0:
                self.stream(yX, nameX, devnameX, [""]*len(yX))

            diff = (time.time() - start_time)

    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir, file = os.path.split(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/Deneb/deneb.ui", self.widget)
        # self.setCallbacks()
        self.widget.pushButton.clicked.connect(self.__openConnectionCallback)
        self.widget.samplerateSpinBox.valueChanged.connect(self.__changeSamplerate)
        self.widget.comboBox.setCurrentText(HOST)
        self.__openConnectionCallback()
        return self.widget

    def __openConnectionCallback(self):
        if self.run:
            self.run = False
            self.widget.pushButton.setText("Verbinden")
            self.__base_address = ""
        else:
            address = self.widget.comboBox.currentText()
            self.__base_address = "http://"+address+"/"
            try:
                self.deneb_get_all()
                ok = True
            except:
                ok = False
            if ok:
                self.run = True
                self.__updater = Thread(target=self.updateT)
                self.__updater.start()
                self.widget.pushButton.setText("Beenden")
            else:
                self.__base_address = ""
                self.run = False
                self.widget.pushButton.setText("Fehler")

    def deneb_get_all(self):
        instring = C_client("parameter-dump;")
        data_blocks = instring.split(";")
        names = []
        y_values = []
        for d in data_blocks[:-1]:
            try:
                y_values.append(float(d.split("=")[1]))
                names.append(d.split("=")[0])
            except IndexError:
                #print(" ### failed to split this string: "+str(d))
                pass
        return names, y_values

    def __changeSamplerate(self):
        self.samplerate = self.widget.samplerateSpinBox.value()


if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
