try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from ..LoggerPlugin import LoggerPlugin

import os
import sys
import time
from threading import Thread
import requests
from PyQt5 import uic
from PyQt5 import QtWidgets

devicename = "Template"

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

    def updateT(self):
        diff = 0
        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            self.stream([0], "noName", self.devicename, [""]) # send data to RTOC

    def loadGUI(self): # Only needed for Plugin-GUI
        self.widget = QtWidgets.QWidget()
        packagedir = self.getDir(__file__)
        uic.loadUi(packagedir+"/Template/template.ui", self.widget)
        return self.widget



if __name__ == "__main__":
    os.chdir('..')
    app = QtWidgets.QApplication(sys.argv)
    myapp = QtWidgets.QMainWindow()
    widget = Plugin()
    widget.loadGUI()
    myapp.setCentralWidget(widget.widget)

    myapp.show()
    app.exec_()
    widget.run = False
    sys.exit()
