# -*- encoding: utf-8 -*-

import sys
import os
from PyQt5 import QtCore
from PyQt5 import uic
from PyQt5 import QtWidgets, QtGui
from functools import partial
import time
import traceback
import json

import data.lib.pyqt_customlib as pyqtlib
import RTLogger
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


class SubWindow(QtWidgets.QMainWindow):#, RTPlotWidget):
    def __init__(self, logger, selfself, idx, title="SubWindow"):
        super(SubWindow, self).__init__()#logger, selfself, idx)
        self.widget = RTPlotWidget(logger, selfself, idx)
        #super(RTPlotWidget, self).__init__(logger, selfself, idx)
        _DOCK_OPTS = QtGui.QMainWindow.AnimatedDocks
        _DOCK_OPTS |= QtGui.QMainWindow.AllowNestedDocks
        _DOCK_OPTS |= QtGui.QMainWindow.AllowTabbedDocks
        self.self=selfself
        self.setDockOptions(_DOCK_OPTS)
        self.setCentralWidget(self.widget.widget)
        self.setWindowTitle(title)
        app_icon = QtGui.QIcon("data/icon.png")
        self.setWindowIcon(app_icon)
        self.show()
        self.signalObjects = self.widget.signalObjects
        self.treeWidget = self.widget.treeWidget
    # def closeEvent(self, event, *args, **kwargs):
    #     super(SubWindow, self).closeEvent(event)

    def closeEvent(self, event, *args, **kwargs):
        #print("Closing plot "+str(self.widget.id))
        if self.widget.id == 0:
            self.widget.stop()
        else:
            for signalObject in self.widget.signalObjects:
                #self.self.plotWidgets[0].addSignalRAW(signalObject)
                self.self.plotWidgets[0].addSignal(signalObject.devicename, signalObject.signalname, signalObject.id, signalObject.unit)
            while len(self.widget.signalObjects)!=0:
                signalObject = self.widget.signalObjects[0]
                self.widget.deleteSignal(signalObject.id, signalObject.devicename, signalObject.signalname)
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

class Callback(QtCore.QThread):
    received = QtCore.pyqtSignal(int, str, str, str)

    def __init__(self, idx=0, devicename="", dataname="", unit=""):
        super(Callback, self).__init__()
        self.idx = idx
        self.devicename = devicename
        self.dataname = dataname
        self.unit = unit

    def setValues(self, idx, devicename, dataname, unit):
        self.idx = idx
        self.devicename = devicename
        self.dataname = dataname
        self.unit = unit
        self.run()

    def run(self):
        # print(received)
        self.received.emit(self.idx, self.devicename, self.dataname, self.unit)

class EventCallback(QtCore.QThread):
    received = QtCore.pyqtSignal(float, str, str, str, int)

    def __init__(self):
        super(EventCallback, self).__init__()
        self.time = 0
        self.text = ''
        self.dname = ''
        self.sname = ''
        self.priority = 0

    def setValues(self, time, text, dname, sname, priority):
        self.time = time
        self.text = text
        self.dname = dname
        self.sname = sname
        self.priority = priority
        self.run()

    def run(self):
        # print(received)
        self.received.emit(self.time, self.text, self.dname, self.sname, self.priority)

class Updater(QtCore.QThread):
    received = QtCore.pyqtSignal()

    def run(self):
        while True:
            time.sleep(0.1)
            self.received.emit()


class RTOC(QtWidgets.QMainWindow, Actions):
    def __init__(self):
        super(RTOC, self).__init__()
        uic.loadUi("data/ui/rtoc.ui", self)
        self.app_icon = QtGui.QIcon("data/icon.png")
        self.setWindowIcon(self.app_icon)
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        #self.tray_icon.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))
        self.tray_icon.setIcon(self.app_icon)
        self.tray_icon.activated.connect(self.systemTrayClickAction)

        self.logger = RTLogger.RTLogger()
        self.logger.tr = self.tr
        self.forceQuit = False
        self.newSignalThread = Callback(self)
        self.newSignalThread.received.connect(self.addNewSignal)
        # #self.newSignalThread.start()
        self.logger.newSignalCallback = self.newSignalThread.setValues
        #self.logger.newSignalCallback = self.newSignalThread
        self.logger.callback = self.newDataCallback
        self.logger.clearCallback = self.clearData
        self.config = self.logger.config
        self.loadPlotStyles()

        self.darkmode = self.config["darkmode"]
        self.signalTimeOut = self.config["signalInactivityTimeout"]

        self.initToolBar()
        self.connectButtons()
        self.initDeviceWidget()
        self.initPluginsWidget()
        self.initPlotWidgets()
        self.initScriptWidget()
        self.initTrayIcon()
        self.initEventsWidget()

        self.logger.scriptExecutedCallback = self.scriptWidget.executedCallback
        self.logger.handleScriptCallback = self.scriptWidget.triggeredScriptCallback


        self.newEventThread = EventCallback()
        self.newEventThread.received.connect(self.eventWidget.update)
        self.logger.newEventCallback = self.newEventThread.setValues

        if not self.config["pluginsWidget"]:
            self.pluginsWidget.hide()
        if not self.config["scriptWidget"]:
            self.scriptDockWidget.hide()
        if not self.config["signalsWidget"]:
            self.signalsWidget.hide()
        if not self.config["deviceWidget"]:
            self.deviceWidget.hide()
        if not self.config["eventWidget"]:
            self.eventWidgets.hide()
        if not self.config["tcpserver"]:
            self.TCPServerAction.setChecked(False)

        self.newPlotWidget()

        self.updateLabels()
        self.readSettings()

        self.loadSession()

    def loadPlotStyles(self):
        filename = "plotStyles.json"
        if os.path.exists(filename):
            with open(filename, encoding="UTF-8") as jsonfile:
                self.plotStyles = json.load(jsonfile, encoding="UTF-8")
        else:
            self.plotStyles = {}

    def savePlotStyles(self):
        with open("plotStyles.json", 'w', encoding="utf-8") as fp:
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
        quit_action = QtWidgets.QAction(self.tr("Beenden"), self)
        self.hide_action = QtWidgets.QAction(self.tr("Im Hintergrund laufen"), self)
        self.tcp_action = QtWidgets.QAction(self.tr("TCP Server"), self)
        self.hide_action.setCheckable(True)
        self.tcp_action.setCheckable(True)
        self.tcp_action.setChecked(self.config['systemTray'])
        self.hide_action.setChecked(self.config['tcpserver'])
        show_action.triggered.connect(self.show)
        self.hide_action.triggered.connect(self.trayToggleSystemTray)
        quit_action.triggered.connect(self.forceClose)
        self.tcp_action.triggered.connect(self.trayToggleTcpServer)
        tray_menu = QtWidgets.QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(self.hide_action)
        tray_menu.addAction(self.tcp_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.systemTrayAction.setChecked(self.config["systemTray"])

    def initDeviceWidget(self):
        for plugin in self.logger.devicenames:
            #button = QtWidgets.QCheckBox()
            button = QtWidgets.QToolButton()
            button.setText(plugin.replace("plugins.", ""))
            button.setCheckable(True)

            sizePolicy = QtGui.QSizePolicy(
                QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            # sizePolicy.setHeightForWidth(
            #    button.sizePolicy().hasHeightForWidth())
            button.setSizePolicy(sizePolicy)

            # button.setCheckable(True)
            button.clicked.connect(partial(self.toggleDevice, plugin, button))
            self.deviceLayout.addWidget(button)

    def initPluginsWidget(self):
        self.pluginsBox.removeItem(0)

    def initScriptWidget(self):
        self.scriptWidget = ScriptWidget(self.logger)
        self.scriptLayout.addWidget(self.scriptWidget)

    def initPlotWidgets(self):
        self.activePlotWidgetIndex = -1
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
            # plotWidget.show()
            self.plotWidgets[self.activePlotWidgetIndex].droppedTree.connect(self.signalsDropped)
        else:
            #dockwidget = QtWidgets.QDockWidget("Plot "+str(self.activePlotWidgetIndex), self.plotWidgets[self.activePlotWidgetIndex])
            #dockwidget = QtWidgets.QDialog("Plot "+str(len(self.plotWidgets)))
            plotWidget = SubWindow(self.logger, self, self.activePlotWidgetIndex,
                                   "Graph "+str(len(self.plotWidgets)+1))
            self.plotWidgets.append(plotWidget)
            self.plotWidgets[self.activePlotWidgetIndex].widget.droppedTree.connect(self.signalsDropped)


    def signalsDropped(self, dicti):
        for idx, item in enumerate(dicti["signalObjects"]):
            self.moveSignal(dicti["oldWidget"],dicti["newWidget"],item)

    def moveSignal(self, oldIdx, newIdx, signalItem):
        if oldIdx != newIdx:
            if signalItem.childCount()==0:
                #print("Moving signal from "+str(oldIdx)+" to "+str(newIdx))
                signalObject = self.plotWidgets[oldIdx].treeWidget.itemWidget(signalItem,0)
                signalLabel = self.plotWidgets[oldIdx].treeWidget.itemWidget(signalItem,1)
                if signalObject != None and signalLabel != None:
                    #self.plotWidgets[newIdx].addSignalRAW(signalObject)
                    self.plotWidgets[oldIdx].deleteSignal(signalObject.id, signalObject.devicename, signalObject.signalname)
                    self.plotWidgets[newIdx].addSignal(signalObject.devicename, signalObject.signalname, signalObject.id, signalObject.unit)
                self._drag_info = {"oldWidget":"", "newWidget":"", "signalObjects":[]}
            else:
                #print("Group moving: len "+str(signalItem.childCount()))
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

    def toggleDevice(self, deviceName, button):
        if not button.isChecked():
            #print("Closing Device connection: "+deviceName)
            ok = self.logger.stopPlugin(deviceName.replace("plugins.", ""))
            button.setMenu(None)
            if ok:
                for idx in range(self.pluginsBox.count()):
                    if self.pluginsBox.itemText(idx) == deviceName.replace("plugins.", ""):
                        self.pluginsBox.removeItem(idx)
                        break
                if self.pluginsBox.count() == 0:
                    self.pluginsWidget.hide()
            else:
                button.setChecked(True)
        else:
            #print("Loading Device connection: "+deviceName)
            ok, errors = self.logger.startPlugin(deviceName.replace("plugins.", ""))
            if ok:
                try:
                    invert_op = getattr(self.logger.pluginObjects[deviceName], "loadGUI", None)
                    if callable(invert_op):
                        widget = self.logger.pluginObjects[deviceName].loadGUI()
                        if self.logger.pluginObjects[deviceName].smallGUI is None:
                            #window = QtWidgets.QMainWindow()
                            #window.setCentralWidget(widget)
                            widget.setWindowTitle(deviceName.replace("plugins.", ""))
                            widget.show()
                        elif self.logger.pluginObjects[deviceName].smallGUI is True:
                            button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
                            button.setMenu(QtWidgets.QMenu(button))
                            action = QtWidgets.QWidgetAction(button)
                            action.setDefaultWidget(widget)
                            button.menu().addAction(action)
                        else:
                            self.pluginsBox.addItem(widget, deviceName.replace("plugins.", ""))
                            if not self.pluginsWidget.isVisible():
                                self.pluginsWidget.show()
                except:
                    tb = traceback.format_exc()
                    pyqtlib.info_message(self.tr("Fehler"), self.tr("Fehler beim Laden der Geräte GUI\nBitte Code überprüfen."),tb)
            else:
                pyqtlib.info_message(self.tr("Fehler"), self.tr("Fehler beim Laden des Geräts\nBitte stellen Sie sicher, dass das Gerät verbunden ist."),errors)
                button.setChecked(False)
        self.scriptWidget.updateListWidget()

    def addNewSignal(self, id, devicename, signalname, dataunit):
        #idx , devicename, signalname, dataunit = self.logger.newSignal
        self.plotWidgets[self.activePlotWidgetIndex].addSignal(
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
            self.scriptWidget.openScript("","neu")

    def forceClose(self):
        self.forceQuit = True
        self.close()

    def closeEvent(self, event):#, *args, **kwargs):
        if self.systemTrayAction.isChecked() and not self.forceQuit:
            self.tray_icon.show()
            event.ignore()
            self.hide()
            t=self.tr("läuft im Hintergrund weiter und zeichnet Messwerte auf")
            self.tray_icon.showMessage(
                self.tr("RealTime OpenControl"),
                t,
                self.app_icon,
                2000
            )
        else:
            self.savePlotStyles()
            if len(self.logger.signals)!=0:
                ok = pyqtlib.tri_message(
                self.tr("Speichern"), self.tr("Wollen Sie die aktuelle Sitzung speichern?"),"")
            else:
                ok=False
            if ok != None:
                if ok == True:
                    self.logger.exportJSON("restore")
                elif ok == False:
                    if os.path.exists("restore.json"):
                        os.remove("restore.json")
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
        if not self.settings.value("geometry") == None:
            self.restoreGeometry(self.settings.value("geometry", ""))
        if not self.settings.value("windowState") == None:
            self.restoreState(self.settings.value("windowState"))

        if not self.settings.value("devicesGeometry") == None:
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


def splashScreen(app):
    # Create and display the splash screen
    splash_pix = QtGui.QPixmap('data/splash.png')
    splash = QtWidgets.QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
    splash.setMask(splash_pix.mask())
    #splash.show()
    #app.processEvents()

    splash.setEnabled(False)
    # splash = QSplashScreen(splash_pix)
    # adding progress bar
    progressBar = QtWidgets.QProgressBar(splash)
    progressBar.setStyleSheet("QProgressBar{border: 0px solid grey;border-radius: 20px;text-align: center; background-color: rgba(255, 255, 255, 0)} QProgressBar::chunk {background-color: rgba(31, 31, 31, 0.7);width: 10px;margin: 0px;}")
    progressBar.setMaximum(10)
    progressBar.setGeometry(0, splash_pix.height() -27, splash_pix.width(), 27)

    # splash.setMask(splash_pix.mask())

    splash.show()
    #splash.showMessage("<h1><font color='white'>RealTime OpenControl loading ...</font></h1>\nv1.6", QtCore.Qt.AlignBottom | QtCore.Qt.AlignCenter, QtCore.Qt.black)

    for i in range(1, 11):
        progressBar.setValue(i)
        t = time.time()
        while time.time() < t + 0.1:
           app.processEvents()

    return splash

def setStyleSheet(app, myapp):
    try:
        import qtmodern.styles
        import qtmodern.windows
        qtmodern.styles.dark(app)
        #mw = qtmodern.windows.ModernWindow(myapp)
        mw = myapp
        return app, mw
    except:
        tb = traceback.format_exc()
        print(tb)
        print("New Style not installed")
        with open("data/ui/darkmode.html", 'r') as myfile:
            stylesheet = myfile.read().replace('\n', '')
        app.setStyleSheet(stylesheet)
        return app, myapp

def setLanguage(app):
    with open("config.json", encoding="UTF-8") as jsonfile:
        config = json.load(jsonfile, encoding="UTF-8")
    if config['language'] == 'en':
        translator = QtCore.QTranslator()
        translator.load("lang/en_en.qm")
        app.installTranslator(translator)
    # more info here: http://kuanyui.github.io/2014/09/03/pyqt-i18n/
    # generate translationfile: % pylupdate5 RTOC.py -ts lang/de_de.ts
    # compile translationfile: % lrelease-qt5 lang/de_de.ts
    # use self.tr("TEXT TO TRANSLATE") in the code

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    with open("config.json", encoding="UTF-8") as jsonfile:
        config = json.load(jsonfile, encoding="UTF-8")
        if config['language'] == 'en':
            print("English language selected")
            translator = QtCore.QTranslator()
            translator.load("lang/en_en.qm")
            app.installTranslator(translator)
            # more info here: http://kuanyui.github.io/2014/09/03/pyqt-i18n/
            # generate translationfile: % pylupdate5 RTOC.py -ts lang/de_de.ts
            # compile translationfile: % lrelease-qt5 lang/de_de.ts
            # use self.tr("TEXT TO TRANSLATE") in the code
    myapp = RTOC()

    splash = splashScreen(app)
    app, myapp = setStyleSheet(app, myapp)

    myapp.show()
    splash.finish(myapp)
    app.exec_()
    sys.exit()
