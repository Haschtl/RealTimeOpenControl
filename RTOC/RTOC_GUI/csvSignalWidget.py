from PyQt5 import QtGui
from PyQt5 import uic
from PyQt5 import QtWidgets
from PyQt5.QtCore import QCoreApplication
import os
import sys
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

if True:
    translate = QCoreApplication.translate

    def _(text):
        return translate('csv', text)
else:
    import gettext
    _ = gettext.gettext


class CsvSignalWidget(QtWidgets.QWidget):
    def __init__(self, importer, setup=['', '', 0, 0, '']):
        super(CsvSignalWidget, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        uic.loadUi(packagedir+"/ui/csveditor_signal.ui", self)

        self.self = importer

        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.setSizePolicy(sizePolicy)

        self.deviceEdit.editingFinished.connect(self.self.updateSignalNames)
        self.signalEdit.editingFinished.connect(self.self.updateSignalNames)
        self.unitEdit.currentTextChanged.connect(self.self.updateSignalNames)
        self.xSpinBox.valueChanged.connect(self.checkValidity)
        self.ySpinBox.valueChanged.connect(self.checkValidity)

        self.deviceEdit.setText(setup[0])
        self.signalEdit.setText(setup[1])
        self.xSpinBox.setValue(setup[2])
        self.ySpinBox.setValue(setup[3])
        self.unitEdit.setCurrentText(setup[4])

        self.checkValidity()

    def read(self):
        ret = []
        ret.append(self.deviceEdit.text())
        ret.append(self.signalEdit.text())
        ret.append(self.xSpinBox.value())
        ret.append(self.ySpinBox.value())
        ret.append(self.unitEdit.currentText())

        return ret

    def checkValidity(self):
        error = False
        tooltiptext = ''
        if self.xSpinBox.value() == 0:
            tooltiptext += translate('RTOC', 'No x-data selected\n')
        elif self.xSpinBox.value() > self.self.model.columnCount():
            error = 1
            tooltiptext += translate('RTOC', 'Column {} not in CSV file\n').format(self.xSpinBox.value())
        if self.ySpinBox.value() == 0:
            error = 2
            tooltiptext += translate('RTOC', 'y-data not in CSV file (0)\n')
        elif self.ySpinBox.value() > self.self.model.columnCount():
            error = 3
            tooltiptext += translate('RTOC', 'Column {} not in CSV file\n').format(self.ySpinBox.value())

        if error is False:
            ylen = self.self.getColumn(self.ySpinBox.value()-1)
            if self.xSpinBox.value() != 0:
                xlen = self.self.getColumn(self.xSpinBox.value()-1)
            else:
                xlen = False

            if ylen is None:
                error = 4
                tooltiptext += translate('RTOC', 'Y-data empty\n')

            if xlen is None:
                error = 5
                tooltiptext += translate('RTOC', 'X-data empty\n')

            if error is False:
                xCheck, xData = self.checkData(self.self.getColumn(self.xSpinBox.value()-1))
                yCheck, yData = self.checkData(self.self.getColumn(self.ySpinBox.value()-1))

                if xlen is not False:
                    if len(xData) != len(yData):
                        error = 6
                        tooltiptext += translate('RTOC', 'Length of X and Y is different: {}:{}\n').format(len(xData), len(yData))
                if xCheck != [] and xlen is not False:
                    error = 7
                    tooltiptext += translate('RTOC', 'X: Error in following columns: {}\n').format(xCheck)
                if yCheck != []:
                    error = 8
                    tooltiptext += translate('RTOC', 'Y: Error in following columns: {}\n').format(yCheck)

        self.infoLabel.setToolTip(tooltiptext)
        if error is not False:
            self.infoLabel.setText(str(error))
            self.infoLabel.setStyleSheet('background-color: rgb(114, 29, 29)')
        else:
            self.infoLabel.setText('OK')
            self.infoLabel.setStyleSheet('background-color: rgb(44, 114, 29)')
        return error

    def checkData(self, data):
        error = []
        ret = []
        for idx, d in enumerate(data):
            try:
                try:
                    if d.text().replace(' ', '') != '':
                        # text = d.text()
                        empty = False
                    else:
                        empty = True
                except Exception:
                    empty = True
                if not empty:
                    ret.append(float(d.text().replace(',', '.')))
            except Exception:
                error.append(idx+1)
        return error, ret

    def updateName(self, lastDevice='', lastSignal='', lastUnit=''):
        if self.deviceEdit.text() != '':
            thisDevice = self.deviceEdit.text()
        else:
            thisDevice = lastDevice
        if self.unitEdit.currentText() != '':
            thisUnit = self.unitEdit.currentText()
        else:
            thisUnit = lastUnit
        if self.signalEdit.text() != '':
            thisSignal = self.signalEdit.text()
        else:
            try:
                lastInt = int(lastSignal[len(lastSignal)-1])+1
                lastSignal = lastSignal[0:len(lastSignal)-1]
            except Exception:
                lastInt = 1
            thisSignal = lastSignal+str(lastInt)

        self.deviceEdit.setPlaceholderText(thisDevice)
        self.signalEdit.setPlaceholderText(thisSignal)
        # self.unitEdit.setCurrentText(thisUnit)

        return thisDevice, thisSignal, thisUnit

    def getSignal(self):
        if self.checkValidity() is False:
            sigName = self.signalEdit.text()
            devName = self.deviceEdit.text()
            unit = self.unitEdit.currentText()
            xCheck, xData = self.checkData(self.self.getColumn(self.xSpinBox.value()-1))
            yCheck, yData = self.checkData(self.self.getColumn(self.ySpinBox.value()-1))
            if xData == []:
                xData = list(range(len(yData)))
            if sigName.replace(' ', '') == '':
                sigName = self.signalEdit.placeholderText()
            if devName.replace(' ', '') == '':
                devName = self.deviceEdit.placeholderText()
            return (xData, yData, sigName, devName, unit)
        else:
            return None

    def closeEvent(self, event, *args, **kwargs):
        super(CsvSignalWidget, self).closeEvent(event)
