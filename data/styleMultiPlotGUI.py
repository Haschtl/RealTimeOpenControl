from PyQt5 import QtCore
from PyQt5 import uic
from PyQt5 import QtWidgets, QtGui
import pyqtgraph as pg
from functools import partial

from data.stylePlotGUI import plotStyler

class plotMultiStyler(QtWidgets.QDialog):
    def __init__(self, signalnames, plots=[], logger=None):  # + (filepath, known_values)
        super(plotMultiStyler, self).__init__()
        uic.loadUi("data/ui/stylePlotDialog.ui", self)
        self.setCallbacks()

        self.logger = logger
        self.plots = plots
        self.lineColor = None
        self.fillLevel = None
        self.symbolColor = None
        self.listWidget.clear()
        self.styler = plotStyler(plots[0])
        self.stylerLayout.addWidget(self.styler)
        for signal in signalnames:
            text = ".".join(signal)
            self.listWidget.addItem(text)

        #self.show()

    def setCallbacks(self):
        self.cancelButton.clicked.connect(self.close)
        self.styleSelectedButton.clicked.connect(self.styleSelected)
        self.styleAllButton.clicked.connect(self.styleAll)

    def styleAll(self):
        for plot in self.plots:
            self.styler.setStyleAction(plot)
        self.close()

    def styleSelected(self):
        for selectedSignal in self.listWidget.selectedItems():
            signalname = selectedSignal.text()
            idx = self.logger.getSignalId(signalname.split(".")[0], signalname.split(".")[1])
            if idx != -1:
                #symbol, brush = self.styler.getStyle()
                self.styler.setStyleAction(self.plots[idx])
