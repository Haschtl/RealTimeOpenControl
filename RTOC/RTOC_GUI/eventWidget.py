from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import uic
import datetime
import os
import sys

# from .globalActionWidget import GlobalActionWidget
# from .globalEventWidget import GlobalEventWidget
from ..lib import pyqt_customlib as pyqtlib
import logging as log

log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

if True:
    translate = QtCore.QCoreApplication.translate

    def _(text):
        return translate('rtoc', text)
else:
    import gettext
    _ = gettext.gettext


class EventWidget(QtWidgets.QWidget):
    refresh = QtCore.pyqtSignal()

    def __init__(self, parent, logger):
        super(EventWidget, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/RTOC_GUI'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/ui/eventWidget.ui", self)
        self.toolBox.hide()
        self.parent = parent
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

        # self.globalActionWidget = GlobalActionWidget(logger)
        # self.globalEventWidget = GlobalEventWidget(logger)
        # self.globalEventLayout_2.addWidget(self.globalEventWidget)
        # self.globalActionLayout.addWidget(self.globalActionWidget)

        self.updateAllEvents()

    def clear(self):
        self.events = []
        self.setmydata()
        database = False
        if self.logger.config['postgresql']['active']:
            database = pyqtlib.alert_message(translate('RTOC', 'Delete from database'), translate('RTOC', 'Do you also remove the events from the database?'), translate('RTOC', 'Signals will remain'), "", translate('RTOC', "Yes"), translate('RTOC', "No"))
        self.logger.database.clear(False, False, True, database)

    def updateAllEvents(self):
        self.events = []
        if self.logger.database is not None:
            for evID in self.logger.database.events().keys():
                event = self.logger.database.events()[evID]
                # [DEVICE_ID,SIGNAL_ID,EVENT_ID,TEXT,TIME,VALUE,PRIORITY]
                # TIME, TEXT, PRIORITY, VALUE, EVENT_ID, DEVICE_ID, SIGNAL_ID
                name = self.logger.database.getEventName(evID)
                self.update(event[4], event[3], name[0], name[1], event[6], event[5], event[2], evID)
        # else:
            # print('NOT UPDATING EVENT_WIDGET FROM DATABASE')

    def update(self, time, text, devicename, signalname, priority, value, id, event_id):
        try:
            timestr = datetime.datetime.fromtimestamp(time).strftime("%H:%M:%S %d.%m.%Y")
        except Exception:
            logging.warning('Translation error')
            timestr = datetime.datetime.fromtimestamp(time).strftime("%H:%M:%S %d.%m.%Y")
        # print(timestr)
        self.events.append([priority, str(timestr), text, devicename, signalname, value, id, event_id])

        self.refresh.emit()

    def setmydata(self):
        events = self.filterEvents(self.events)
        self.tableWidget.setRowCount(0)
        self.tableWidget.setRowCount(len(events))
        self.tableWidget.setSortingEnabled(False)
        evLen = len(events)-1
        for n, event in enumerate(events):
            if event[0] == 2:
                color = QtGui.QColor(177, 19, 19)
            elif event[0] == 1:
                color = QtGui.QColor(198, 131, 40)
            else:
                color = QtGui.QColor(198, 131, 40)
                color.setAlpha(0)
            for m, item in enumerate(event):
                if m != 0 and m != 7:
                    # print(item)
                    newitem = QtWidgets.QTableWidgetItem(item)
                    newitem.setBackground(color)
                    self.tableWidget.setItem(evLen-n, m-1, newitem)
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
