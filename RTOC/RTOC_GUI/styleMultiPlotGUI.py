from PyQt5 import uic
from PyQt5 import QtWidgets
import os
import sys

from .stylePlotGUI import plotStyler
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)


class plotMultiStyler(QtWidgets.QDialog):
    def __init__(self, signalnames, plots=[], logger=None):
        super(plotMultiStyler, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/RTOC_GUI'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/ui/stylePlotDialog.ui", self)
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

        # self.show()

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
            idx = self.logger.database.getSignalID(signalname.split(".")[0], signalname.split(".")[1])
            if idx != -1:
                self.styler.setStyleAction(self.plots[idx])
