# -*- encoding: utf-8 -*-
"""
The core module of RTOC_GUI
"""

import sys

import os
from PyQt5 import QtCore
from PyQt5 import uic
from PyQt5 import QtWidgets, QtGui
from functools import partial
import traceback
import json

try:
    from .RTLogger import RTLogger
    from .lib import pyqt_customlib as pyqtlib
    from .lib import general_lib as lib
    from .RTOC_GUI.scriptWidget import ScriptWidget
    from .RTOC_GUI.eventWidget import EventWidget
    from .RTOC_GUI.RTPlotWidget import RTPlotWidget
    from .RTOC_GUI.Actions import Actions
    from .RTOC_GUI import RTOC_Import
except (SystemError, ImportError):
    from RTLogger import RTLogger
    from lib import pyqt_customlib as pyqtlib
    from lib import general_lib as lib
    from RTOC_GUI.scriptWidget import ScriptWidget
    from RTOC_GUI.eventWidget import EventWidget
    from RTOC_GUI.RTPlotWidget import RTPlotWidget
    from RTOC_GUI.Actions import Actions
    from RTOC_GUI import RTOC_Import

import logging as log
log.basicConfig(level=log.DEBUG)
logging = log.getLogger(__name__)

if os.name == 'nt':
    import ctypes
    myappid = 'RTOC.3.0'  # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

# I've got a Qt5-only Python distro installed (WinPython 3.5 Qt5) which includes pyqtgraph 0.10.0. Exporting images from PlotWidgets and ImageViews doesn't work anymore and gives this exception:
#
# Traceback (most recent call last): File "C:\WinPython35_Qt5\python-3.5.3.amd64\lib\site-packages\pyqtgraph\exporters\Exporter.py", line 77, in fileSaveFinished self.export(fileName=fileName, **self.fileDialog.opts) File "C:\WinPython35_Qt5\python-3.5.3.amd64\lib\site-packages\pyqtgraph\exporters\ImageExporter.py", line 70, in export bg = np.empty((self.params['width'], self.params['height'], 4), dtype=np.ubyte) TypeError: 'float' object cannot be interpreted as an integer QWaitCondition: Destroyed while threads are still waiting
#
# Didn't happen with WinPython 3.5 Qt4 (pyqtgraph 0.9.10 I think). Am I the only one experiencing this?
#
# Update: simple fix: in ImageExporter.py, line 70:
# bg = np.empty((int(self.params['width']), int(self.params['height']), 4), dtype=np.ubyte)
#
# https://github.com/pyqtgraph/pyqtgraph/issues/454

if True:
    translate = QtCore.QCoreApplication.translate

    def _(text):
        return translate('rtoc', text)
else:
    import gettext
    _ = gettext.gettext

LINECOLORS = ['r', 'g', 'b', 'c', 'm', 'y', 'w']


class _SubWindow(QtWidgets.QMainWindow):
    addSignal2 = QtCore.pyqtSignal(str, str, int, str)

    def __init__(self, logger, selfself, idx, title="SubWindow"):
        super(_SubWindow, self).__init__()  # logger, selfself, idx)
        self.widget = RTPlotWidget(logger, selfself, idx)
        _DOCK_OPTS = QtGui.QMainWindow.AnimatedDocks
        _DOCK_OPTS |= QtGui.QMainWindow.AllowNestedDocks
        _DOCK_OPTS |= QtGui.QMainWindow.AllowTabbedDocks
        self.self = selfself
        self.setDockOptions(_DOCK_OPTS)
        self.setCentralWidget(self.widget.widget)
        self.setWindowTitle(title)
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        app_icon = QtGui.QIcon(packagedir+"/data/icon.png")
        self.setWindowIcon(app_icon)
        self.show()
        self.signalObjects = self.widget.signalObjects
        self.treeWidget = self.widget.treeWidget

        self.addSignal2.connect(self.widget.addSignal, QtCore.Qt.QueuedConnection)
        # self.importer = None

    def closeEvent(self, event, *args, **kwargs):
        """
        Closes the main window and all its sub-components
        """
        if self.widget.id == 0:
            self.widget.stop()
        else:
            for signalObject in self.widget.signalObjects:
                self.self.plotWidgets[0].addSignal(
                    signalObject.devicename, signalObject.signalname, signalObject.id, signalObject.unit)
            while len(self.widget.signalObjects) != 0:
                signalObject = self.widget.signalObjects[0]
                self.widget.deleteSignal(
                    signalObject.id, signalObject.devicename, signalObject.signalname)
            self.self.deletePlotWidget(self.widget.id)
            self.widget.stop()
        super(_SubWindow, self).closeEvent(event)

    def clear(self):
        """
        Clears all RTPlotWidgets
        """
        self.widget.clear()

    def updatePlot(self):
        """
        Triggers each signal no reload data
        """
        self.widget.updatePlot()

    def stop(self):
        """
        Stops all signal plots
        """
        self.widget.stop()

    def deleteSignal(self, idx, devicename, signalname):
        """
        Deletes the selected signal in RTLogger
        """
        self.widget.deleteSignal(idx, devicename, signalname)

    def removeSignal(self, idx, devicename, signalname):
        """
        !!! I dont know whats the different to deleteSignal !!!
        """
        self.widget.removeSignal(idx, devicename, signalname)

    def addSignalRAW(self, signalObject):
        """
        Add a new signal to active RTPlotWidget with a signalObject
        """
        self.widget.addSignalRAW(signalObject)

    def addSignal(self, devicename, signalname, id, unit):
        """
        Add a new signal to active RTPlotWidget with a devicename, signalname, id and unit.
        """
        self.widget.addSignal(devicename, signalname, id, unit)


class RTOC(QtWidgets.QMainWindow, Actions):
    """GUI-code is not documented."""
    foundRTOCServerCallback = QtCore.pyqtSignal(list)
    reloadDevicesCallback = QtCore.pyqtSignal()

    def __init__(self, websocket=None, port=5050, forceLocal = False, customConfigPath=None):
        super(RTOC, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/RTOC_GUI/ui/rtoc.ui", self)
        self.setAcceptDrops(True)
        self.app_icon = QtGui.QIcon(packagedir+"/data/icon.png")
        self.setWindowIcon(self.app_icon)
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.app_icon)
        self.tray_icon.activated.connect(self.systemTrayClickAction)
        self.forceQuit = False
        self.initPlotWidgets()

        self.logger = RTLogger.RTLogger(websocket, port, True, forceLocal = forceLocal, customConfigPath=customConfigPath)
        self.config = self.logger.config
        self.settings = None  # window position settings
        self.loadPlotStyles()
        self.initScriptWidget()
        self.newPlotWidget()
        self.logger.tr = self.tr

        for sigID in self.logger.database.signals().keys():
            name = self.logger.database.getSignalName(sigID)
            dataunit = self.logger.database.signals()[sigID][4]
            self.addNewSignal(sigID, name[0], name[1], dataunit)

        self.logger.newSignalCallback = self.addNewSignal
        self.logger.callback = self.newDataCallback
        self.logger.clearCallback = self.clearData
        self.logger.stopDeviceCallback = self.remoteDeviceStop
        self.logger.startDeviceCallback = self.remoteDeviceStart
        self.logger.recordingLengthChangedCallback = self.loggerChangedAlert
        self.logger.reloadDevicesCallback = self.reloadDevicesCallback.emit
        self.reloadDevicesCallback.connect(self.reloadDevices)
        self.logger.reloadDevicesRAWCallback = self.reloadDevicesRAW
        self.logger.reloadSignalsGUICallback = self.reloadSignals

        self.darkmode = self.config['GUI']['darkmode']
        # self.signalTimeOut = self.config['GUI']['signalInactivityTimeout']

        self.initToolBar()
        self.connectButtons()
        self.initDeviceWidget()
        self.initPluginsWidget()
        self.initTrayIcon()
        self.initEventsWidget()

        self.logger.scriptExecutedCallback = self.scriptWidget.executedCallback
        self.logger.handleScriptCallback = self.scriptWidget.triggeredScriptCallback
        self.logger.newEventCallback = self.eventWidget.update
        if self.logger.database is not None:
            self.logger.database.connect_callbacks()

        if self.config['postgresql']['active']:
            if self.logger.database.status != 'connected':
                pyqtlib.info_message(translate('RTOC', 'Database error'), translate('RTOC', 'Could not connect to PostgreSQL database.'),
                                     translate('RTOC', 'Please adjust the PostgreSQL options in the settings and restart RTOC afterwards.'))
        else:
            # self.pullFromDatabaseButton.hide()
            # self.pushToDatabaseButton.hide()
            # self.exportDatabaseButton.hide()
            self.menuDatenbank.hide()
        # if not self.config['GUI']['pluginsWidget']:

        if not self.config['GUI']['scriptWidget']:
            self.scriptDockWidget.hide()
        if not self.config['GUI']['deviceWidget']:
            self.deviceWidget.hide()
        if not self.config['GUI']['deviceRAWWidget']:
            self.deviceRAWWidget.hide()
        if not self.config['GUI']['eventWidget']:
            self.eventWidgets.hide()
        # self.deviceRAWWidget.hide()
        self.actionWebsocketServer.setChecked(self.config['websocket']['active'])
        self.actionTelegramBot_2.setChecked(self.config['telegram']['active'])
        self.actionBotToken_2.setText(self.config['telegram']['token'])
        if self.config['websocket']['password'] == '':
            self.actionWebsocketPassword.setText(translate('RTOC', 'Password protection: Off'))
        else:
            self.actionWebsocketPassword.setText(translate('RTOC', 'Password protection: On'))
        self.actionWebsocketPort.setText(translate('RTOC', 'Port: {}').format(self.config['websocket']['port']))
        self.updateLabels()
        if self.config['GUI']['restoreWidgetPosition']:
            self.readSettings()

        self.loadSession(self.config['global']['documentfolder']+'/restore.json', True)
        self.pluginsWidget.hide()

        self.importer = RTOC_Import.RTOC_Import('', self, self.importCallback)

        self.remoteHostWidgets = []

        if not self.config['GUI']['restoreWidgetPosition']:
            self.tabifyDockWidget(self.graphWidget, self.eventWidgets)
            self.tabifyDockWidget(self.graphWidget, self.scriptDockWidget)
            self.tabifyDockWidget(self.deviceWidget, self.deviceRAWWidget)
            self.graphWidget.show()
            self.graphWidget.raise_()
            self.deviceWidget.show()
            self.deviceWidget.raise_()

    def loggerChangedAlert(self, devicename, signalname, length):
        self.maxLengthSpinBox.setValue(length)
        pyqtlib.info_message(translate('RTOC', "Warning"), translate('RTOC', "Recording length changed to {}.").format(length), translate('RTOC', 'Signal: {}.{}').format(devicename, signalname))

    def loadPlotStyles(self):
        filename = self.config['global']['documentfolder']+"/plotStyles.json"
        if os.path.exists(filename):
            try:
                with open(filename, encoding="UTF-8") as jsonfile:
                    self.plotStyles = json.load(jsonfile, encoding="UTF-8")
            except Exception:
                logging.debug(traceback.format_exc())
                self.plotStyles = {}

        else:
            self.plotStyles = {}

    def savePlotStyles(self):
        with open(self.config['global']['documentfolder']+"/plotStyles.json", 'w', encoding="utf-8") as fp:
            json.dump(self.plotStyles, fp,  sort_keys=False, indent=4, separators=(',', ': '))

    def initToolBar(self):
        sp = QtWidgets.QWidget()
        sp.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.toolBar.addWidget(sp)
        self.toolBar.addWidget(self.label_2)
        self.toolBar.addWidget(self.maxLengthSpinBox)

        self.toolBar.addWidget(sp)
        self.toolBar.addSeparator()
        self.toolBar.addWidget(self.clearButton)
        self.toolBar.addWidget(self.createGraphButton)

    def initTrayIcon(self):
        show_action = QtWidgets.QAction(translate('RTOC', "Maximize"), self)
        show_action.triggered.connect(self.show)
        self.hide_action = QtWidgets.QAction(translate('RTOC', "Run in background"), self)
        self.hide_action.setCheckable(True)
        self.hide_action.setChecked(self.config['GUI']['systemTray'])
        self.hide_action.triggered.connect(self.toggleSystemTray)
        self.websocket_action = QtWidgets.QAction(translate('RTOC', "Websocket Server"), self)
        self.websocket_action.setCheckable(True)
        self.websocket_action.setChecked(self.config['websocket']['active'])
        self.websocket_action.triggered.connect(self.toggleWebsocketServer)
        quit_action = QtWidgets.QAction(translate('RTOC', "Quit"), self)
        quit_action.triggered.connect(self.forceClose)

        tray_menu = QtWidgets.QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(self.hide_action)
        tray_menu.addAction(self.websocket_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.systemTrayAction.setChecked(self.config['GUI']['systemTray'])
        self.actionWebsocketServer.setChecked(self.config['websocket']['active'])

    def reloadDevicesRAW(self):
        self.updateDeviceRAW()

    def reloadDevices(self):
        self.logger.getDeviceList()
        self.initDeviceWidget()
        self.updateDeviceRAW()

    def reloadSignals(self):
        plotted_ids = []
        for window in self.plotWidgets:
            for widget in window.signalObjects:
                plotted_ids.append(widget.id)
        for sigID in self.logger.database.signals().keys():
            if sigID not in plotted_ids:
                devicename, signalname = self.logger.database.getSignalName(sigID)
                dataunit = self.logger.database._signals[sigID][4]
                self.addNewSignal(id, devicename, signalname, dataunit)

    def initDeviceWidget(self):
        donotreloadplugins = []
        for i in reversed(range(self.deviceLayout.count())):
            if not self.deviceLayout.itemAt(i).widget().isChecked() or ':' in self.deviceLayout.itemAt(i).widget().text():
                self.deviceLayout.itemAt(i).widget().setParent(None)
            else:
                donotreloadplugins.append(self.deviceLayout.itemAt(i).widget().text())

        for plugin in self.logger.devicenames.keys():
            if plugin not in donotreloadplugins:
                button = QtWidgets.QToolButton()
                button.setText(plugin)
                button.setCheckable(True)

                sizePolicy = QtGui.QSizePolicy(
                    QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
                sizePolicy.setHorizontalStretch(0)
                sizePolicy.setVerticalStretch(0)
                button.setSizePolicy(sizePolicy)

                button.clicked.connect(partial(self.toggleDevice, plugin, button))
                self.deviceLayout.addWidget(button)

                if self.logger.pluginStatus[plugin] is True:
                    button.setChecked(True)

        for plugin in self.logger.remote.devicenames.keys():
            if plugin not in donotreloadplugins:
                button = QtWidgets.QToolButton()
                button.setText(plugin)
                button.setCheckable(True)

                sizePolicy = QtGui.QSizePolicy(
                    QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
                sizePolicy.setHorizontalStretch(0)
                sizePolicy.setVerticalStretch(0)
                button.setSizePolicy(sizePolicy)
                button.setStyleSheet("background-color: rgb(13, 71, 97);")

                if self.logger.remote.pluginStatus[plugin] is True:
                    button.setChecked(True)

                name = plugin.split(':')
                button.clicked.connect(
                    partial(self.logger.remote.toggleDevice, name[0], name[1], button))
                self.deviceLayout.addWidget(button)

    def initPluginsWidget(self):
        self.pluginsBox.removeItem(0)

    def initScriptWidget(self):
        self.scriptWidget = ScriptWidget(self.logger)
        self.scriptLayout.addWidget(self.scriptWidget)

    def initPlotWidgets(self):
        self.activePlotWidgetIndex = 0
        self.plotWidgets = []

    def initEventsWidget(self):
        self.eventWidget = EventWidget(self, self.logger)
        self.eventLayout.addWidget(self.eventWidget)

    def newPlotWidget(self):
        self.activePlotWidgetIndex = len(self.plotWidgets)
        if self.activePlotWidgetIndex == 0:
            plotWidget = RTPlotWidget(self.logger, self, 0)
            self.plotWidgets.append(plotWidget)
            self.plotLayout.addWidget(self.plotWidgets[self.activePlotWidgetIndex].widget)
            self.plotWidgets[self.activePlotWidgetIndex].droppedTree.connect(self.signalsDropped)
        else:
            plotWidget = _SubWindow(self.logger, self, self.activePlotWidgetIndex,
                                   "Graph "+str(len(self.plotWidgets)+1))
            self.plotWidgets.append(plotWidget)
            self.plotWidgets[self.activePlotWidgetIndex].widget.droppedTree.connect(
                self.signalsDropped)

    def signalsDropped(self, dicti):
        for idx, item in enumerate(dicti["signalObjects"]):
            self.moveSignal(dicti["oldWidget"], dicti["newWidget"], item)

    def moveSignal(self, oldIdx, newIdx, signalItem):
        if oldIdx != newIdx:
            if signalItem.childCount() == 0:
                signalObject = self.plotWidgets[oldIdx].treeWidget.itemWidget(signalItem, 0)
                signalLabel = self.plotWidgets[oldIdx].treeWidget.itemWidget(signalItem, 1)
                if signalObject is not None and signalLabel is not None:
                    self.plotWidgets[oldIdx].deleteSignal(
                        signalObject.id, signalObject.devicename, signalObject.signalname)
                    self.plotWidgets[newIdx].addSignal(
                        signalObject.devicename, signalObject.signalname, signalObject.id, signalObject.unit)
                self._drag_info = {"oldWidget": "", "newWidget": "", "signalObjects": []}
            else:
                while signalItem.childCount() != 0:
                    self.moveSignal(oldIdx, newIdx, signalItem.child(0))

    def deletePlotWidget(self, id):
        if self.activePlotWidgetIndex == id:
            self.activePlotWidgetIndex = 0
        for idx, p in enumerate(self.plotWidgets):
            if idx != 0:
                if p.widget.id == id:
                    self.plotWidgets.pop(idx)
        # for idx, widget in enumerate(self.plotWidgets):
        #     widget.id = idx

    def updateLabels(self):
        self.maxLengthSpinBox.setValue(self.logger.config['global']['recordLength'])

    def remoteDeviceStop(self, devicename):
        items = (self.deviceLayout.itemAt(i) for i in range(self.deviceLayout.count()))
        for w in items:
            if w.widget().text() == devicename:
                w.widget().setChecked(False)

    def remoteDeviceStart(self, devicename):
        items = (self.deviceLayout.itemAt(i) for i in range(self.deviceLayout.count()))
        for w in items:
            if w.widget().text() == devicename:
                w.widget().setChecked(True)

    def toggleDevice(self, deviceName, button):
        if not button.isChecked():
            ok = self.logger.stopPlugin(deviceName, False)
            button.setMenu(None)
            if ok:
                for idx in range(self.pluginsBox.count()):
                    if self.pluginsBox.itemText(idx) == deviceName:
                        self.pluginsBox.removeItem(idx)
                        break
                if self.pluginsBox.count() == 0:
                    self.pluginsWidget.hide()
            else:
                button.setChecked(True)
        else:
            ok, errors = self.logger.startPlugin(deviceName, False)
            if ok:
                try:
                    invert_op = getattr(self.logger.pluginObjects[deviceName], "loadGUI", None)
                    if callable(invert_op):
                        widget = self.logger.pluginObjects[deviceName].loadGUI()
                        if self.logger.pluginObjects[deviceName].smallGUI is None:
                            widget.setWindowTitle(deviceName)
                            widget.show()
                        elif self.logger.pluginObjects[deviceName].smallGUI is True:
                            button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
                            button.setMenu(QtWidgets.QMenu(button))
                            action = QtWidgets.QWidgetAction(button)
                            action.setDefaultWidget(widget)
                            button.menu().addAction(action)
                        else:
                            self.pluginsBox.addItem(widget, deviceName)
                            if not self.pluginsWidget.isVisible():
                                self.pluginsWidget.show()
                except Exception:
                    tb = traceback.format_exc()
                    logging.debug(tb)
                    pyqtlib.info_message(translate('RTOC', "Error"), translate("RTOC",
                        "Error loading plugin-GUI. Please check your code."), tb)
            else:
                pyqtlib.info_message(translate('RTOC', "Error"), translate("RTOC",
                    "Error loading plugin. Please make sure the plugin is correct."), errors)
                button.setChecked(False)
        self.scriptWidget.updateListWidget()
        self.updateDeviceRAW()

    def addNewSignal(self, id, devicename, signalname, dataunit):
        self.plotWidgets[self.activePlotWidgetIndex].addSignal2.emit(
            devicename, signalname, id, dataunit)
        self.scriptWidget.updateListWidget()

    def newDataCallback(self, devicename, signalname):
        # devicename, signalname = self.logger.latestSignal
        for plot in self.plotWidgets:
            for signal in plot.signalObjects:
                if signal.devicename == devicename and signal.signalname == signalname:
                    signal.newDataIncoming()
                    return
        # self.newSignalThread.start()

    def clearData(self):
        self.scriptWidget.clear()
        for p in self.plotWidgets:
            p.clear()

    def loadSession(self, fileName="restore.json", clear=None):
        if clear is None:
            clear = pyqtlib.alert_message(translate('RTOC', 'Merge sessions'), translate('RTOC', 'Do you want to remove the current session?'), translate("RTOC",
                'Unsaved data will be lost.'), '', translate('RTOC', 'Yes'), translate('RTOC', 'No'))
        if clear:
            self.clearData()
        ok = self.logger.database.restoreJSON(fileName, clear)
        if type(ok) == list:
            self.openScripts(ok)
            # self.scriptWidget.openFile(self.config["lastScript"])
        # else:
            # self.scriptWidget.openScript("", "neu")

    def openScripts(self, scripts):
        for script in scripts:
            if type(script) == list:
                if len(script) == 2:
                    self.scriptWidget.openScript(script[0], script[1])
                elif len(script) == 3:
                    self.scriptWidget.openScript(script[0], script[1], script[2])
            elif type(script) == str:
                self.scriptWidget.openFile(script)

    def forceClose(self):
        self.forceQuit = True
        self.close()

    def closeEvent(self, event):  # , *args, **kwargs):
        if self.systemTrayAction.isChecked() and not self.forceQuit:
            self.tray_icon.show()
            event.ignore()
            self.hide()
            t = translate('RTOC', " is running in the background.")
            self.tray_icon.showMessage(
                translate('RTOC', "RealTime OpenControl"),
                t,
                self.app_icon,
                2000
            )
        else:
            self.savePlotStyles()
            if len(self.logger.database.signals()) > 0 and not self.logger.config['postgresql']['active']:
                ok = pyqtlib.tri_message(
                    translate('RTOC', "Save"), translate('RTOC', "Do you want to save the current session?"), "")
            else:
                ok = False
            if ok is not None:
                if ok is True:
                    self.logger.database.exportJSON(
                        self.config['global']['documentfolder']+"/restore.json", True)
                elif ok is False:
                    if os.path.exists(self.config['global']['documentfolder']+"/restore.json"):
                        os.remove(self.config['global']['documentfolder']+"/restore.json")
                logging.info('Goodbye')
                self.hide()
                self.run = False
                if self.config['GUI']['restoreWidgetPosition']:
                    self.saveSettings()
                self.scriptWidget.close()
                self.importer.close()
                for plot in self.plotWidgets:
                    plot.close()
                    super(RTOC, self).closeEvent(event)
                self.logger.save_config()
                self.logger.stop()
            else:
                event.ignore()

    def readSettings(self):
        self.settings = QtCore.QSettings('user', 'RTOC')
        if not self.settings.value("geometry") is None:
            self.restoreGeometry(self.settings.value("geometry", ""))
        if not self.settings.value("windowState") is None:
            self.restoreState(self.settings.value("windowState"))

        if not self.settings.value("devicesGeometry") is None:
            self.deviceWidget.resize(self.settings.value("devicesGeometry", ""))

    def saveSettings(self):
        if self.settings:
            self.settings.setValue('geometry', self.saveGeometry())
            self.settings.setValue('windowState', self.saveState())

            self.settings.setValue('devicesGeometry', self.deviceWidget.size())

    def center(self):
        qr = self.frameGeometry()
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def mousePressEvent(self, event):
        self.activePlotWidgetIndex = 0
        super(RTOC, self).mousePressEvent(event)

    def dragEnterEvent(self, e):
        self.toggleDragView(True)
        if e.mimeData().hasUrls or e.mimeData().hasText:
            e.accept()
            elementType, elementContent = lib.identifyElementTypeFromString(e.mimeData().text())
            if elementContent == '':
                text = "Dateityp nicht erkannt"
                e.ignore()
            else:
                text = "Datentyp erkannt: "+elementType  # +": "+str(elementContent)
            self.drag_content.setText(text)
        else:
            e.ignore()
            self.drag_content.setText("Unbekannter Inhalt")

    def dragLeaveEvent(self, e):
        self.toggleDragView(False)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls or e.mimeData().hasImage or e.mimeData().hasText:
            e.accept()
        else:
            e.ignore()

    def loadWav(self, filename):
        try:
            from scipy.io import wavfile
            fs, data = wavfile.read(filename)
            text, ok = pyqtlib.text_message(self, translate('RTOC', "Enter signalname"), translate("RTOC",
                "Specify a name for the signal to be imported."), os.path.splitext(str(filename))[0].split("/")[-1]+'.Signal')
            if ok:
                y = list(data)
                # x = list(range(y))/fs
                x = [v/fs for v in list(range(len(y)))]
                names = text.split('.')
                if len(names) < 2:
                    names.append('Signal')
                self.logger.database.plot(x, y, sname=names[1], dname=names[0])
        except Exception:
            tb = traceback.format_exc()
            logging.debug(tb)
            pyqtlib.info_message(translate('RTOC', "Error"), translate('RTOC', "File {} could not be opened.").format(filename), translate('RTOC', "This file may be damaged."))

    def dropEvent(self, e):
        if e.mimeData().hasText:
            elementType, elementContent = lib.identifyElementTypeFromString(e.mimeData().text())
            if os.name != 'nt':
                elementContent = '/'+elementContent
            if elementType == 'pfad':
                if elementContent.endswith('.json'):
                    self.loadSession(elementContent)
                elif elementContent.endswith('.wav') or elementContent.endswith('.wave'):
                    self.loadWav(elementContent)
                else:
                    self.importer.loadCsv(elementContent)
                    self.importer.show()
            else:
                self.importer.loadCsvStr(e.mimeData().text())
                self.importer.show()
        else:
            e.ignore()
        self.toggleDragView(False)

    def toggleDragView(self, status=True):
        if status:
            # logging.info('Drag enabled')
            self.drag_content.show()
        else:
            # logging.info('Drag disabled')
            self.drag_content.hide()


if __name__ == '__main__':
    # main()
    sys.exit()
