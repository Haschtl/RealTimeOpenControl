from PyQt5 import QtCore
from PyQt5 import uic
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QCoreApplication

import os
import sys

from ..lib import pyqt_customlib as pyqtlib

translate = QCoreApplication.translate


class RemoteWidget(QtWidgets.QWidget):
    def __init__(self, selfself, remotehost="", parent=None):
        super(RemoteWidget, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/data'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/ui/remoteHostWidget.ui", self)
        self.setWindowTitle(remotehost)
        #elf.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.self = selfself
        self.hostname = remotehost
        self.parent = parent
        self.listWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.listWidget.customContextMenuRequested.connect(self.listItemRightClicked)

        self.disconnectButton.clicked.connect(self.disconnect)
        self.maxLengthSpinBox.editingFinished.connect(self.resizeRemoteLogger)
        self.clearButton.clicked.connect(self.clear)
        self.pauseButton.clicked.connect(self.pause)
        self.saveButton.clicked.connect(self.saveRemoteSession)
        self.remote = self.self.logger.remote.getConnection(self.hostname)
        self.remote.updateRemoteCallback = self.updateRemote
        if self.remote != None:
            self.maxLengthSpinBox.setValue(self.remote.maxLength)
            self.updateList()
            self.pauseButton.setChecked(self.remote.pause)
            self.setStatusLabel()

    def setStatusLabel(self):
        if self.remote.status == "connected":
            self.statusLabel.setText(translate('RTRemote', 'Verbunden'))
            self.statusLabel.setStyleSheet('background-color: rgb(0, 82, 17)')
        elif self.remote.status == "disconnected":
            self.statusLabel.setText(translate('RTRemote', 'Fehler'))
            self.statusLabel.setStyleSheet('background-color: rgb(98, 1, 1)')
        elif self.remote.status == "wrongPassword":
            self.statusLabel.setText(translate('RTRemote', 'Falsches Passwort'))
            self.statusLabel.setStyleSheet('background-color: rgb(98, 1, 1)')
        elif self.remote.status == "error":
            self.statusLabel.setText(translate('RTRemote', 'Fehler'))
            self.statusLabel.setStyleSheet('background-color: rgb(98, 1, 1)')
        elif self.remote.status == "protected":
            self.statusLabel.setText(translate('RTRemote', 'Passwortgeschützt'))
            self.statusLabel.setStyleSheet('background-color: rgb(98, 1, 1)')

    def disconnect(self):
        ans = pyqtlib.alert_message(translate('RTRemote', 'Verbindung trennen'), translate('RTRemote', 'Möchtest du die Verbindung zu ')+self.hostname+translate(
            'RTRemote', ' trennen?'), translate('RTRemote', 'Übertragene Signale bleiben bestehen'), "", translate('RTRemote', "Ja"), translate('RTRemote', "Nein"))
        if ans:
            ans = self.self.logger.remote.disconnect(self.hostname)
            if ans == False:
                ans = pyqtlib.info_message(translate('RTRemote', 'Fehler'), translate(
                    'RTRemote', 'Konnte die Verbindung zu ')+self.hostname+translate('RTRemote', ' nicht trennen.'), '')
            self.close()

    def resizeRemoteLogger(self):
        self.self.logger.remote.resize(self.hostname, self.maxLengthSpinBox.value())

    def something(self):
        if self.checkBox.isChecked():
            selection = self.remote.siglist
            selection = [".".join(i) for i in selection]
        else:
            selection = []
            for o in self.listWidget.selectedItems():
                selection.append(o.text())

    def updateList(self):
        t = []
        for o in self.listWidget.selectedItems():
            t.append(o.text())
        self.listWidget.clear()
        for sig in self.remote.siglist:
            self.listWidget.addItem('.'.join(sig))
        for idx in range(self.listWidget.count()):
            sig = self.listWidget.item(idx)
            if sig.text() in t:
                self.listWidget.item(idx).setSelected(True)
        # now tell RTRemote to only listen to selected Items

    def plotSignals(self):
        pass

    def closeEvent(self, event, *args, **kwargs):
        self.parent.close()
        widgetIdx = -1
        for idx, widget in enumerate(self.self.remoteHostWidgets):
            if widget.widget().hostname == self.hostname:
                widgetIdx = idx
        if widgetIdx != -1:
            self.self.remoteHostWidgets.pop(widgetIdx)
        super(RemoteWidget, self).closeEvent(event)

    def toggleCheckAll(self, state):
        for idx in range(self.listWidget.count()):
            self.listWidget.item(idx).setSelected(state)

    def listItemRightClicked(self, QPos):
        self.listMenu = QtGui.QMenu()
        menu_item = self.listMenu.addAction(translate('RTRemote', "Signal löschen"))
        menu_item.triggered.connect(self.menuItemClicked)
        parentPosition = self.listWidget.mapToGlobal(QtCore.QPoint(0, 0))
        self.listMenu.move(parentPosition + QPos)
        self.listMenu.show()

    def menuItemClicked(self):
        currentItemName = str(self.listWidget.currentItem().text())
        self.self.logger.remote.clearHost(self.hostname, [currentItemName])

    def clear(self):
        self.self.logger.remote.clearHost(self.hostname, 'all')

    def pause(self, value):
        self.self.logger.remote.pauseHost(self.hostname, value)

    def saveRemoteSession(self):
        examplename = "RTOC-RemoteSession"
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, translate('RTRemote', "Session speichern"),
                                                            (QtCore.QDir.homePath() + "/" + examplename + ".json"), "JSON Files (*.json)")
        if fileName:
            self.self.logger.remote.downloadSession(self.hostname, fileName)
            pyqtlib.info_message(translate('RTRemote', 'Download abgeschlossen'), translate(
                'RTRemote', 'Session wurde erfolgreich heruntergeladen.'), '')

    def updateRemote(self):
        self.updateList()
        self.maxLengthSpinBox.setValue(self.remote.maxLength)
        self.setStatusLabel()
