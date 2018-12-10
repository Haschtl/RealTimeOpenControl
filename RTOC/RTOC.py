# -*- encoding: utf-8 -*-

import sys
import os
from PyQt5 import QtCore
from PyQt5 import uic
from PyQt5 import QtWidgets, QtGui
from functools import partial
import traceback
import json
import getopt

try:
    from . import RTLogger
    from .data.lib import pyqt_customlib as pyqtlib
    from .data.scriptWidget import ScriptWidget
    from .data.eventWidget import EventWidget
    from .data.RTPlotWidget import RTPlotWidget
    from .data.Actions import Actions
except ImportError:
    import RTLogger
    from data.lib import pyqt_customlib as pyqtlib
    from data.scriptWidget import ScriptWidget
    from data.eventWidget import EventWidget
    from data.RTPlotWidget import RTPlotWidget
    from data.Actions import Actions

if os.name == 'nt':
    import ctypes
    myappid = 'mycompany.myproduct.subproduct.version'  # arbitrary string
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

LINECOLORS = ['r', 'g', 'b', 'c', 'm', 'y', 'w']


class SubWindow(QtWidgets.QMainWindow):
    def __init__(self, logger, selfself, idx, title="SubWindow"):
        super(SubWindow, self).__init__()  # logger, selfself, idx)
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

    def closeEvent(self, event, *args, **kwargs):
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
        super(SubWindow, self).closeEvent(event)

    def clear(self):
        self.widget.clear()

    def updatePlot(self):
        self.widget.updatePlot()

    def stop(self):
        self.widget.stop()

    def deleteSignal(self, idx, devicename, signalname):
        self.widget.deleteSignal(idx, devicename, signalname)

    def removeSignal(self, idx, devicename, signalname):
        self.widget.removeSignal(idx, devicename, signalname)

    def addSignalRAW(self, signalObject):
        self.widget.addSignalRAW(signalObject)

    def addSignal(self, devicename, signalname, id, unit):
        self.widget.addSignal(devicename, signalname, id, unit)


class RTOC(QtWidgets.QMainWindow, Actions):
    def __init__(self):
        super(RTOC, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/data/ui/rtoc.ui", self)
        self.app_icon = QtGui.QIcon(packagedir+"/data/icon.png")
        self.setWindowIcon(self.app_icon)
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.app_icon)
        self.tray_icon.activated.connect(self.systemTrayClickAction)

        self.forceQuit = False
        self.initPlotWidgets()

        self.logger = RTLogger.RTLogger()
        self.config = self.logger.config
        self.loadPlotStyles()
        self.initScriptWidget()
        self.newPlotWidget()
        self.logger.tr = self.tr

        for id in self.logger.signalIDs:
            name = self.logger.getSignalNames(id)
            dataunit = self.logger.getSignalUnits(id)
            self.addNewSignal(id, name[0], name[1], dataunit)

        self.logger.newSignalCallback = self.addNewSignal
        self.logger.callback = self.newDataCallback
        self.logger.clearCallback = self.clearData
        self.logger.stopDeviceCallback = self.remoteDeviceStop
        self.logger.startDeviceCallback = self.remoteDeviceStart

        self.darkmode = self.config["darkmode"]
        self.signalTimeOut = self.config["signalInactivityTimeout"]

        self.initToolBar()
        self.connectButtons()
        self.initDeviceWidget()
        self.initPluginsWidget()
        self.initTrayIcon()
        self.initEventsWidget()

        self.logger.scriptExecutedCallback = self.scriptWidget.executedCallback
        self.logger.handleScriptCallback = self.scriptWidget.triggeredScriptCallback
        self.logger.newEventCallback = self.eventWidget.update
        # if not self.config["pluginsWidget"]:
        self.pluginsWidget.hide()
        if not self.config["scriptWidget"]:
            self.scriptDockWidget.hide()
        if not self.config["deviceWidget"]:
            self.deviceWidget.hide()
        if not self.config["eventWidget"]:
            self.eventWidgets.hide()
        self.actionTCPServer.setChecked(self.config["tcpserver"])
        self.HTMLServerAction.setChecked(self.config["rtoc_web"])
        self.actionTelegramBot.setChecked(self.config["telegram_bot"])
        self.actionBotToken.setText(self.config['telegram_token'])
        if self.config['tcppassword']=='':
            self.actionTCPPassword.setText(self.tr('Passwort-Schutz: Aus'))
        else:
            self.actionTCPPassword.setText(self.tr('Passwort-Schutz: An'))

        self.updateLabels()
        self.readSettings()

        self.loadSession()

    def loadPlotStyles(self):
        filename = self.config['documentfolder']+"/plotStyles.json"
        if os.path.exists(filename):
            try:
                with open(filename, encoding="UTF-8") as jsonfile:
                    self.plotStyles = json.load(jsonfile, encoding="UTF-8")
            except:
                self.plotStyles = {}
        else:
            self.plotStyles = {}

    def savePlotStyles(self):
        with open(self.config['documentfolder']+"/plotStyles.json", 'w', encoding="utf-8") as fp:
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
        show_action = QtWidgets.QAction(self.tr("Anzeigen"), self)
        show_action.triggered.connect(self.show)
        self.hide_action = QtWidgets.QAction(self.tr("Im Hintergrund laufen"), self)
        self.hide_action.setCheckable(True)
        self.hide_action.setChecked(self.config['systemTray'])
        self.hide_action.triggered.connect(self.toggleSystemTray)
        self.tcp_action = QtWidgets.QAction(self.tr("TCP Server"), self)
        self.tcp_action.setCheckable(True)
        self.tcp_action.setChecked(self.config['tcpserver'])
        self.tcp_action.triggered.connect(self.toggleTcpServer)
        quit_action = QtWidgets.QAction(self.tr("Beenden"), self)
        quit_action.triggered.connect(self.forceClose)

        tray_menu = QtWidgets.QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(self.hide_action)
        tray_menu.addAction(self.tcp_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.systemTrayAction.setChecked(self.config["systemTray"])
        self.actionTCPServer.setChecked(self.config["tcpserver"])

    def initDeviceWidget(self):
        for plugin in self.logger.devicenames.keys():
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

            if self.logger.pluginStatus[plugin] == True:
                button.setChecked(True)

    def initPluginsWidget(self):
        self.pluginsBox.removeItem(0)

    def initScriptWidget(self):
        self.scriptWidget = ScriptWidget(self.logger)
        self.scriptLayout.addWidget(self.scriptWidget)

    def initPlotWidgets(self):
        self.activePlotWidgetIndex = 0
        self.plotWidgets = []

    def initEventsWidget(self):
        self.eventWidget = EventWidget(self.logger)
        self.eventLayout.addWidget(self.eventWidget)

    def newPlotWidget(self):
        self.activePlotWidgetIndex = len(self.plotWidgets)
        if self.activePlotWidgetIndex == 0:
            plotWidget = RTPlotWidget(self.logger, self, 0)
            self.plotWidgets.append(plotWidget)
            self.plotLayout.addWidget(self.plotWidgets[self.activePlotWidgetIndex].widget)
            self.plotWidgets[self.activePlotWidgetIndex].droppedTree.connect(self.signalsDropped)
        else:
            plotWidget = SubWindow(self.logger, self, self.activePlotWidgetIndex,
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
        self.plotWidgets.pop(id)
        for idx, widget in enumerate(self.plotWidgets):
            widget.id = idx

    def updateLabels(self):
        self.maxLengthSpinBox.setValue(self.logger.maxLength)

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
            ok, errors = self.logger.startPlugin(deviceName, None, False)
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
                except:
                    tb = traceback.format_exc()
                    pyqtlib.info_message(self.tr("Fehler"), self.tr(
                        "Fehler beim Laden der Geräte GUI\nBitte Code überprüfen."), tb)
            else:
                pyqtlib.info_message(self.tr("Fehler"), self.tr(
                    "Fehler beim Laden des Geräts\nBitte stellen Sie sicher, dass das Gerät verbunden ist."), errors)
                button.setChecked(False)
        self.scriptWidget.updateListWidget()

    def addNewSignal(self, id, devicename, signalname, dataunit):
        self.plotWidgets[self.activePlotWidgetIndex].addSignal2.emit(
            devicename, signalname, id, dataunit)
        self.scriptWidget.updateListWidget()

    def newDataCallback(self):
        devicename, dataname = self.logger.latestSignal
        for plot in self.plotWidgets:
            for signal in plot.signalObjects:
                if signal.devicename == devicename and signal.signalname == dataname:
                    signal.newDataIncoming()
                    return
        # self.newSignalThread.start()

    def clearData(self):
        self.scriptWidget.clear()
        for p in self.plotWidgets:
            p.clear()

    def loadSession(self, fileName="restore.json"):
        self.clearData()
        ok = self.logger.restoreJSON(fileName)
        if ok:
            self.scriptWidget.openFile(self.config["lastScript"])
        else:
            self.scriptWidget.openScript("", "neu")

    def forceClose(self):
        self.forceQuit = True
        self.close()

    def closeEvent(self, event):  # , *args, **kwargs):
        if self.systemTrayAction.isChecked() and not self.forceQuit:
            self.tray_icon.show()
            event.ignore()
            self.hide()
            t = self.tr("läuft im Hintergrund weiter und zeichnet Messwerte auf")
            self.tray_icon.showMessage(
                self.tr("RealTime OpenControl"),
                t,
                self.app_icon,
                2000
            )
        else:
            self.savePlotStyles()
            if len(self.logger.signals) >= 0 and self.logger.signalNames != [['RTOC', '']]:
                ok = pyqtlib.tri_message(
                    self.tr("Speichern"), self.tr("Wollen Sie die aktuelle Sitzung speichern?"), "")
            else:
                ok = False
            if ok is not None:
                if ok == True:
                    self.logger.exportJSON("restore")
                elif ok == False:
                    if os.path.exists(self.config['documentfolder']+"/restore.json"):
                        os.remove(self.config['documentfolder']+"/restore.json")
                print('Goodbye')
                self.run = False
                self.saveSettings()
                self.scriptWidget.close()
                for plot in self.plotWidgets:
                    plot.close()
                self.logger.save_config()
                self.logger.stop()
                super(RTOC, self).closeEvent(event)
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


class RTOC_TCP(QtWidgets.QMainWindow):
    def __init__(self):
        super(RTOC_TCP, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        self.logger = RTLogger.RTLogger(True)
        self.config = self.logger.config
        app_icon = QtGui.QIcon(packagedir+"/data/icon.png")
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        self.tray_icon.setIcon(app_icon)
        self.tray_icon.activated.connect(self.systemTrayClickAction)

        quit_action = QtWidgets.QAction("Beenden", self)
        quit_action.triggered.connect(self.close)

        tray_menu = QtWidgets.QMenu()
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        t = "TCP-Server gestartet\nLäuft im Hintergrund"
        print(t)
        self.tray_icon.show()
        self.tray_icon.showMessage(
            "RealTime OpenControl",
            t,
            app_icon,
            2000
        )

    def systemTrayClickAction(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Context:
            print('clicked')

    def closeEvent(self, event):
        if len(self.logger.signals) != 0:
            ok = pyqtlib.tri_message(
                self.tr("Speichern"), self.tr("Wollen Sie die aktuelle Sitzung speichern?"), "")
        else:
            ok = False
        if ok is not None:
            if ok == True:
                self.logger.exportJSON("restore")
            elif ok == False:
                if os.path.exists(self.config['documentfolder']+"/restore.json"):
                    os.remove(self.config['documentfolder']+"/restore.json")
            print('Goodbye')
            # self.logger.save_config()
            self.logger.stop()
            super(RTOC_TCP, self).closeEvent(event)
        else:
            event.ignore()


def setStyleSheet(app, myapp):
    try:
        import qtmodern.styles
        import qtmodern.windows
        qtmodern.styles.dark(app)
        #mw = qtmodern.windows.ModernWindow(myapp)
        mw = myapp
        return app, mw
    except ImportError:
        tb = traceback.format_exc()
        print(tb)
        print("New Style not installed")
        with open("/data/ui/darkmode.html", 'r') as myfile:
            stylesheet = myfile.read().replace('\n', '')
        app.setStyleSheet(stylesheet)
        return app, myapp


def setLanguage(app):
    try:
        userpath = os.path.expanduser('~/Documents/RTOC')
        with open(userpath+"/config.json", encoding="UTF-8") as jsonfile:
            config = json.load(jsonfile, encoding="UTF-8")
    except:
        config={'language':'en'}
    if config['language'] == 'en':
        translator = QtCore.QTranslator()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        translator.load(packagedir+"/lang/en_en.qm")
        app.installTranslator(translator)
    # more info here: http://kuanyui.github.io/2014/09/03/pyqt-i18n/
    # generate translationfile: % pylupdate5 RTOC.py -ts lang/de_de.ts
    # compile translationfile: % lrelease-qt5 lang/de_de.ts
    # use self.tr("TEXT TO TRANSLATE") in the code


def main():
    opts, args = getopt.getopt(sys.argv[1:], "hsr:", ["remote="])
    if len(opts) == 0:
        startRTOC()
    else:
        for opt, arg in opts:
            if opt == '-h':
                print(
                    'RTOC.py [-h, -s] [-r <Remoteadress>]\n -h: Hilfe\n-s: TCP-Server ohne GUI\n-r <Remoteadresse>: TCP-Client zu RTOC-Server')
                sys.exit()
            elif opt == '-s':
                runInBackground()
                sys.exit(0)
            elif opt in ("-r", "--remote"):
                remotepath = arg
                startRemoteRTOC(remotepath)


def runInBackground():
    app = QtWidgets.QApplication(sys.argv)
    myapp = RTOC_TCP()
    app, myapp = setStyleSheet(app, myapp)

    app.exec_()


def startRemoteRTOC(remotepath):
    app = QtWidgets.QApplication(sys.argv)
    try:
        userpath = os.path.expanduser('~/Documents/RTOC')
        with open(userpath+"/config.json", encoding="UTF-8") as jsonfile:
            config = json.load(jsonfile, encoding="UTF-8")
    except:
        config={'language':'en'}
    if config['language'] == 'en':
        print("English language selected")
        translator = QtCore.QTranslator()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        translator.load(packagedir+"/lang/en_en.qm")
        app.installTranslator(translator)
    myapp = RTOC()
    myapp.config["tcpserver"] = True

    app, myapp = setStyleSheet(app, myapp)
    print(remotepath)
    myapp.show()
    myapp.pluginsWidget.show()
    myapp.scriptDockWidget.hide()
    myapp.deviceWidget.hide()
    myapp.eventWidgets.show()
    button = QtWidgets.QPushButton()
    button.setCheckable(True)
    button.setChecked(True)
    myapp.toggleDevice('NetWoRTOC', button)
    myapp.logger.getPlugin('NetWoRTOC').start(remotepath)
    myapp.logger.getPlugin('NetWoRTOC').widget.comboBox.setCurrentText(remotepath)
    myapp.logger.getPlugin('NetWoRTOC').run = False
    myapp.logger.getPlugin('NetWoRTOC').__openConnectionCallback()
    #myapp.logger.getPlugin('NetWoRTOC').widget.streamButton.setChecked(True)
    app.exec_()


def startRTOC():
    app = QtWidgets.QApplication(sys.argv)
    try:
        userpath = os.path.expanduser('~/Documents/RTOC')
        with open(userpath+"/config.json", encoding="UTF-8") as jsonfile:
            config = json.load(jsonfile, encoding="UTF-8")
    except:
        config={'language':'en'}
    if config['language'] == 'en':
        print("English language selected")
        translator = QtCore.QTranslator()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        translator.load(packagedir+"/lang/en_en.qm")
        app.installTranslator(translator)
        # more info here: http://kuanyui.github.io/2014/09/03/pyqt-i18n/
        # generate translationfile: % pylupdate5 RTOC.py -ts lang/de_de.ts
        # compile translationfile: % lrelease-qt5 lang/de_de.ts
        # use self.tr("TEXT TO TRANSLATE") in the code
    myapp = RTOC()
    app, myapp = setStyleSheet(app, myapp)

    myapp.show()
    app.exec_()


if __name__ == '__main__':
    main()
    sys.exit()
