from PyQt5 import QtCore
from PyQt5 import uic
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QCoreApplication

import os
import sys

from .scriptWidget import ScriptWidget
# from .globalActionWidget import GlobalActionWidget
# from .globalEventWidget import GlobalEventWidget
from ..lib import pyqt_customlib as pyqtlib
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

if True:
    translate = QCoreApplication.translate

    def _(text):
        return translate('remote', text)
else:
    import gettext
    _ = gettext.gettext


class RemoteWidget(QtWidgets.QWidget):
    update = QtCore.pyqtSignal()

    def __init__(self, selfself, remotehost="", parent=None, name="Remote"):
        super(RemoteWidget, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/RTOC_GUI'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/ui/remoteHostWidget.ui", self)
        self.toolBox.hide()
        self.editButton.hide()
        self.setWindowTitle(name)
        # self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.self = selfself
        self.hostname = remotehost
        self.parent = parent
        self.name = name
        self.listWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.listWidget.customContextMenuRequested.connect(self.listItemRightClicked)

        self.disconnectButton.clicked.connect(self.disconnect)
        self.maxLengthSpinBox.editingFinished.connect(self.resizeRemoteLogger)
        self.clearButton.clicked.connect(self.clear)
        self.pauseButton.clicked.connect(self.pause)
        self.saveButton.clicked.connect(self.saveRemoteSession)
        self.remote = self.self.logger.remote.getConnection(self.hostname)
        self.remote.updateRemoteCallback = self.update.emit
        self.update.connect(self.updateRemote)
        if self.remote is not None:
            self.maxLengthSpinBox.setValue(self.remote.maxLength)
            self.updateList()
            self.pauseButton.setChecked(self.remote.pause)
            self.setStatusLabel()

        # self.globalActionWidget = GlobalActionWidget(self.self.logger.remote)
        # self.globalEventWidget = GlobalEventWidget(self.self.logger.remote)
        # self.globalEventLayout.addWidget(self.globalEventWidget)
        # self.globalActionLayout.addWidget(self.globalActionWidget)

        self.scriptWidget = ScriptWidget(self.self.logger)
        self.scriptLayout.addWidget(self.scriptWidget)

        self.editLayout.hide()

        self.editButton.clicked.connect(self.toggleEditView)

    def toggleEditView(self, value):
        if value:
            self.hostLineEdit.setText(self.remote.host)
            self.portSpinBox.setValue(self.remote.port)
            self.nameLineEdit.setText(self.remote.name)
            self.passwordLineEdit.setText(self.remote.tcppassword)
            self.editLayout.show()
            self.pauseButton.hide()
            self.clearButton.hide()
        else:
            self.editLayout.hide()
            self.pauseButton.show()
            self.clearButton.show()

    def setStatusLabel(self):
        if self.remote.status == "connected":
            self.statusLabel.setText(translate('RTOC', 'Verbunden'))
            self.statusLabel.setStyleSheet('background-color: rgb(0, 82, 17)')
        elif self.remote.status == "disconnected":
            self.statusLabel.setText(translate('RTOC', 'Fehler'))
            self.statusLabel.setStyleSheet('background-color: rgb(98, 1, 1)')
        elif self.remote.status == "wrongPassword":
            self.statusLabel.setText(translate('RTOC', 'Falsches Passwort'))
            self.statusLabel.setStyleSheet('background-color: rgb(98, 1, 1)')
        elif self.remote.status == "error":
            self.statusLabel.setText(translate('RTOC', 'Fehler'))
            self.statusLabel.setStyleSheet('background-color: rgb(98, 1, 1)')
        elif self.remote.status == "protected":
            self.statusLabel.setText(translate('RTOC', 'Passwortgesch\xfctzt'))
            self.statusLabel.setStyleSheet('background-color: rgb(98, 1, 1)')

    def disconnect(self):
        if self.editButton.isChecked():
            self.toggleEditView(False)
            self.editButton.setChecked(False)
        else:
            ans = pyqtlib.alert_message(translate('RTOC', 'Verbindung trennen'), translate('RTOC', 'M\xf6chtest du die Verbindung zu {} trennen?').format(self.hostname), translate('RTOC', '\xdcbertragene Signale bleiben bestehen'), "", translate('RTOC', "Ja"), translate('RTOC', "Nein"))
            if ans:
                ans = self.self.logger.remote.disconnect(self.hostname)
                if ans is False:
                    ans = pyqtlib.info_message(translate('RTOC', 'Fehler'), translate('RTOC', 'Konnte die Verbindung zu {} nicht trennen.').format(self.hostname), '')
                self.close()

    def resizeRemoteLogger(self):
        self.self.logger.remote.resize(self.name, self.maxLengthSpinBox.value())
    #
    # def something(self):
    #     if self.checkBox.isChecked():
    #         selection = self.remote.siglist
    #         selection = [".".join(i) for i in selection]
    #     else:
    #         selection = []
    #         for o in self.listWidget.selectedItems():
    #             selection.append(o.text())

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
                sig.setSelected(True)
                self.listWidget.item(idx).setSelected(True)
        # self.self.logger.remote.sigSelectList = t
        self.remote.sigSelectList = [i.split('.') for i in t]
        # now tell RTRemote to only listen to selected Items

    def plotSignals(self):
        pass

    def closeEvent(self, event, *args, **kwargs):
        self.remote.close()
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
        menu_item = self.listMenu.addAction(translate('RTOC', "Signal l\xf6schen"))
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
        if self.editButton.isChecked():
            host = self.hostLineEdit.text()
            port = self.portSpinBox.value()
            name = self.nameLineEdit.text()
            password = self.passwordLineEdit.text()
            self.remote.saveSettings(host, port, name, password)

            self.toggleEditView(False)
            self.editButton.setChecked(False)
        else:
            title = translate('RTOC', "Session speichern")
            examplename = "RTOC-RemoteSession"
            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, title,
                                                                (QtCore.QDir.homePath() + "/" + examplename + ".json"), "JSON Files (*.json)")
            if fileName:
                self.self.logger.remote.downloadSession(self.hostname, fileName)
                pyqtlib.info_message(translate('RTOC', 'Download abgeschlossen'), translate('RTOC', 'Session wurde erfolgreich heruntergeladen.'), '')

    def updateRemote(self):
        self.updateList()
        self.maxLengthSpinBox.setValue(self.remote.maxLength)
        self.setStatusLabel()
