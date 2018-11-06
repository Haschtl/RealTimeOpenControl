from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import uic
import datetime


class EventWidget(QtWidgets.QWidget):
    def __init__(self, logger):
        super(EventWidget, self).__init__()
        uic.loadUi("data/ui/eventWidget.ui", self)

        self.logger = logger
        self.events = []
        self.tableWidget.setSizeAdjustPolicy(
        QtWidgets.QAbstractScrollArea.AdjustToContents)
        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)

        self.filterEdit.textChanged.connect(self.setmydata)
        self.highButton.clicked.connect(self.setmydata)
        self.middleButton.clicked.connect(self.setmydata)
        self.lowButton.clicked.connect(self.setmydata)
        self.clearButton.clicked.connect(self.clear)

    def clear(self):
        self.events = []
        self.setmydata()

    def update(self, time, text, devicename, signalname, priority):
        self.events.append([priority, datetime.datetime.fromtimestamp(time).strftime(self.tr("%H:%M:%S %d.%m.%Y")), text, devicename, signalname])
        #self.tableWidget.insertRow(r)

        #self.tableWidget.setVerticalHeaderItem(r, QtWidgets.QTableWidgetItem(str(r)))
        #newitem = QtWidgets.QTableWidgetItem(datetime.datetime.fromtimestamp(time).strftime(self.tr("%H:%M:%S %d.%m.%Y")))
        # newitem = QtWidgets.QTableWidgetItem("Test")
        # self.tableWidget.setItem(r, 0, newitem)
        # newitem = QtWidgets.QTableWidgetItem(text)
        # self.tableWidget.setItem(r, 1, newitem)
        # newitem = QtWidgets.QTableWidgetItem(devicename)
        # self.tableWidget.setItem(r, 2, newitem)
        # newitem = QtWidgets.QTableWidgetItem(signalname)
        # self.tableWidget.setItem(r, 3, newitem)
        # self.tableWidget.viewport().update()
        events = self.setmydata()
        #self.tableWidget
        #self.tableWidget.resizeColumnsToContents()

    def setmydata(self):
        events = self.filterEvents(self.events)
        self.tableWidget.setRowCount(0);
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
                    #self.tableWidget.item(l-n, m-1).setBackground(color)
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
                if text.replace(" ","") == "" or text.lower() in " ".join(event[1:]).lower():
                    filteredEvents.append(event)
        return filteredEvents
