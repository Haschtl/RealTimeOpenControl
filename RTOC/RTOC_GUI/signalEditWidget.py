from PyQt5 import QtWidgets
from PyQt5.QtCore import QCoreApplication
from PyQt5 import uic
import time
import os
# from collections import deque
import numpy as np
import sys
from ..RTLogger.RTWebsocketClient import RTWebsocketClient

from ..lib import pyqt_customlib as pyqtlib
from .stylePlotGUI import plotStyler
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

if True:
    translate = QCoreApplication.translate

    def _(text):
        return translate('rtoc', text)
else:
    import gettext
    _ = gettext.gettext


class SignalEditWidget(QtWidgets.QWidget):
    def __init__(self, selfself, id, plotWidget):
        super(SignalEditWidget, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/RTOC_GUI'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/ui/signalWidget2.ui", self)
        self.self = selfself
        self.id = id
        self.plotWidget = plotWidget
        self.style = self.self.style

        self.pauseButton.clicked.connect(self.togglePause)
        self.renameButton.clicked.connect(self.renameSignal)
        self.editPlotButton.clicked.connect(self.editPlotStyle)
        self.deleteButton.clicked.connect(self.deleteSignal)
        self.exportButton.clicked.connect(self.exportSignal)
        self.xTimeBaseButton.clicked.connect(self.toggleXTimeBase)
        self.eventButton.clicked.connect(self.toggleEvents)

        self.sendRemoteButton.clicked.connect(self.sendRemote)
        self.offsetXSpinBox.valueChanged.connect(self.setXOffset)
        self.offsetYSpinBox.valueChanged.connect(self.setYOffset)
        self.scaleYSpinBox.valueChanged.connect(self.setYScale)
        self.scaleXSpinBox.valueChanged.connect(self.setXScale)

        self.xOffsetButton.clicked.connect(self.zeroXOffset)
        self.yOffsetButton.clicked.connect(self.zeroYOffset)

        self.cutButton.clicked.connect(self.cutSignal)
        self.duplicateButton.clicked.connect(self.duplicateSignal)

        self.submitModificationButton.clicked.connect(self.submitModification)

        self.labelButton.clicked.connect(self.toggleLabel)

    def togglePause(self):
        if self.pauseButton.isChecked():
            self.self.active = False
            self.pauseButton.setStyleSheet("background-color: rgb(114, 29, 29)")
        else:
            self.self.active = True
            self.pauseButton.setStyleSheet("")

    def toggleLabel(self):
        if self.labelButton.isChecked():
            self.self.labelItem.show()
        else:
            self.self.labelItem.hide()

    def toggleXTimeBase(self):
        if self.xTimeBaseButton.isChecked():
            self.self.xTimeBase = True
        else:
            self.self.xTimeBase = False

    def toggleEvents(self):
        if self.eventButton.isChecked() and self.self.logger.config['GUI']['showEvents']:
            self.self.showEvents = True
            for event in self.self.eventItems:
                event.show()
                event.vLine.show()
        else:
            self.self.showEvents = False
            for event in self.self.eventItems:
                event.hide()
                event.vLine.hide()

    def editPlotStyle(self):
        dialog = plotStyler(self.self.plot, "Stil von "+self.self.devicename + "."+self.self.signalname+" anpassen")
        if dialog.exec_():
            symbol = dialog.symbol
            brush = dialog.brush
            for key in symbol.keys():
                if type(symbol[key]) not in [int, float, str]:
                    symbol[key] = str(symbol[key])
            for key in brush.keys():
                if brush[key] is None:
                    pass
                elif type(brush[key]) not in [int, float, str]:
                    brush[key] = str(brush[key])
            self.plotWidget.plotStyles[str(self.self.devicename)+"."+str(self.self.signalname)] = {}
            self.plotWidget.plotStyles[str(self.self.devicename) + "."+str(self.self.signalname)]["symbol"] = symbol
            self.plotWidget.plotStyles[str(self.self.devicename) + "."+str(self.self.signalname)]["brush"] = brush

            self.self.labelItem.setColor(symbol["color"])
            self.self.updateLegend()

    def deleteSignal(self):
        self.self.remove(True, True, False)
        self.close()

    def cutSignal(self):
        if not self.plotWidget.cutButton.isChecked():
            pyqtlib.info_message(translate('RTOC', "Info"), translate('RTOC', "Select cutting tool first"),
                                 translate('RTOC', "You need to select the cutting area first."))
        else:
            x1 = self.plotWidget.cutVLine1.value()
            x2 = self.plotWidget.cutVLine2.value()
            xmin = 0
            xmax = 0
            if x1 == x2:
                pass
            elif x1 < x2:
                xmin = x1
                xmax = x2
            else:
                xmin = x2
                xmax = x1
            if xmin != xmax:
                xmin = self.plotWidget.lastActive+xmin
                xmax = self.plotWidget.lastActive+xmax

                minIdx = -1
                maxIdx = -1

                signal = self.self.logger.database.getSignal(self.id)
                for idx, value in enumerate(signal[2]):
                    if value > xmin and minIdx == -1:
                        minIdx = idx
                    elif value > xmax and maxIdx == -1:
                        maxIdx = idx
                        break
                if maxIdx > minIdx:
                    signalname = self.self.logger.database.getSignalName(self.id)[1] + \
                        "_cut"+str(int(xmax-xmin))+'s'
                    devicename = self.self.logger.database.getSignalName(self.id)[0]
                    unit = signal[4]
                    x = list(signal[2])[minIdx:maxIdx]
                    y = list(signal[3])[minIdx:maxIdx]
                    self.self.logger.database.plot(x, y, signalname, devicename, unit)
                    self.self.updatePlot()

    def exportSignal(self):
        dir_path = self.self.logger.config['global']['documentfolder']
        fileBrowser = QtWidgets.QFileDialog(self)
        fileBrowser.setDirectory(dir_path)
        fileBrowser.setNameFilters(
            [translate('RTOC', "CSV file (*.csv)")])
        fileBrowser.selectNameFilter("")
        fname, mask = fileBrowser.getSaveFileName(
            self, translate('RTOC', "Export"), dir_path, translate('RTOC', "CSV file (*.csv)"))
        # if fileBrowser.exec_():
        if fname:
            fileName = fname
            if mask == translate('RTOC', 'CSV file (*.csv)'):
                self.self.logger.database.exportSignal(fileName, self.self.logger.database.getSignal(self.id))

    def renameSignal(self):
        name, ok = pyqtlib.text_message(
            self, translate('RTOC', "Rename"), translate('RTOC', "Please enter a new name"), self.self.logger.database.getSignalName(self.id)[1])
        if name != "" and ok:
            self.self.logger.database.renameSignal(self.id, name)
        self.self.updatePlot()
        self.self.rename(name)

    def duplicateSignal(self):
        name = self.self.logger.database.getSignalName(self.id)
        signal = self.self.logger.database.getSignal(self.id)
        x = list(signal[2])
        y = list(signal[3])
        unit = signal[4]
        self.self.logger.database.plot(x, y, name[1]+"_2", name[0], unit)

    def zeroXOffset(self):
        value = self.self.logger.database.getSignal(self.id)[2][-1]
        if self.self.xTimeBase:
            self.self.signalModifications[0] = time.time()-value
        else:
            self.self.signalModifications[0] = -value
        self.offsetXSpinBox.setValue(self.self.signalModifications[0])
        self.self.updatePlot()

    def zeroYOffset(self):
        value = np.mean(self.self.logger.database.getSignal(self.id)[3])
        self.self.signalModifications[1] = -value
        self.offsetYSpinBox.setValue(-value)
        self.self.updatePlot()

    def setXOffset(self):
        self.self.signalModifications[0] = self.offsetXSpinBox.value()
        self.self.updatePlot()

    def setYOffset(self):
        self.self.signalModifications[1] = self.offsetYSpinBox.value()
        self.self.updatePlot()

    def setYScale(self):
        value = self.scaleYSpinBox.value()
        if value == 0:
            value = 1
        self.self.signalModifications[3] = value
        self.self.updatePlot()

    def setXScale(self):
        value = self.scaleXSpinBox.value()
        if value == 0:
            value = 1
        self.self.signalModifications[2] = value
        self.self.updatePlot()

    def submitModification(self):  # !!!
        ok = pyqtlib.alert_message(
            translate('RTOC', "Warning"), translate('RTOC', "Data will be changed permanently"))
        if ok:
            offsetX = self.self.signalModifications[0]
            offsetY = self.self.signalModifications[1]
            scaleX = self.self.signalModifications[2]
            scaleY = self.self.signalModifications[3]

            signal = self.self.logger.database.getSignal(self.id)
            x = list(signal[2])
            y = list(signal[3])
            y = [scaleY*(y+offsetY) for y in y]
            x = [scaleX*(x+offsetX) for x in x]
            if self.xySwapButton.isChecked():
                temp = x
                x = y
                y = temp
                self.xySwapButton.setChecked(False)
            self.self.logger.database.plot(x, y, sname=self.self.signalname, dname=self.self.devicename)

            self.scaleXSpinBox.setValue(1)
            self.scaleYSpinBox.setValue(1)
            self.offsetXSpinBox.setValue(0)
            self.offsetYSpinBox.setValue(0)

            self.self.updatePlot()

    def sendRemote(self):
        signal = self.self.logger.database.getSignal(self.id)
        name = self.self.logger.database.getSignalName(self.id)
        textlist = []
        for s in self.self.logger.config['websocket']['knownHosts'].keys():
            textlist.append(self.self.logger.config['websocket']['knownHosts'][s][0]+' ('+s+')')
        item, ok = pyqtlib.item_message(None, translate("RTOC",
            'Select host'), "Please select a known host", textlist, stylesheet="")
        if ok:
            idx = textlist.index(item)
            for idx2, s in enumerate(self.self.logger.config['websocket']['knownHosts'].keys()):
                if idx == idx2:
                    twoname = s.split(':')
                    host = twoname[0]
                    port = int(twoname[1])
                    password = self.self.logger.config['websocket']['knownHosts'][s][1]
                    client = RTWebsocketClient(host, port, password).connect().send(x=list(signal[2]), y=list(
                        signal[3]), dname=self.self.logger.config['global']['name']+":"+name[0], sname=name[1], unit=signal[4])
