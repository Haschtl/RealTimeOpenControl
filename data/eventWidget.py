from PyQt5 import QtWidgets
from PyQt5 import uic
import datetime


class EventWidget(QtWidgets.QWidget):
    def __init__(self, logger):
        super(EventWidget, self).__init__()
        uic.loadUi("data/ui/eventWidget.ui", self)

        self.eventStartTimeEdit.dateTimeChanged.connect(self.filterEvents)
        self.eventEndTimeEdit.dateTimeChanged.connect(self.filterEvents)
        self.eventStartTimeEdit.hide()
        self.eventEndTimeEdit.hide()
        self.label.hide()
        self.label_3.hide()
        self.logger = logger
        self.events = []
        self.tableWidget.setSizeAdjustPolicy(
        QtWidgets.QAbstractScrollArea.AdjustToContents)
        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
    def filterEvents(self):
        pass

    def update(self, time, text, devicename, signalname):
        r = self.tableWidget.rowCount()+1
        self.events.append([datetime.datetime.fromtimestamp(time).strftime(self.tr("%H:%M:%S %d.%m.%Y")), text, devicename, signalname])
        #self.tableWidget.insertRow(r)
        self.tableWidget.setRowCount(r)
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
        self.setmydata()
        #self.tableWidget
        #self.tableWidget.resizeColumnsToContents()

    def setmydata(self):
        for n, event in enumerate(self.events):
            for m, item in enumerate(event):
                newitem = QtWidgets.QTableWidgetItem(item)
                self.tableWidget.setItem(n, m, newitem)
