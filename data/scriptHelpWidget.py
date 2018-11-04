from PyQt5 import QtWidgets
from PyQt5 import uic


class ScriptHelpWidget(QtWidgets.QWidget):
    def __init__(self, selfself):
        super(ScriptHelpWidget, self).__init__()
        uic.loadUi("data/ui/scriptHelpWidget.ui", self)
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
            if self.logger.pluginStatus['plugins.' + element.split(".")[0]] == "OK":
                if element.split(".")[1] not in ["dataY", "dataX", "datanames", "dataunits", "devicename", "run", "smallGUI",'sock']:
                    self.listWidget.addItem(element)
        for element in self.logger.pluginFunctions.keys():
            if self.logger.pluginStatus['plugins.' + element.split(".")[0]] == "OK":
                if element.split(".")[1] not in ["loadGUI", "updateT", "stream", "plot", "event", "createTCPClient", "sendTCP", "close"]:
                    self.listWidget.addItem(element+"()")
        for element in self.logger.signalNames:
            self.signalListWidget.addItem(".".join(element))

    def closeEvent(self, event, *args, **kwargs):
        self.self.helpButton.setChecked(False)
        super(ScriptHelpWidget, self).closeEvent(event)
