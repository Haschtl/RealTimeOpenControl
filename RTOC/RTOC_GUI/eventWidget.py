from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import uic
import datetime
import os
import sys


class EventWidget(QtWidgets.QWidget):
    refresh = QtCore.pyqtSignal()

    def __init__(self, logger):
        super(EventWidget, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/data'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/ui/eventWidget.ui", self)

        self.logger = logger
        self.events = []
        self.tableWidget.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.AdjustToContents)
        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.filterEdit.textChanged.connect(self.setmydata)
        self.highButton.clicked.connect(self.setmydata)
        self.middleButton.clicked.connect(self.setmydata)
        self.lowButton.clicked.connect(self.setmydata)
        self.clearButton.clicked.connect(self.clear)
        self.refresh.connect(self.setmydata,  QtCore.Qt.QueuedConnection)

    def clear(self):
        self.events = []
        self.setmydata()

    def update(self, time, text, devicename, signalname, priority, value, id):
        self.events.append([priority, datetime.datetime.fromtimestamp(time).strftime(
            self.tr("%H:%M:%S %d.%m.%Y")), text, devicename, signalname, value, id])

        self.refresh.emit()

    def setmydata(self):
        events = self.filterEvents(self.events)
        self.tableWidget.setRowCount(0)
        self.tableWidget.setRowCount(len(events))
        self.tableWidget.setSortingEnabled(False)
        l = len(events)-1
        for n, event in enumerate(events):
            if event[0] == 2:
                color = QtGui.QColor(177, 19, 19)
            elif event[0] == 1:
                color = QtGui.QColor(198, 131, 40)
            else:
                color = QtGui.QColor(198, 131, 40)
                color.setAlpha(0)
            for m, item in enumerate(event):
                if m != 0:
                    newitem = QtWidgets.QTableWidgetItem(item)
                    newitem.setBackground(color)
                    self.tableWidget.setItem(l-n, m-1, newitem)
        self.tableWidget.setSortingEnabled(True)

        return events

    def filterEvents(self, events):
        priorities = []
        if self.lowButton.isChecked():
            priorities.append(0)
        if self.middleButton.isChecked():
            priorities.append(1)
        if self.highButton.isChecked():
            priorities.append(2)

        text = self.filterEdit.text()

        filteredEvents = []
        for idx, event in enumerate(events):
            if event[0] in priorities:
                # " ".join(event[1:]).lower():
                if text.replace(" ", "") == "" or text.lower() in str(event[1:]).lower():
                    filteredEvents.append(event)
        return filteredEvents
