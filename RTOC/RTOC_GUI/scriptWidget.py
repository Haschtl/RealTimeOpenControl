import os
from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5 import QtCore
import sys
import traceback

from .scriptHelpWidget import ScriptHelpWidget
from .scriptSubWidget import ScriptSubWidget
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


class ScriptWidget(QtWidgets.QWidget):
    def __init__(self, logger):
        super(ScriptWidget, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/RTOC_GUI'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/ui/scriptWidget.ui", self)

        self.logger = logger
        self.scripts = []
        self.activeScript = 0

        self.help = ScriptHelpWidget(self)
        self.help.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

        self.loadScriptButton.clicked.connect(self.loadScriptAction)
        self.saveScriptButton.clicked.connect(self.saveScriptAction)
        self.helpButton.clicked.connect(self.toggleHelpAction)
        self.tabWidget.currentChanged.connect(self.changeActiveScript)
        self.openScript("", translate('RTOC', "new"))
        self.updateListWidget()

    def getSession(self):
        ans = []
        for script in self.scripts:
            scriptstr = script.scriptEdit.toPlainText()
            filepath = script.filepath
            if filepath == '':
                name = translate('RTOC', 'new')
            else:
                name = filepath
            ans.append([scriptstr, name, filepath])
        return ans

    def openFile(self, fileName):
        if os.path.exists(fileName):
            try:
                with open(fileName, "r") as file:
                    text = file.read()
                head, tail = os.path.split(fileName)
                self.openScript(text, tail, fileName)
                # self.logger.config["lastScript"] = fileName
                return True
            except Exception:
                self.openScript(translate('RTOC', "Failed to load {}").format(fileName), translate('RTOC', "Error"), fileName)
                # self.logger.config["lastScript"] = ""
                logging.debug(traceback.format_exc())
                return False
        else:
            self.openScript(translate('RTOC', "File not found: {}").format(fileName), translate('RTOC', "Error"), fileName)
            return False

    def openScript(self, scriptstr="", name="", filepath=""):
        self.scripts.append(ScriptSubWidget(self.logger, scriptstr, filepath))
        self.scripts[-1].modifiedCallback = self.scriptModifiedCallback
        self.tabWidget.insertTab(len(self.scripts)-1, self.scripts[len(self.scripts)-1], name)
        self.tabWidget.setCurrentIndex(len(self.scripts)-1)

    def scriptModifiedCallback(self, edited, newtext=None):
        if edited:
            text = self.tabWidget.tabText(self.activeScript)+"*"
            self.tabWidget.setTabText(self.activeScript, text)
        else:
            if newtext is not None:
                text = newtext
            else:
                text = self.tabWidget.tabText(self.activeScript)[:-1]
            self.tabWidget.setTabText(self.activeScript, text)

    def closeScript(self, idx):
        if idx < len(self.scripts):
            self.scripts[idx].close()
            if self.scripts[idx].run is False:
                self.tabWidget.removeTab(idx)
                self.scripts.pop(idx)
                if len(self.scripts) == 0:
                    self.openScript("", translate('RTOC', "Unknown"))

    def changeActiveScript(self):
        self.activeScript = self.tabWidget.currentIndex()
        if self.activeScript == len(self.scripts):
            self.openScript("", translate('RTOC', "Unknown"))

    def addTextToScriptEdit(self, strung):
        self.scripts[self.activeScript].addTextToScriptEdit(strung)

    def saveScriptAction(self):
        self.scripts[self.activeScript].saveScript()

    def loadScriptAction(self):
        dir_path = self.logger.config['global']['documentfolder']
        dir_path = self.logger.config['global']['documentfolder']
        fileBrowser = QtWidgets.QFileDialog(self)
        fileBrowser.setDirectory(dir_path)
        fileBrowser.setNameFilters(["Python (*.py)"])
        fileBrowser.selectNameFilter("")
        fname, mask = fileBrowser.getOpenFileName(
            self, translate('RTOC', "Load script"), dir_path, "Python (*.py)")
        # if fileBrowser.exec_():
        if fname:
            fileName = fname
            if mask == 'Python (*.py)':
                text = ""
                with open(fileName, "r") as file:
                    text = file.read()
                head, tail = os.path.split(fileName)
                self.openScript(text, tail, fileName)
                # self.logger.config["lastScript"] = fileName

    def toggleHelpAction(self):
        if self.helpButton.isChecked():
            self.help.show()
        else:
            self.help.hide()

    def updateListWidget(self):
        self.help.updateListWidget()
        for script in self.scripts:
            script.triggerWidget.triggerSignals.clear()
            for element in self.logger.database.signalNames():
                script.triggerWidget.triggerSignals.addItem(".".join(element))

    def executedCallback(self, ok, text):
        self.scripts[0].executedCallback(ok, text)

    def triggeredScriptCallback(self, devicename, signalname):
        for script in self.scripts:
            if script.triggerMethod == "signal":
                script.handleScript(devicename, signalname)

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)
        quitAction = menu.addAction(translate('RTOC', "Quit"))
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == quitAction:
            self.closeScript(self.activeScript)

    def clear(self):
        # self.scriptEdit.clear()
        self.help.signalListWidget.clear()
        for script in self.scripts:
            script.triggerWidget.triggerSignals.clear()
        self.updateListWidget()

    def closeEvent(self, event):
        for script in self.scripts:
            # script.run=False
            script.close()
            if script.run is True:
                break
