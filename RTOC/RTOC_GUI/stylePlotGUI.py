from PyQt5 import QtCore
from PyQt5 import uic
from PyQt5 import QtWidgets, QtGui
import pyqtgraph as pg
import os
import sys
from PyQt5.QtCore import QCoreApplication

from . import define as define
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

if True:
    translate = QCoreApplication.translate

    def _(text):
        return translate('signal', text)
else:
    import gettext
    _ = gettext.gettext


class plotStyler(QtWidgets.QDialog):
    def __init__(self, plot=None, title="", stylesheet=""):
        super(plotStyler, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/RTOC_GUI'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/ui/stylePlotDialog2.ui", self)
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setStyleSheet(stylesheet)
        self.setCallbacks()
        self.plot = plot
        self.lineColor = None
        self.fillLevel = None
        self.symbolColor = None
        self.symbolPenColor = None
        self.shadowColor = None
        self.fillColor = None
        self.brush = {}
        self.symbol = {}
        self.colorDialog = QtGui.QColorDialog()
        self.colorDialog.hide()
        self.colorLayout.addWidget(self.colorDialog)
        self.colorDialog.colorSelected.connect(self.setColor)
        if plot is not None:
            symbol, brush = getStyle(plot)
            self.setGUIStyle(symbol, brush)

    def setCallbacks(self):
        self.cancelButton.clicked.connect(self.close)
        self.styleButton.clicked.connect(self.setStyleAction)
        self.lineColorButton.clicked.connect(self.setLineColor)
        self.shadowColorButton.clicked.connect(self.setShadowColor)
        self.symbolColorButton.clicked.connect(self.setSymbolColor)
        self.fillColorButton.clicked.connect(self.setFillColor)
        self.symbolPenColorButton.clicked.connect(self.setSymbolPenColor)
        self.fillColorSpinBox.valueChanged.connect(self.setFillLevel)
        self.deleteFillButton.clicked.connect(self.deleteFill)

    def setLineColor(self):
        self.colorDialog.show()
        self.setMinimumSize(1100, 500)
        self.resize(1100, 500)
        self.lineColorButton.setStyleSheet("background-color:" + self.lineColor)

    def setShadowColor(self):
        self.colorDialog.show()
        self.setMinimumSize(1100, 500)
        self.resize(1100, 500)
        self.shadowColorButton.setStyleSheet("background-color:" + self.shadowColor)

    def setColor(self):
        color = self.colorDialog.currentColor().name()
        stylesheet = "background-color:" + color
        if self.lineColorButton.isChecked():
            self.lineColor = color
            self.lineColorButton.setStyleSheet(stylesheet)
            self.lineColorButton.setChecked(False)
        if self.shadowColorButton.isChecked():
            self.shadowColor = color
            self.shadowColorButton.setStyleSheet(stylesheet)
            self.shadowColorButton.setChecked(False)

        if self.symbolColorButton.isChecked():
            self.symbolColor = color
            self.symbolColorButton.setStyleSheet(stylesheet)
            self.symbolColorButton.setChecked(False)

        if self.symbolPenColorButton.isChecked():
            self.symbolPenColor = color
            self.symbolPenColorButton.setStyleSheet(stylesheet)
            self.symbolPenColorButton.setChecked(False)

        if self.fillColorButton.isChecked():
            self.fillColor = color
            self.fillColorButton.setStyleSheet(stylesheet)
            self.fillColorButton.setChecked(False)

        self.colorDialog.hide()
        self.setMinimumSize(466, 500)
        self.resize(466, 500)

    def setSymbolColor(self):
        self.colorDialog.show()
        self.setMinimumSize(1100, 500)
        self.resize(1100, 500)
        if self.symbolColor is not None:
            self.symbolColorButton.setStyleSheet("background-color:" + str(self.symbolColor))

    def setFillColor(self):
        self.colorDialog.show()
        self.setMinimumSize(1100, 500)
        self.resize(1100, 500)
        if self.fillColor is not None:
            self.fillColorButton.setStyleSheet("background-color:" + str(self.fillColor))
        self.fillLevel = self.fillColorSpinBox.value()

    def setSymbolPenColor(self):
        self.colorDialog.show()
        self.setMinimumSize(1100, 500)
        self.resize(1100, 500)
        if self.symbolPenColor is not None:
            self.symbolPenColorButton.setStyleSheet("background-color:" + str(self.symbolPenColor))

    def setFillLevel(self):
        self.fillLevel = self.fillColorSpinBox.value()

    def deleteFill(self):
        self.fillLevel = None
        self.fillColorSpinBox.setValue(0)
        self.fillColor = None
        self.fillColorButton.setStyleSheet("")

    def setStyleAction(self, plot=None):
        plot = self.plot
        symbol, brush = self.getGUIStyle()
        setStyle(plot, symbol, brush)
        self.symbol, self.brush = getStyle(plot)
        self.accept()

    def setGUIStyle(self, symbol, brush):
        if "style" in symbol.keys():
            style = symbol["style"]
            idx = 0
            if style == QtCore.Qt.SolidLine:
                idx = 0
            elif style == QtCore.Qt.DotLine:
                idx = 1
            elif style == QtCore.Qt.DashLine:
                idx = 2
            elif style == QtCore.Qt.DashDotLine:
                idx = 3
            elif style == QtCore.Qt.DashDotDotLine:
                idx = 4
            self.lineStyleComboBox.setCurrentIndex(idx)

        if "shadowStyle" in symbol.keys():
            style = symbol["shadowStyle"]
            idx = 0
            if style == QtCore.Qt.SolidLine:
                idx = 1
            elif style == QtCore.Qt.DotLine:
                idx = 2
            elif style == QtCore.Qt.DashLine:
                idx = 3
            elif style == QtCore.Qt.DashDotLine:
                idx = 4
            elif style == QtCore.Qt.DashDotDotLine:
                idx = 5
            self.shadowStyleComboBox.setCurrentIndex(idx)

        if "alpha" in symbol.keys():
            self.alphaSpinBox.setValue(int(symbol["alpha"]*100))
        if "width" in symbol.keys():
            self.lineWidthSpinBox.setValue(symbol["width"])

        if "shadowWidth" in symbol.keys():
            self.shadowWidthSpinBox.setValue(symbol["shadowWidth"])

        if "color" in symbol.keys():
            self.lineColor = symbol["color"]
            if type(self.lineColor) == str:
                self.lineColorButton.setStyleSheet("background-color:"+str(self.lineColor))
            elif type(self.lineColor) == tuple:
                self.lineColorButton.setStyleSheet("background-color:"+str(self.lineColor))
            elif self.shadowColor is not None:
                self.lineColorButton.setStyleSheet("background-color:"+str(self.lineColor.name()))

        if "shadowColor" in symbol.keys():
            self.shadowColor = symbol["shadowColor"]
            if type(self.shadowColor) == str:
                self.shadowColorButton.setStyleSheet("background-color:"+str(self.shadowColor))
            elif type(self.shadowColor) == tuple:
                self.shadowColorButton.setStyleSheet("background-color:"+str(self.shadowColor))
            elif self.shadowColor is not None:
                self.shadowColorButton.setStyleSheet(
                    "background-color:"+str(self.shadowColor.name()))

        if "style" in brush.keys():
            style = brush["style"]
            idx = 0
            if style == "d":
                idx = 0
            elif style == "o":
                idx = 1
            elif style == "x":
                idx = 2
            elif style == "s":
                idx = 3
            elif style == "t":
                idx = 4
            elif style == "+":
                idx = 5
            self.symbolComboBox.setCurrentIndex(idx)

        if "size" in brush.keys():
            self.symbolSizeSpinBox.setValue(brush["size"])

        if "color" in brush.keys():
            self.symbolColor = brush["color"]
            if type(self.symbolColor) == str:
                self.symbolColorButton.setStyleSheet("background-color:"+str(self.symbolColor))
            elif type(self.symbolColor) == tuple:
                self.symbolColorButton.setStyleSheet("background-color:"+str(self.symbolColor))
            elif self.shadowColor is not None:
                self.symbolColorButton.setStyleSheet(
                    "background-color:"+str(self.symbolColor.name()))

        if "fillBrush" in brush.keys():
            self.fillColor = brush["fillBrush"]
            if type(self.fillColor) == str:
                self.fillColorButton.setStyleSheet("background-color:"+str(self.fillColor))
            elif type(self.fillColor) == tuple:
                self.fillColorButton.setStyleSheet("background-color:"+str(self.fillColor))
            elif self.shadowColor is not None:
                self.fillColorButton.setStyleSheet("background-color:"+str(self.fillColor.name()))

        if "pen" in brush.keys():
            self.symbolPenColor = brush["pen"]
            if type(self.symbolPenColor) == str:
                self.symbolPenColorButton.setStyleSheet(
                    "background-color:"+str(self.symbolPenColor))
            elif type(self.symbolPenColor) == tuple:
                self.symbolPenColorButton.setStyleSheet(
                    "background-color:"+str(self.symbolPenColor))
            elif self.shadowColor is not None:
                self.symbolPenColorButton.setStyleSheet(
                    "background-color:"+str(self.symbolPenColor.name()))

        if "fillLevel" in brush.keys():
            if brush["fillLevel"] is not None:
                self.fillLevel = brush["fillLevel"]
                self.fillColorSpinBox.setValue(self.fillLevel)

    def getGUIStyle(self):
        symbol = {}
        brush = {}
        style = self.lineStyleComboBox.currentText()
        if style == translate('RTOC', 'Line'):
            symbol["style"] = QtCore.Qt.SolidLine
        elif style == translate('RTOC', 'Dots (D)'):
            symbol["style"] = QtCore.Qt.DotLine
        elif style == translate('RTOC', 'Strokes (S)'):
            symbol["style"] = QtCore.Qt.DashLine
        elif style == translate('RTOC', 'D S'):
            symbol["style"] = QtCore.Qt.DashDotLine
        elif style == translate('RTOC', 'D D S'):
            symbol["style"] = QtCore.Qt.DashDotDotLine
        else:
            logging.warning('no style applied')

        style = self.shadowStyleComboBox.currentText()
        if style == translate('RTOC', 'Line'):
            symbol["shadowStyle"] = QtCore.Qt.SolidLine
        elif style == translate('RTOC', 'Dots (D)'):
            symbol["shadowStyle"] = QtCore.Qt.DotLine
        elif style == translate('RTOC', 'Strokes (S)'):
            symbol["shadowStyle"] = QtCore.Qt.DashLine
        elif style == translate('RTOC', 'D S'):
            symbol["shadowStyle"] = QtCore.Qt.DashDotLine
        elif style == translate('RTOC', 'D D S'):
            symbol["shadowStyle"] = QtCore.Qt.DashDotDotLine
        else:
            symbol["shadowStyle"] = 0

        symbol["alpha"] = self.alphaSpinBox.value()/100
        symbol["width"] = self.lineWidthSpinBox.value()
        symbol["shadowWidth"] = self.shadowWidthSpinBox.value()
        if self.lineColor is not None:
            symbol["color"] = self.lineColor

        symbol["shadowColor"] = self.shadowColor

        style = self.symbolComboBox.currentText()
        if style in [translate('RTOC', 'Rectangle'), translate('RTOC', 'Diamond')]:
            brush["style"] = "d"
        elif style == translate('RTOC', 'Circle'):
            brush["style"] = "o"
        elif style == "X":
            brush["style"] = "x"
        elif style == translate('RTOC', 'Square'):
            brush["style"] = "s"
        elif style == translate('RTOC', 'Triangle'):
            brush["style"] = "t"
        elif style == "Plus":
            brush["style"] = "+"
        else:
            brush["style"] = ""

        brush["size"] = self.symbolSizeSpinBox.value()

        if self.symbolColor is not None:
            brush["color"] = self.symbolColor

        if self.symbolPenColor is not None:
            brush["pen"] = self.symbolPenColor

        brush["fillLevel"] = self.fillLevel
        brush["fillBrush"] = self.fillColor

        return symbol, brush


def getStyle(plot):
    symbol = {}
    brush = {}

    opts = plot.opts

    symbol["style"] = opts['pen'].style()
    symbol["width"] = opts['pen'].width()
    symbol["color"] = opts['pen'].color().name()
    symbol["alpha"] = opts["alphaHint"]
    if opts['shadowPen'] is not None:
        symbol["shadowColor"] = opts['shadowPen'].color().name()
        symbol["shadowWidth"] = opts['shadowPen'].width()
        symbol["shadowStyle"] = opts['shadowPen'].style()
    else:
        symbol["shadowColor"] = None
        symbol["shadowWidth"] = 0
        symbol["shadowStyle"] = 0
        # 'shadowPen': None,
    brush["fillLevel"] = opts['fillLevel']
    if opts['fillBrush'] is not None:
        if type(opts['symbolBrush']) == tuple:
            brush["fillBrush"] = opts['fillBrush']
        else:
            brush["fillBrush"] = opts['fillBrush'].color().name()
            # 'fillBrush': None,

    brush["style"] = opts['symbol']
    brush["size"] = opts['symbolSize']
    if type(opts['symbolBrush']) == tuple:
        brush["color"] = opts['symbolBrush']
    else:
        brush["color"] = opts['symbolBrush'].color().name()

    if type(opts['symbolPen']) == tuple:
        brush["pen"] = opts['symbolPen']
    else:
        brush["pen"] = opts['symbolPen'].color().name()
    return symbol, brush


def setStyle(plot, symbol={}, brush={}):
    if symbol != {}:
        if "width" not in symbol.keys():
            symbol["width"] = define.defaultLineWidth
        if "style" not in symbol.keys():
            symbol["style"] = 1
        if "shadowWidth" not in symbol.keys():
            symbol["shadowWidth"] = None
        if "shadowStyle" not in symbol.keys():
            symbol["shadowStyle"] = None
        pen = pg.mkPen(color=symbol["color"], width=int(
            symbol["width"]), style=int(symbol["style"]))
        plot.setPen(pen)
        # logging.debug(symbol["style"])
        if symbol["shadowWidth"] is not None and symbol["shadowStyle"] is not None:
            plot.setShadowPen(color=symbol["shadowColor"], width=int(
                symbol["shadowWidth"]), style=int(symbol["shadowStyle"]), cosmetic=True)
        else:
            plot.setShadowPen(None)
    if "alpha" in symbol.keys():
        plot.setAlpha(symbol["alpha"], False)

    for key in brush.keys():
        if key == "style":
            if brush["style"] != "":
                plot.setSymbol(brush["style"])
            else:
                plot.setSymbol(None)
        elif key == "color":
            c = brush["color"]
            plot.setSymbolBrush(c)
        elif key == "size":
            plot.setSymbolSize(brush["size"])
        elif key == "fillLevel":
            plot.setFillLevel(brush["fillLevel"])
        elif key == "fillBrush":
            plot.setFillBrush(brush["fillBrush"])
        elif key == "pen":
            plot.setSymbolPen(brush["pen"])
