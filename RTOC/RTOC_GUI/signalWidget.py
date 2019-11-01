from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
import pyqtgraph as pg
import random
import time
import os
import sys
from functools import partial
from datetime import timedelta
import traceback
import datetime
from PyQt5.QtCore import QCoreApplication

from ..lib import general_lib as lib
from .signalEditWidget import SignalEditWidget
from . import define as define
from ..lib import pyqt_customlib as pyqtlib
from .stylePlotGUI import setStyle as setPlotStyle
from .stylePlotGUI import getStyle as getPlotStyle
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


def mouseClickEventPlotCurveItem(self, ev):
    if ev.button() != QtCore.Qt.LeftButton:
        return
    ev.accept()
    self.sigClicked.emit(self)


def widgets_at(pos):
    """Return ALL widgets at `pos`

    Arguments:
        pos (QPoint): Position at which to get widgets

    """

    widgets = []
    widget_at = QtWidgets.qApp.widgetAt(pos)

    while widget_at:
        widgets.append(widget_at)

        # Make widget invisible to further enquiries
        widget_at.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        widget_at = QtWidgets.qApp.widgetAt(pos)

    # Restore attribute
    for widget in widgets:
        widget.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)

    return widgets


class QLine(QtWidgets.QLabel):
    def __init__(self):
        super(QLine, self).__init__()
        p = QtGui.QPixmap(20, 20)
        bgcolor = QtGui.QColor('black')
        bgcolor.setAlpha(0)
        p.fill(bgcolor)
        painter = QtGui.QPainter(p)
        line = QtCore.QLineF(20, 20, 0, 0)
        painter.drawLine(line)
        painter.end()
        self.setPixmap(p)
        self.setMinimumWidth(20)
        self.setMinimumHeight(20)

    def styleIt(self, symbol={}, brush={}):
        p = QtGui.QPixmap(20, 20)
        bgcolor = QtGui.QColor('black')
        bgcolor.setAlpha(0)
        p.fill(bgcolor)
        painter = QtGui.QPainter(p)
        line = QtCore.QLineF(0, 10, 20, 10)
        if symbol != {}:
            if "width" not in symbol.keys():
                symbol["width"] = define.defaultLineWidth
            if "style" not in symbol.keys():
                symbol["style"] = 1
            if "shadowWidth" not in symbol.keys():
                symbol["shadowWidth"] = None
            if "shadowStyle" not in symbol.keys():
                symbol["shadowStyle"] = None
            pen = QtGui.QPen(int(symbol["style"]))
            color = QtGui.QColor(symbol["color"])
            color.setAlpha(int(symbol["alpha"]*255))
            pen.setColor(color)
            pen.setWidthF(int(symbol["width"]))
            painter.setPen(pen)

        painter.drawLine(line)
        painter.end()
        self.setPixmap(p)


class MyLabel(QtWidgets.QLabel):
    def __init__(self, text):
        super().__init__(text)

    def _set_color(self, col):

        palette = self.palette()
        palette.setColor(self.foregroundRole(), col)
        self.setPalette(palette)

    color = QtCore.pyqtProperty(QtGui.QColor, fset=_set_color)


class AnimationThread(QtCore.QThread):
    window_update_request = QtCore.pyqtSignal(bool)

    def __init__(self):
        QtCore.QThread.__init__(self)
        self.thread_must_be_run = True
        self.mutex = QtCore.QMutex()
        # print " thread init done "

    def stop_this_thread(self):
        self.thread_must_be_run = False

    def run(self):
        self.mutex.lock()
        self.window_update_request.emit(True)
        self.mutex.unlock()
        time.sleep(define.blinkingIdentifier)
        self.window_update_request.emit(False)


class AnimatedWidget(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)

    def getBackColor(self):
        return self.palette().color(QtGui.QPalette.Background)

    def anim(self):
        self.color_anim = QtCore.QPropertyAnimation(self, b'backColor')
        color1 = QtGui.QColor(255, 0, 0)
        color2 = QtGui.QColor(0, 255, 0)
        self.color_anim.setStartValue(color1)
        self.color_anim.setKeyValueAt(0.5, color2)
        self.color_anim.setEndValue(color1)
        self.color_anim.setDuration(1000)
        self.color_anim.setLoopCount(1)
        self.color_anim.start()

    def setBackColor(self, color):
        pal = self.palette()
        pal.setColor(QtGui.QPalette.Background, color)
        self.setPalette(pal)

    backColor = QtCore.pyqtProperty(QtGui.QColor, getBackColor, setBackColor)


# class SignalWidget(QtWidgets.QToolButton):
class SignalWidget(QtWidgets.QWidget):
    def __init__(self, plotWidget, logger, devicename, signalname, id, unit, remotehost=None):
        super(SignalWidget, self).__init__()
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)

        if getattr(sys, 'frozen', False):
            # frozen
            self.packagedir = os.path.dirname(sys.executable)+'/RTOC/RTOC_GUI'
        else:
            # unfrozen
            self.packagedir = os.path.dirname(os.path.realpath(__file__))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        # self.legend = QtWidgets.QLabel('-')
    #    self.legend.setSizePolicy(sizePolicy)
        self.visibleIcon = QtWidgets.QLabel(self)
        self.visibleIcon.setGeometry(0, 0, 5, 5)
        #self.icon.setGeometry(0, 0, 10, 10)
        #use full ABSOLUTE path to the image, not relative
        pixmap = QtGui.QPixmap(self.packagedir + "/ui/icons/visible.png")
        pixmap = pixmap.scaledToHeight(20)
        self.visibleIcon.setPixmap(pixmap)
        self.visibleIcon.setSizePolicy(sizePolicy)
        self.legend2 = QLine()
        self.button = QtWidgets.QToolButton()  # QPushButton()
        self.text = QtWidgets.QLabel(signalname)
        # self.layout.addWidget(self.legend)
        self.layout.addWidget(self.visibleIcon)
        self.layout.addWidget(self.legend2)
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.text)
        self.visibleIcon.show()
        self.clicked = self.button.clicked

        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.setSizePolicy(sizePolicy)
        self.button.setSizePolicy(sizePolicy)
        self.setCheckable(True)

        self.clicked.connect(self.toggleSignal)
        #self.setStyleSheet("QToolButton{background-color: rgb(44, 114, 29)}")

        self.hidden = False
        self.logger = logger
        self.plotWidget = plotWidget
        self.devicename = devicename
        self.signalname = signalname
        self.unit = unit
        self.id = id
        self.active = True
        self.showEvents = True
        # self.signalTimeOut = define.signalTimeOut
        self.signalTimeOut = self.logger.config['GUI']['signalInactivityTimeout']
        self.style = {}
        self.xTimeBase = self.plotWidget.xTimeBase
        self.events = []
        self.eventItems = []

        self.animation_thread = AnimationThread()
        self.animation_thread.window_update_request.connect(self.blinkLabel)

        self.initLabel()
        if self.signalname in lib.column(self.logger.database.signalNames(), 1) and False:
            self.legendName = signalname+" ["+unit+"]"
        else:
            self.legendName = devicename+"."+signalname+" ["+unit+"]"
        self.plot = pg.PlotDataItem(x=[], y=[], name=self.legendName)

        # REMOVE THIS PART IF ITS TOO SLOW
        self.display_text = pg.TextItem(text='', color=(
            200, 200, 200), fill=(200, 200, 200, 50), anchor=(1, 1))
        self.display_text.hide()
        self.plotWidget.plot.addItem(self.display_text,  ignoreBounds=True)
        self.plotWidget.plot.scene().sigMouseMoved.connect(self.onMove)

        self.plotWidget.legend.addItem(self.plot, self.legendName)
        symbol, brush = self.findStyle()
        self.plot.curve.setClickable(True)
        self.plot.curve.sigClicked.connect(
            partial(self.plotWidget.signalClickedAction, self.devicename, self.signalname))
        setPlotStyle(self.plot, symbol, brush)

        self.labelItem = pg.TextItem(devicename+"."+signalname,
                                     color=symbol["color"], html=None, anchor=(0, 0.5))
        self.labelItem.setPos(0, 0)

        self.initMenu()
        self.editWidget.xTimeBaseButton.setChecked(self.xTimeBase)
        self.editWidget.labelButton.setChecked(
            self.plotWidget.plotViewWidget.labelButton.isChecked())
        # if self.plotWidget.plotViewWidget.labelButton.isChecked():
        if self.logger.config['GUI']['plotLabelsEnabled']:
            self.labelItem.hide()
        self.editWidget.toggleLabel()

        self.signalModifications = [0, 0, 1, 1]

        self.updateLegend()
        self.setText(signalname)
        self.toggleSignal()
        self.setChecked(logger.config['GUI']['autoShowGraph'])
        self.remoteHost = None

        if remotehost is not None:
            self.remoteHost = remotehost

        #self.treeWidget.mousePressEvent = self.mousePressEventTreeWidget
        #self.treeWidget.itemClicked.connect(self.signalClicked)
        #self.treeWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        #self.treeWidget.customContextMenuRequested.connect(self._open_menu)

    # def signalClicked(self, event):
    #     self.toggleDevice(event.child(0), event)
    #
    # def _open_menu(self, lisi):
    #     print(lisi)
    #     indexes = self.treeWidget.selectedIndexes()
    #     print(indexes)
    #     print(indexes[0].model())
    #     for ix in self.treeWidget.selectedIndexes():
    #         text = ix.data() # or ix.data()
    #         print(text)
    #     if len(indexes) == 0:
    #         return

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:

            pos = self.text.mapToGlobal(self.visibleIcon.pos())
            x = pos.x()
            y = pos.y()
            diff = self.frameGeometry().width()
            self.button.menu().show()
            self.button.menu().move(x-diff+40,y+20)
        # elif event.button() == QtCore.Qt.LeftButton:
        else:
            if self.isChecked():
                self.button.setChecked(False)
            else:
                self.button.setChecked(True)
            self.toggleSignal()
        QtWidgets.QWidget.mousePressEvent(self, event)

    def setCheckable(self, value):
        self.button.setCheckable(value)

    def setText(self, signalname):
        self.button.setText(signalname)
        self.text.setText(signalname)

    def setChecked(self, value):
        self.button.setChecked(value)
        self.toggleSignal()

    def isChecked(self):
        return self.button.isChecked()
    # def setSizePolicy(self, policy):
    #    self.button.setSizePolicy(policy)

    def menu(self):
        return self.button.menu()

    # def setStyleSheet(self, stylesheet):
    #     self.button.setStyleSheet(stylesheet)

    def setMinimumHeight(self, height):
        self.button.setMinimumHeight(height)

    def setMaximumHeight(self, height):
        self.button.setMaximumHeight(height)

    def updateLegend(self):
        symbol, brush = getPlotStyle(self.plot)
        self.legend2.styleIt(symbol, brush)

    def toggleEditWidget(self, value=None):
        if value:
            self.editWidget.show()
        else:
            self.editWidget.hide()

    def setLegendType(self, line='-', symbol=''):
        if line == 1 or line == 0:
            line = '_'
        elif line == 2:
            line = '-'
        elif line == 3:
            line = '.'
        elif line == 4:
            line = '-.'
        elif line == 5:
            line = '-..'
        else:
            line = ''
        if symbol is None:
            symbol = ""
        # else:
        #    symbol = ''
        self.legend.setText(line+symbol+line)

    def setLegendColor(self, color, bgcolor=None):
        if bgcolor is None:
            self.legend.setStyleSheet(
                "QLabel { background-color : "+str(color)+"; color : "+str(color)+"; }")
        else:
            self.legend.setStyleSheet(
                "QLabel { background-color : "+str(bgcolor)+"; color : "+str(color)+"; }")

    def onMove(self, pos):
        act_pos = self.plot.mapFromScene(pos)
        p1 = self.plot.scatter.pointsAt(act_pos)
        if len(p1) != 0:
            x, y = p1[0].pos()
            # logging.debug(x)
            self.display_text.setText(self.devicename+'.'+self.signalname+'\nx=%f\ny=%f' % (x, y))
            self.display_text.setPos(x, y)
            self.display_text.show()
        else:
            self.display_text.hide()

    def findStyle(self):
        for signal in self.plotWidget.plotStyles.keys():
            if signal == str(self.devicename)+"."+str(self.signalname):
                symbol = self.plotWidget.plotStyles[signal]["symbol"]
                brush = self.plotWidget.plotStyles[signal]["brush"]
                return symbol, brush
        else:
            symbol = {}
            brush = {}

            def r(): return random.randint(0, 255)
            symbol["color"] = '#%02X%02X%02X' % (r(), r(), r())
            symbol["width"] = define.defaultLineWidth

            self.plotWidget.plotStyles[str(self.devicename)+"."+str(self.signalname)] = {}
            self.plotWidget.plotStyles[str(self.devicename) + "."+str(self.signalname)]["symbol"] = symbol
            self.plotWidget.plotStyles[str(self.devicename) + "."+str(self.signalname)]["brush"] = {}

            return symbol, brush

    def initMenu(self):
        self.button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.button.setMenu(QtWidgets.QMenu(self.button))
        action = QtWidgets.QWidgetAction(self)
        self.editWidget = SignalEditWidget(self, self.id, self.plotWidget)
        action.setDefaultWidget(self.editWidget)
        self.button.menu().addAction(action)
        self.button.hide()

    def newDataIncoming(self):
        signal = self.logger.database.getSignal(self.id)
        if signal is None or signal == []:
            return
        clock = list(signal[2])
        y = list(signal[3])
        if len(clock) > 0 and len(y) > 0:
            self.updateLabel(clock, y, signal[4])

        if self.plotWidget.plotViewWidget.blinkingButton.isChecked():
            self.animation_thread.start()

    def blinkLabel(self, value):
        if value is True:
            self.label.setStyleSheet("background-color: rgb(25, 98, 115)")
        else:
            self.label.setStyleSheet("background-color: #232629")

    def initLabel(self):
        self.label = MyLabel("")

        self.anim = QtCore.QPropertyAnimation(self.label, b"color")
        self.anim.setDuration(1)
        self.anim.setLoopCount(1)
        self.anim.setStartValue(QtGui.QColor(0, 0, 0))
        self.anim.setEndValue(QtGui.QColor(255, 255, 255))

    def rename(self, name):
        self.setText(name)
        self.signalname = name
        self.labelItem.setText(name)

    def createToolTip(self, id, xdata):
        if len(xdata) > 0:
            maxduration = self.calcDuration(list(xdata))
            duration = xdata[-1]-xdata[0]
            try:
                # if self.logger.config['postgresql']['active']:
                #     line1 = translate('RTOC', 'Duration: ')+str(timedelta(seconds=duration))
                #     line2 = translate('RTOC', 'Values: ')+str(len(list(xdata)))
                # else:
                line1 = translate('RTOC', 'Duration: {}/~{}').format(str(timedelta(seconds=round(duration))), str(timedelta(seconds=round(maxduration))))
                line2 = translate('RTOC', 'Values: {}/{}').format(len(list(xdata)), str(self.logger.config['global']['recordLength']))
                count = 20
                if len(xdata) <= count:
                    count = len(xdata)
                if count > 1:
                    meaner = list(xdata)[-count:]
                    diff = 0
                    # for idx, m in enumerate(meaner[:-1]):
                    #     diff += meaner[idx+1]-m
                    diff = meaner[-1]-meaner[0]
                    diff2 = xdata[-1]-xdata[0]
                    if diff != 0:
                        latestSamplerate = str(round((len(meaner)-1)/diff, 2))
                        samplerate = str(round((len(xdata)-1)/diff2, 2))
                    else:
                        latestSamplerate = "?"
                        samplerate = "?"
                else:
                    latestSamplerate = "?"
                    samplerate = "?"
                line3 = translate('RTOC', 'Samplerate (latest): {} ({}) Hz').format(samplerate, latestSamplerate)
                return self.devicename+'.'+self.signalname+'\n'+line1+"\n"+line2 + "\n" + line3
            except Exception:
                logging.debug(traceback.format_exc())
                print(traceback.format_exc())
                return "Tooltip failed"
        else:
            return "Signal empty"

    def updateLabel(self, x, y, current_unit):
        if len(y) > 0:
            current_signal = y[-1]
            self.setText(self.signalname)
            self.label.setText(str(round(current_signal, 5))+" "+str(current_unit))

            self.setToolTip(self.createToolTip(self.id, x))

        delayed = time.time() - x[-1]
        if delayed >= self.signalTimeOut and self.label.styleSheet() != "background-color: rgb(113, 100, 29)":
            self.label.setStyleSheet("background-color: rgb(113, 100, 29)")
        elif delayed < self.signalTimeOut and self.label.styleSheet() == "background-color: rgb(113, 100, 29)":
            self.label.setStyleSheet("background-color: #232629")

    def updateEvents(self, offsetX, offsetY, scaleX, scaleY, ctime, current_time):
        found_ids = []
        for idx0, e in enumerate(self.plotWidget.self.eventWidget.events):
        # priority, time("%H:%M:%S %d.%m.%Y", text, devicename, signalname, value, id
            event = [e[1], e[2], e[0], e[5], e[6], e[3], e[4], e[7]]
            oldEvent = False
            if event[6] == self.signalname and event[5] == self.devicename:
                event[0] = float(datetime.datetime.strptime(event[0], '%H:%M:%S %d.%m.%Y').timestamp())
                for idx, eventItem in enumerate(self.eventItems):
                    if eventItem.id == event[7]:
                        # wenn schon geplottet, dann position anpassen
                        pos = scaleX*(event[0]-ctime+offsetX)
                        eventItem.setPos(pos, 0)
                        self.eventItems[idx].vLine.setPos(pos)
                        oldEvent = True
                        found_ids.append(event[7])
                        break
                if not oldEvent:
                    eventItem = pg.TextItem(str(event[1]), color=(
                        200, 200, 200), html=None, anchor=(0, 0.5))
                    eventItem.setPos(event[0]-current_time, 0)
                    eventItem.vLine = pg.InfiniteLine(angle=90, movable=False)
                    eventItem.id = event[7]
                    self.eventItems.append(eventItem)
                    idx = len(self.eventItems)-1
                    self.plotWidget.plot.addItem(eventItem,  ignoreBounds=True)
                    self.plotWidget.plot.addItem(
                        self.eventItems[idx].vLine, ignoreBounds=True)
                    if self.showEvents and self.logger.config['GUI']['showEvents']:
                        pass
                        logging.debug('NOT HIDDEN')
                    else:
                        self.eventItems[idx].hide()
                        self.eventItems[idx].vLine.hide()
                        logging.debug('HIDDEN')

        for idx, eventItem in enumerate(self.eventItems):
            if eventItem.id not in found_ids:
                # if not delete in database
                self.eventItems[idx].hide()
                self.eventItems[idx].vLine.hide()
                logging.debug('Not deleted, but hidden')

    def updatePlot(self):
        current_time = time.time()
        if self.active:
            offsetX = self.signalModifications[0]
            offsetY = self.signalModifications[1]
            scaleX = self.signalModifications[2]
            scaleY = self.signalModifications[3]
        # else:
        #     offsetX = 0
        #     offsetY = 0
        #     scaleX = 1
        #     scaleY = 1

            if self.plotWidget.active and self.xTimeBase:
                ctime = current_time - self.plotWidget.globalXOffset
            elif self.xTimeBase:
                ctime = self.plotWidget.lastActive - self.plotWidget.globalXOffset
            else:
                ctime = 0 - self.plotWidget.globalXOffset

            signal = self.logger.database.getSignal(self.id)
            if signal is None or signal == []:
                return
            clock = list(signal[2])
            y = list(signal[3])
            # if self.logger.getEvents(self.id) == []:
            #     # logging.error('COULD NOT DELETE EVENTS FOR SIGNAL ID: '+str(self.id))
            #     # logging.info('')
            #     pass
            # else:
            self.updateEvents(offsetX, offsetY, scaleX, scaleY, ctime, current_time)
            if len(clock) > 0 and len(y) > 0:
                self.updateLabel(clock, y, signal[4])
                if self.active:
                    # if clock[len(clock)-1] <= current_time+10000 and clock[len(clock)-1] > current_time-10000:
                    if self.logger.config['GUI']['xRelative']:
                        for idx2 in range(len(clock)):
                            clock[idx2] = scaleX*(clock[idx2]-ctime+offsetX)
                        data = y
                        data = [scaleY*(y+offsetY) for y in data]
                        if len(clock) == len(data):
                            if self.editWidget.xySwapButton.isChecked():
                                temp = data
                                data = clock
                                clock = temp
                            # if self.logger.config['postgresql']['active'] and len(data) > self.logger.config['global']['recordLength']:
                            #     start = len(data) - self.logger.config['global']['recordLength']
                            #     clock = clock[start:-1]
                            #     data = data[start:-1]
                            self.plot.setData(x=list(clock), y=list(data))
                            self.labelItem.setPos(clock[-1], data[-1])
                        else:
                            logging.error(self.devicename+"."+self.signalname+": len(x) != len(y)")
                    else:
                        data = y
                        data = [scaleY*(y+offsetY) for y in data]
                        clockx = [scaleX*(x+offsetX)-self.plotWidget.globalXOffset for x in clock]
                        if len(clock) == len(data):
                            if self.editWidget.xySwapButton.isChecked():
                                temp = data
                                data = clockx
                                clockx = temp
                            # if self.logger.config['postgresql']['active'] and len(data) > self.logger.config['global']['recordLength']:
                            #     start = len(data) - self.logger.config['global']['recordLength']
                            #     clockx = clock[start:-1]
                            #     data = data[start:-1]
                            self.plot.setData(x=clockx, y=data)
                            self.labelItem.setPos(clockx[-1], data[-1])
                        else:
                            logging.error(self.devicename+"."+self.signalname+": len(x) != len(y)")

    def toggleSignal(self):
        if self.isChecked() and not self.hidden:
            self.active = True
            self.plotWidget.legend.addItem(
                self.plot, self.legendName)
            #self.setStyleSheet("background-color: rgb(44, 114, 29)")
            pixmap = QtGui.QPixmap(self.packagedir + "/ui/icons/visible.png")

            pixmap = pixmap.scaledToHeight(20)
            self.visibleIcon.setPixmap(pixmap)
            #
            # self.visibleIcon.show()
            self.labelItem.show()
            self.updatePlot()
            if self.showEvents and self.logger.config['GUI']['showEvents']:
                for event in self.eventItems:
                    event.show()
                    event.vLine.show()
        else:
            self.active = False
            self.plot.clear()
            self.plotWidget.legend.removeItem(self.legendName)
            pixmap = QtGui.QPixmap(self.packagedir + "/ui/icons/invisible.png")

            pixmap = pixmap.scaledToHeight(20)
            self.visibleIcon.setPixmap(pixmap)
            self.labelItem.hide()
            for event in self.eventItems:
                event.hide()
                event.vLine.hide()

    def remove(self, cb=True, total=True, force = True):
        database = False
        if self.logger.config['postgresql']['active'] and not force:
            database = pyqtlib.alert_message(translate('RTOC', 'Remove from database'), translate('RTOC', 'Do you want to remove that signal from the database, too?'), translate('RTOC', 'The events that are assigned to the signal are also deleted.'))
        self.plotWidget.legend.removeItem(self.legendName)
        if total:
            self.logger.database.removeSignal(self.id, None, None, database)
        self.labelItem.hide()
        self.button.menu().hide()
        # self.editWidget.hide()
        self.hide()
        self.close()

        for item in self.eventItems:
            self.plotWidget.plot.getPlotItem().removeItem(item.vLine)
            self.plotWidget.plot.getPlotItem().removeItem(item)

        self.eventItems = []
        self.events = []
        self.plot.clear()
        if cb:
            self.plotWidget.removeSignal(self.id, self.devicename, self.signalname)

    def closeEvent(self, event, *args, **kwargs):
        super(SignalWidget, self).closeEvent(event)

    def calcDuration(self, x):
        if len(x) > 2:
            dt = x[-1]-x[0]
            length = len(x)
            maxlen = self.logger.config['global']['recordLength']
            return dt/length*maxlen
        else:
            return -1

    def toggleEvents(self, value):
        if value:
            self.showEvents = True
            for event in self.eventItems:
                event.show()
                event.vLine.show()
        else:
            self.showEvents = False
            for event in self.eventItems:
                event.hide()
                event.vLine.hide()
