from PyQt5 import uic
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import QtGui
from functools import partial
import os
from threading import Thread

import plugins.netWoRTOC.networkscan as networkscan
import data.lib.pyqt_customlib as pyqtlib
from PyQt5.QtCore import QCoreApplication

import nmap
import socket

translate = QCoreApplication.translate
HOST = "127.0.0.1"

class GUI(QtWidgets.QWidget):
    updateDevices = QtCore.pyqtSignal(dict)
    updateHostListCallback = QtCore.pyqtSignal()

    def __init__(self, selfself):
        super(GUI, self).__init__()
        packagedir, file = os.path.split(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/networtoc.ui", self)
        # self.setCallbacks()
        self.self = selfself
        #self.connectButton.clicked.connect(self.self.__openConnectionCallback)
        #self.doubleSpinBox.valueChanged.connect(self.self.__changeSamplerate)
        self.hostlist = [HOST]
        self.comboBox.setCurrentText(HOST)
        #self.singleButton.clicked.connect(self.self.plotSignals)
        # self.widget.updateDevices = QtCore.pyqtSignal()
        self.updateDevices.connect(self.updateDeviceList, QtCore.Qt.QueuedConnection)
        self.updateHostListCallback.connect(self.updateHostList, QtCore.Qt.QueuedConnection)
        #self.__openConnectionCallback()
        self.searchButton.clicked.connect(self.getRTOCServerList)

        self.listWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.listWidget.customContextMenuRequested.connect(self.listItemRightClicked)

        self.checkBox.stateChanged.connect(self.toggleCheckAll)

    def toggleCheckAll(self, state):
        for idx in range(self.listWidget.count()):
            self.listWidget.item(idx).setSelected(state)

    def listItemRightClicked(self, QPos):
        self.listMenu= QtGui.QMenu()
        menu_item = self.listMenu.addAction(translate('NetWoRTOC',"Signal löschen"))
        menu_item.triggered.connect(self.menuItemClicked)
        parentPosition = self.listWidget.mapToGlobal(QtCore.QPoint(0, 0))
        self.listMenu.move(parentPosition + QPos)
        self.listMenu.show()

    def menuItemClicked(self):
        currentItemName=str(self.listWidget.currentItem().text() )
        ans = self.self.sendTCP(logger={'clear': [currentItemName]})

    def updateDeviceList(self, dict):
        for i in reversed(range(self.deviceLayout.count())):
            self.deviceLayout.itemAt(i).widget().setParent(None)
        self.pluginCallWidget.clear()
        for sig in dict.keys():
            button = QtWidgets.QToolButton()
            button.setText(sig)
            button.setCheckable(True)
            if dict[sig]['status'] == True:
                button.setChecked(True)
                for element in dict[sig]['functions']:
                    self.pluginCallWidget.addItem(sig+"."+element+'()')
                for element in dict[sig]['parameters']:
                    self.pluginCallWidget.addItem(sig+"."+element)
            elif dict[sig]['status'] != False:
                button.setToolTip(str(dict[sig]['status']))
            sizePolicy = QtGui.QSizePolicy(
                QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            button.setSizePolicy(sizePolicy)

            # button.setCheckable(True)
            button.clicked.connect(partial(self.self.toggleDevice, sig, button))
            self.deviceLayout.addWidget(button)            #self.widget.listWidget.addItem('.'.join(sig))

    def getRTOCServerList(self):
        if self.searchButton.text() != translate('NetWoRTOC','Sucht...'):
            ok = pyqtlib.alert_message(translate('NetWoRTOC',"RTOC-Netzwerksuche"), translate('NetWoRTOC',"Möchten Sie wirklich das Netzwerk nach RTOC-Servern durchsuchen?"), translate('NetWoRTOC',"Dieser Vorgang wird einige Zeit in Anspruch nehmen"))
            if ok:
                t = Thread(target=self.searchThread)
                t.start()
                self.searchButton.setText(translate('NetWoRTOC','Sucht...'))
        else:
            pyqtlib.info_message(translate('NetWoRTOC',"Bitte warten"), translate('NetWoRTOC',"NetWoRTOC sucht gerade nach RTOC-Servern"), translate('NetWoRTOC',"Bitte warten bis der Vorgang abgeschlossen ist."))

    def updateHostList(self):
        self.comboBox.clear()
        for item in self.hostlist:
            self.comboBox.addItem(item)
        pyqtlib.info_message(translate('NetWoRTOC',"Fertig"), translate('NetWoRTOC',"RTOC-Suche abgeschlossen"), str(len(self.hostlist)-1)+translate('NetWoRTOC'," Server gefunden."))
        self.searchButton.setText(translate('NetWoRTOC','Suchen'))

    def searchThread(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        ip_parts = ip.split('.')
        base_ip = ip_parts[0] + '.' + ip_parts[1] + '.' + ip_parts[2] + '.'
        nm = nmap.PortScanner()
        ans = nm.scan(base_ip+'0-255','5050')
        for ip in ans['scan'].keys():
            if ans['scan'][ip]['tcp'][5050]['state'] != 'closed':
                if len(ans['scan'][ip]['hostnames'])>0:
                    for hostname in ans['scan'][ip]['hostnames']:
                        if hostname['name'] != '':
                            self.hostlist.append(hostname['name'])
                else:
                    self.hostlist.append(ip)
        self.hostlist.append(HOST)
        self.updateHostListCallback.emit()
