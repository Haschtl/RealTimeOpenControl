from PyQt5 import QtWidgets
from PyQt5 import uic
import time
import os
from collections import deque
import numpy as np
import sys

from .lib import pyqt_customlib as pyqtlib
from .stylePlotGUI import plotStyler


class SignalEditWidget(QtWidgets.QWidget):
    def __init__(self, selfself, id, plotWidget):
        super(SignalEditWidget, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/data'
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
        if self.eventButton.isChecked():
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
        dialog = plotStyler(self.self.plot, "Stil von "+self.self.devicename +
                            "."+self.self.signalname+" anpassen")
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
            self.plotWidget.plotStyles[str(self.self.devicename) +
                                       "."+str(self.self.signalname)]["symbol"] = symbol
            self.plotWidget.plotStyles[str(self.self.devicename) +
                                       "."+str(self.self.signalname)]["brush"] = brush

            self.self.labelItem.setColor(symbol["color"])

    def deleteSignal(self):
        self.self.remove()
        self.close()

    def cutSignal(self):
        if not self.plotWidget.cutButton.isChecked():
            pyqtlib.info_message(self.tr("Info"), self.tr("Wähle zuerst das Schneide-Tool aus"),
                                 self.tr("Du musst zuerst deine Schnittbereich festlegen"))
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

                for idx, value in enumerate(self.self.logger.getSignal(self.id)[0]):
                    if value > xmin and minIdx == -1:
                        minIdx = idx
                    elif value > xmax and maxIdx == -1:
                        maxIdx = idx
                        break
                if maxIdx > minIdx:
                    signalname = self.self.logger.getSignalNames(self.id)[1] + \
                        "_cut"+str(len(self.self.logger.signals))
                    devicename = self.self.logger.getSignalNames(self.id)[0]
                    unit = self.self.logger.getSignalUnits(self.id)
                    x = list(self.self.logger.getSignal(self.id)[0])[minIdx:maxIdx]
                    y = list(self.self.logger.getSignal(self.id)[1])[minIdx:maxIdx]
                    self.self.logger.plot(x, y, signalname, devicename, unit)
                    self.self.updatePlot()

    def exportSignal(self):
        dir_path = self.config['documentfolder']
        fileBrowser = QtWidgets.QFileDialog(self)
        fileBrowser.setDirectory(dir_path)
        fileBrowser.setNameFilters(
            [self.tr("CSV-Datei (*.csv)")])
        fileBrowser.selectNameFilter("")
        fname, mask = fileBrowser.getSaveFileName(
            self, self.tr("Export"), dir_path, self.tr("CSV-Datei (*.csv)"))
        # if fileBrowser.exec_():
        if fname:
            fileName = fname
            if mask == self.tr('CSV-Datei (*.csv)'):
                self.self.logger.exportSignal(fileName, self.self.logger.getSignal(self.id))

    def renameSignal(self):
        name, ok = pyqtlib.text_message(
            self, self.tr("Umbenennen"), self.tr("Bitte gib einen neuen Namen an"), self.self.logger.getSignalNames(self.id)[1])
        if name != "" and ok:
            self.self.logger.getSignalNames(self.id)[1] = name
        self.self.updatePlot()
        self.self.rename(name)

    def duplicateSignal(self):
        signalname = self.self.logger.getSignalNames(self.id)[1]
        devicename = self.self.logger.getSignalNames(self.id)[0]
        x, y = self.self.logger.getSignal(self.id)
        unit = self.self.logger.getSignalUnits(self.id)
        self.self.logger.plot(x, y, signalname+"_2", devicename, unit)

    def zeroXOffset(self):
        value = self.self.logger.getSignal(self.id)[0][-1]
        if self.self.xTimeBase:
            self.self.signalModifications[0] = time.time()-value
        else:
            self.self.signalModifications[0] = -value
        self.offsetXSpinBox.setValue(self.self.signalModifications[0])
        self.self.updatePlot()

    def zeroYOffset(self):
        value = np.mean(self.self.logger.getSignal(self.id)[1])
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

    def submitModification(self):
        ok = pyqtlib.alert_message(
            self.tr("Achtung"), self.tr("Daten werden dauerhaft geändert"), "", "", self.tr("Ja"), self.tr("Nein"))
        if ok:
            offsetX = self.self.signalModifications[0]
            offsetY = self.self.signalModifications[1]
            scaleX = self.self.signalModifications[2]
            scaleY = self.self.signalModifications[3]

            x = list(self.self.logger.getSignal(self.id)[0])
            y = list(self.self.logger.getSignal(self.id)[1])
            y = [scaleY*(y+offsetY) for y in y]
            x = [scaleX*(x+offsetX) for x in x]
            if self.xySwapButton.isChecked():
                temp = x
                x = y
                y = temp
                self.xySwapButton.setChecked(False)
            self.self.logger.getSignal(self.id)[0] = deque(x, self.self.logger.maxLength)
            self.self.logger.getSignal(self.id)[1] = deque(y, self.self.logger.maxLength)

            self.scaleXSpinBox.setValue(1)
            self.scaleYSpinBox.setValue(1)
            self.offsetXSpinBox.setValue(0)
            self.offsetYSpinBox.setValue(0)

            self.self.updatePlot()
