from PyQt5 import QtWidgets
from PyQt5 import uic
import os
import sys
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)


class ScriptHelpWidget(QtWidgets.QWidget):
    def __init__(self, selfself):
        super(ScriptHelpWidget, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/RTOC_GUI'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/ui/scriptHelpWidget.ui", self)
        self.self = selfself
        self.logger = self.self.logger

        self.listWidget.clicked.connect(self.addFuncToScriptEdit)
        self.signalListWidget.clicked.connect(self.addSignalToScriptEdit)
        self.listWidget_default.clicked.connect(self.addDefaultToScriptEdit)
        self.listWidget_default_2.clicked.connect(self.addDefaultToScriptEdit2)

    def addFuncToScriptEdit(self):
        text = self.listWidget.selectedItems()[0].text()
        self.self.addTextToScriptEdit(text)

    def addSignalToScriptEdit(self):
        text = self.signalListWidget.selectedItems()[0].text()
        self.self.addTextToScriptEdit(text)

    def addDefaultToScriptEdit(self):
        text = self.listWidget_default.selectedItems()[0].text()
        self.self.addTextToScriptEdit(text)

    def addDefaultToScriptEdit2(self):
        text = self.listWidget_default_2.selectedItems()[0].text()
        self.self.addTextToScriptEdit(text)

    def updateListWidget(self):
        self.listWidget.clear()
        self.signalListWidget.clear()
        self.signalListWidget.addItem("clock")
        for element in self.logger.pluginParameters.keys():
            if self.logger.pluginStatus[element.split('.')[0]] == True:
                if element.split(".")[1] not in ["run", "smallGUI", 'widget', 'samplerate','lockPerpetialTimer']:
                    self.listWidget.addItem(element)
        for element in self.logger.pluginFunctions.keys():
            if self.logger.pluginStatus[element.split('.')[0]] == True:
                if element.split(".")[1] not in ["loadGUI", "updateT", "stream", "plot", "event", "createTCPClient", "close", "cancel", "start", "setSamplerate","setDeviceName",'setPerpetualTimer','setInterval','getDir']:
                    parStr = ', '.join(self.logger.pluginFunctions[element][1])
                    self.listWidget.addItem(element+"("+parStr+")")
        for element in self.logger.database.signalNames():
            self.signalListWidget.addItem(".".join(element))

    def closeEvent(self, event, *args, **kwargs):
        self.self.helpButton.setChecked(False)
        super(ScriptHelpWidget, self).closeEvent(event)
