from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5 import QtCore
import time
import traceback
from threading import Thread
from ..RTLogger.importCode import importCode
import os
import sys
from ..lib import pyqt_customlib as pyqtlib
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

if True:
    translate = QtCore.QCoreApplication.translate

    def _(text):
        return translate('rtoc', text)
else:
    import gettext
    _ = gettext.gettext


class AnimationThread(QtCore.QThread):
    blinkRequest = QtCore.pyqtSignal(bool)
    errorRequest = QtCore.pyqtSignal()

    def __init__(self):
        QtCore.QThread.__init__(self)
        self.thread_must_be_run = True
        self.mutex = QtCore.QMutex()

    def stop_this_thread(self):
        self.thread_must_be_run = False

    def error(self):
        self.errorRequest.emit()

    def run(self):
        self.mutex.lock()
        self.blinkRequest.emit(True)
        self.mutex.unlock()
        time.sleep(0.05)
        self.blinkRequest.emit(False)


class Callback(QtCore.QThread):
    received = QtCore.pyqtSignal(bool, str)

    def __init__(self, strung=""):
        super(Callback, self).__init__()
        self.ok = True
        self.text = ""

    def setText(self, ok, strung):
        self.ok = ok
        self.text = strung
        self.run()

    def run(self):
        self.received.emit(self.ok, self.text)


class ScriptSubWidget(QtWidgets.QWidget):
    def __init__(self, logger, scriptstr, filepath=""):
        super(ScriptSubWidget, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/RTOC_GUI'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/ui/scriptSubWidget.ui", self)

        self.infoEdit.hide()

        self.logger = logger
        self.scriptEdit.setPlainText(scriptstr)
        self.selectedTriggerSignals = []
        self.triggerMethod = "samplerate"
        self.scriptSamplerate = 10
        self.script = None
        self.scriptEnabled = False
        self.scriptStr = ""
        self.run = True
        self.filepath = filepath
        self.saved = True
        self.initTrigger()

        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self.scriptEdit)
        self.shortcut.activated.connect(self.saveScript)

        self.modifiedCallback = None

        self.triggerWidget.triggerSamplerateSpinBox.valueChanged.connect(
            self.updateTriggerSamplerate)

        self.triggerWidget.triggerSignals.itemSelectionChanged.connect(
            self.updateSelectedTriggerSignals)

        self.scriptEdit.modificationChanged.connect(self.scriptChangedAction)

        self.animation_thread = AnimationThread()
        self.animation_thread.blinkRequest.connect(self.blinkButton)
        self.animation_thread.errorRequest.connect(self.errorButton)

        self.updateThread = Callback()
        self.updateThread.received.connect(self.updateGUI)

        self.__updater = Thread(target=self.samplerateTriggeredThread)    # Actualize data
        self.__updater.start()

    def scriptChangedAction(self, changed):
        if changed:
            self.saved = False
            if self.modifiedCallback:
                self.modifiedCallback(True)
        else:
            self.saved = True

    def initTrigger(self):
        self.startScriptButton.setCheckable(True)
        self.startScriptButton.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.startScriptButton.setMenu(QtWidgets.QMenu(self.startScriptButton))

        action = QtWidgets.QWidgetAction(self.startScriptButton)
        self.triggerWidget = QtWidgets.QWidget()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/RTOC_GUI'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/ui/triggerWidget.ui", self.triggerWidget)
        action.setDefaultWidget(self.triggerWidget)
        self.startScriptButton.menu().addAction(action)
        self.startScriptButton.clicked.connect(self.toggleScript)
        self.singleStartScriptButton.clicked.connect(self.singleRunScript)

        self.triggerWidget.sampleRadio.toggled.connect(self.enableSampleRateTrigger)
        self.triggerWidget.signalRadio.toggled.connect(self.enableSignalTrigger)

        self.startScriptButton.setStyleSheet(
            "QToolButton:checked, QToolButton:pressed,QToolButton::menu-button:pressed {background-color: #31363b;}")

        self.triggerWidget.triggerSignals.clear()
        for element in self.logger.database.signalNames():
            # print(element)
            self.triggerWidget.triggerSignals.addItem(".".join(element))

    def toggleScript(self):
        scriptRunning = self.startScriptButton.isChecked()
        if not scriptRunning:
            self.scriptEnabled = False
            self.startScriptButton.setText("Start")
            self.startScriptButton.setStyleSheet("background-color: #31363b")
        else:
            self.infoEdit.setPlainText("")
            self.infoEdit.hide()
            ok, warnings = self.initScript()
            if ok:
                self.startScript()
            else:
                self.scriptEnabled = False
                self.startScriptButton.setChecked(False)
                self.startScriptButton.setText("Error: Restart")
                self.infoEdit.setPlainText(warnings)
                self.infoEdit.show()

    def saveScript(self):
        if self.filepath == "":
            file_path = os.path.dirname(os.path.realpath(__file__))
            fileBrowser = QtWidgets.QFileDialog(self)
            fileBrowser.setDirectory(file_path)
            fileBrowser.setNameFilters(["Python (*.py)"])
            fileBrowser.selectNameFilter("")
            self.filepath, mask = fileBrowser.getSaveFileName(
                self, translate('RTOC', "Save script as..."), self.filepath, "Python (*.py)")
        if self.filepath:
            fileName = self.filepath
            text = self.scriptEdit.toPlainText()
            with open(fileName, "w") as file:
                text = file.write(text)
                self.scriptEdit.document().setModified(False)
                self.saved = True
                # self.logger.config["lastScript"] = fileName
                if self.modifiedCallback:
                    head, tail = os.path.split(fileName)
                    self.modifiedCallback(False, tail)

    def startScript(self):
        self.scriptEnabled = True
        self.startScriptButton.setChecked(True)
        self.startScriptButton.setText(translate('RTOC', "Stop"))
        self.infoEdit.setPlainText("")
        self.infoEdit.hide()

    def initScript(self):
        self.scriptStr = self.scriptEdit.toPlainText()
        scriptStr = self.logger.generateCode(self.scriptStr)
        ok, errors = self.checkScript(scriptStr)
        if ok:
            try:
                self.script.init(self.logger)
                return True, errors
            except Exception:
                return False, scriptStr + errors + "\nERROR in Initialization"
        else:
            self.scriptEnabled = False
            errors = scriptStr + errors + "\nERROR in Code-Import"
            return False, errors

    def checkScript(self, scriptStr):
        try:
            self.script = importCode(scriptStr, "script")
            return True, ""
        except Exception:
            tb = traceback.format_exc()
            tb = tb+"\nSYNTAX ERROR in script"
            return False, tb

    def singleRunScript(self):
        self.infoEdit.hide()
        ok, ans = self.logger.executeScript(self.scriptEdit.toPlainText())
        if ok:
            self.infoEdit.show()
            self.infoEdit.appendPlainText(ans)
        else:
            self.infoEdit.show()
            self.infoEdit.appendPlainText(ans)

    def addTextToScriptEdit(self, text):
        self.setScriptEditPos(self.getScriptEditPos())
        if text.find("#"):
            text = text[:text.find("#")]
        self.scriptEdit.insertPlainText(text)

    def updateSelectedTriggerSignals(self):
        self.selectedTriggerSignals = []
        for item in self.triggerWidget.triggerSignals.selectedItems():
            self.selectedTriggerSignals.append(item.text())

    def enableSampleRateTrigger(self):
        self.triggerMethod = "samplerate"
        self.triggerWidget.triggerSignals.setEnabled(False)
        self.triggerWidget.triggerSamplerateSpinBox.setEnabled(True)

    def enableSignalTrigger(self):
        self.triggerMethod = "signal"
        self.triggerWidget.triggerSignals.setEnabled(True)
        self.triggerWidget.triggerSamplerateSpinBox.setEnabled(False)

    def updateTriggerSamplerate(self):
        self.scriptSamplerate = self.triggerWidget.triggerSamplerateSpinBox.value()

    # text cursor functions
    def getScriptEditCursor(self):
        return self.scriptEdit.textCursor()

    def setScriptEditPos(self, value):
        tc = self.getScriptEditCursor()
        tc.setPosition(value, QtGui.QTextCursor.KeepAnchor)
        self.scriptEdit.setTextCursor(tc)

    def getScriptEditPos(self):
        return self.getScriptEditCursor().position()

    def executedCallback(self, ok, text):
        if ok:
            self.animation_thread.start()
        else:
            self.animation_thread.error()
        if text != "":
            self.updateThread.setText(ok, text)

    def updateGUI(self, ok, text):
        self.infoEdit.show()
        if self.infoEdit.toPlainText() != text or ok:
            self.infoEdit.appendPlainText(text)

    def blinkButton(self, value):
        if value is True:
            self.startScriptButton.setStyleSheet("QToolButton{background-color: rgb(25, 98, 115)}")
        else:
            self.startScriptButton.setStyleSheet("QToolButton{background-color: #31363b}")

    def errorButton(self):
        if self.startScriptButton.isChecked() and self.startScriptButton.styleSheet != "QToolButton{background-color: #8c2020}":
            self.startScriptButton.setStyleSheet("QToolButton{background-color: #8c2020}")

    def handleScript(self, devicename, signalname):
        if self.scriptEnabled:
            signalname = devicename + "." + signalname
            if signalname in self.selectedTriggerSignals:
                self.executeScript()

    # def singleRunScript(self, scriptStr):
    #     self.scriptStr = self.scriptEdit.toPlainText()
    #     scriptStr = self.logger.generateCode(self.scriptStr)
    #     ok, errors = self.checkScript(scriptStr)
    #     if ok:
    #         self.executeScript()

    def executeScript(self):
        try:
            clock = time.time()
            prints = self.script.test(self.logger, clock)
            self.executedCallback(True, prints)
        except Exception:
            tb = traceback.format_exc()
            self.checkScript(self.logger.generateCode(self.scriptStr))
            scriptConverted = "Script converted:\n\n" + \
                self.logger.generateCode(self.scriptStr)+"\n\n"
            self.executedCallback(False, scriptConverted + tb)

    def samplerateTriggeredThread(self):
        diff = 0
        self.gen_start = time.time()
        while self.run:  # All should be inside of this while-loop, because self.run == False should stops this plugin
            if self.scriptSamplerate < 0:
                self.scriptSamplerate = 0
            if self.scriptSamplerate != 0:
                if diff < 1/self.scriptSamplerate:
                    time.sleep(1/self.scriptSamplerate-diff)
                start_time = time.time()
                if self.scriptEnabled and self.triggerMethod is "samplerate":
                    self.executeScript()
                diff = time.time() - start_time
            else:
                time.sleep(1)

    def closeEvent(self, event):
        if self.saved:
            self.run = False
            super(ScriptSubWidget, self).closeEvent(event)
        else:
            ok = pyqtlib.alert_message(translate('RTOC', "Warning"), translate('RTOC',
                "Do you want to save the script?"), "", "", translate('RTOC', "Yes"), translate('RTOC', "No"))
            if ok is not None:
                if ok is True:
                    self.saveScript()
                self.run = False
                super(ScriptSubWidget, self).closeEvent(event)
