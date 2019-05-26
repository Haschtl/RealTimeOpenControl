from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import uic
import os
import sys
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)


class GlobalEventWidget(QtWidgets.QWidget):
    refresh = QtCore.pyqtSignal()

    def __init__(self, logger):
        super(GlobalEventWidget, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/RTOC_GUI'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/ui/globalEventWidget.ui", self)

        self.logger = logger
