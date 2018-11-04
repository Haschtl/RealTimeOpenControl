from LoggerPlugin import LoggerPlugin

import time
from threading import Thread
import traceback
import requests
from PyQt5 import uic
from PyQt5 import QtWidgets
from PyQt5 import QtCore
import socket
import threading

devicename = "NetWoRTOC"
HOST = "127.0.0.1"


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        # Plugin setup
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)
        self.smallGUI = False

        # Data-logger thread
        self.run = False  # False -> stops thread
        self.__updater = Thread(target=self.updateT)    # Actualize data
        # self.updater.start()

        self.samplerate = 1
        self.__siglist = []

    # THIS IS YOUR THREAD
    def updateT(self):
        diff = 0
        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            try:
                ans = self.sendTCP(getSignalList= True)
                if ans:
                    if 'signallist' in ans.keys():
                        if ans['signallist'] != self.__siglist:
                            self.__siglist = ans['signallist']
                            self.updateList()
                    if self.widget.streamButton.isChecked():
                        self.plotSignals()
            except:
                tb = traceback.format_exc()
                print(tb)
            diff = time.time() - start_time

    def plotSignals(self):
        if self.widget.checkBox.isChecked():
            selection = self.__siglist
            selection = [".".join(i) for i in selection]
        else:
            selection = []
            for o in self.widget.listWidget.selectedItems():
                selection.append(o.text())
        if selection != []:
            ans = self.sendTCP(getSignal= selection)
            if ans != False:
                if 'signals' in ans.keys():
                    for sig in ans['signals'].keys():
                        signame = sig.split('.')
                        s = ans['signals'][sig]
                        self.plot(s[0],s[1],sname = signame[1], dname=signame[0]+"_Remote")

    def updateList(self):
        t = []
        for o in self.widget.listWidget.selectedItems():
            t.append(o.text())
        self.widget.listWidget.clear()
        for sig in self.__siglist:
            self.widget.listWidget.addItem('.'.join(sig))
        for idx in range(self.widget.listWidget.count()):
            sig = self.widget.listWidget.item(idx)
            if sig.text() in t:
                self.widget.listWidget.item(idx).setSelected(True)
    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        uic.loadUi("plugins/netWoRTOC/networtoc.ui", self.widget)
        # self.setCallbacks()
        self.widget.connectButton.clicked.connect(self.__openConnectionCallback)
        self.widget.doubleSpinBox.valueChanged.connect(self.__changeSamplerate)
        self.widget.comboBox.setCurrentText(HOST)
        self.widget.singleButton.clicked.connect(self.plotSignals)
        #self.__openConnectionCallback()
        return self.widget

    def __openConnectionCallback(self):
        if self.run:
            self.run = False
            self.widget.connectButton.setText("Verbinden")
        else:
            address = self.widget.comboBox.currentText()
            self.createTCPClient(address)
            self.run = True
            try:
                ok = self.sendTCP()
                if ok != False:
                    ok = True
            except:
                ok = False
            if ok:
                self.run = True
                self.__updater = Thread(target=self.updateT)
                self.__updater.start()
                self.widget.connectButton.setText("Beenden")
            else:
                self.__base_address = ""
                self.run = False
                self.widget.connectButton.setText("Fehler")


    def __changeSamplerate(self):
        self.samplerate = self.widget.doubleSpinBox.value()
