from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
import pyqtgraph as pg
import random
import time
from functools import partial

from .lib import general_lib as lib
from .signalEditWidget import SignalEditWidget
from . import define as define
from .stylePlotGUI import setStyle as setPlotStyle


def mouseClickEventPlotCurveItem(self, ev):
    if ev.button() != QtCore.Qt.LeftButton:
        return
    ev.accept()
    self.sigClicked.emit(self)


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


class SignalWidget(QtWidgets.QToolButton):
    def __init__(self, plotWidget, logger, devicename, signalname, id, unit):
        super(SignalWidget, self).__init__()
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.setSizePolicy(sizePolicy)
        self.setCheckable(True)

        self.setText(signalname)
        self.setChecked(True)
        self.clicked.connect(self.toggleSignal)
        self.setStyleSheet("QToolButton{background-color: rgb(44, 114, 29)}")

        self.hidden = False
        self.logger = logger
        self.plotWidget = plotWidget
        self.devicename = devicename
        self.signalname = signalname
        self.unit = unit
        self.id = id
        self.active = True
        self.showEvents = True
        self.signalTimeOut = define.signalTimeOut
        self.style = {}
        self.xTimeBase = self.plotWidget.xTimeBase
        self.events = []
        self.eventItems = []

        self.animation_thread = AnimationThread()
        self.animation_thread.window_update_request.connect(self.blinkLabel)

        self.initLabel()
        if self.signalname in lib.column(self.logger.signalNames, 1) and False:
            self.legendName = signalname+" ["+unit+"]"
        else:
            self.legendName = devicename+"."+signalname+" ["+unit+"]"
        self.plot = pg.PlotDataItem(x=[], y=[], name=self.legendName)

        # REMOVE THIS PART IF ITS TOO SLOW
        self.display_text = pg.TextItem(text='', color=(
            200, 200, 200), fill=(200, 200, 200, 50), anchor=(1, 1))
        self.display_text.hide()
        self.plotWidget.plot.addItem(self.display_text)
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
        if self.plotWidget.plotViewWidget.labelButton.isChecked():
            self.labelItem.hide()
        self.editWidget.toggleLabel()

        self.signalModifications = [0, 0, 1, 1]

    def onMove(self, pos):
        act_pos = self.plot.mapFromScene(pos)
        p1 = self.plot.scatter.pointsAt(act_pos)
        if len(p1) != 0:
            x, y = p1[0].pos()
            print(x)
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
            return symbol, brush

    def initMenu(self):
        self.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.setMenu(QtWidgets.QMenu(self))
        action = QtWidgets.QWidgetAction(self)
        self.editWidget = SignalEditWidget(self, self.id, self.plotWidget)
        action.setDefaultWidget(self.editWidget)
        self.menu().addAction(action)

    def newDataIncoming(self):
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

    def createToolTip(self, id):
        maxduration = self.calcDuration(list(self.logger.getSignal(id)[0]))
        duration = self.logger.getSignal(id)[0][-1]-self.logger.getSignal(id)[0][0]
        try:
            line1 = time.strftime("%H:%M:%S", time.gmtime(int(duration))) + \
                "/~"+time.strftime("%H:%M:%S", time.gmtime(int(maxduration)))
            line2 = str(
                len(list(self.logger.getSignal(id)[0])))+"/"+str(self.logger.maxLength)
            count = 20
            if len(self.logger.getSignal(id)[0]) <= count:
                count = len(self.logger.getSignal(id)[0])
            if count > 1:
                meaner = list(self.logger.getSignal(id)[0])[-count:]
                diff = 0
                for idx, m in enumerate(meaner[:-1]):
                    diff += meaner[idx+1]-m
                if diff != 0:
                    line3 = str(round((len(meaner)-1)/diff, 2))+" Hz"
                else:
                    line3 = "? Hz"
            else:
                line3 = "? Hz"
            return line1+"\n"+line2 + "\n" + line3
        except:
            return "Tooltip failed"

    def updatePlot(self):
        current_time = time.time()
        if len(self.logger.signals) > 0:
            if len(self.logger.getSignal(self.id)[1]) > 0:
                current_signal = self.logger.getSignal(self.id)[1][-1]
                current_unit = self.logger.getSignalUnits(self.id)
                self.setText(self.signalname)
                self.label.setText(str(round(current_signal, 5))+" "+str(current_unit))

                self.setToolTip(self.createToolTip(self.id))
            for idx, event in enumerate(self.logger.getEvents(self.id)[0]):
                evtext = self.logger.getEvents(self.id)[1][idx]
                if [event, evtext] not in self.events:
                    self.events.append([event, evtext])
                    eventItem = pg.TextItem(str(evtext), color=(
                        200, 200, 200), html=None, anchor=(0, 0.5))
                    eventItem.setPos(event-current_time, 0)
                    eventItem.vLine = pg.InfiniteLine(angle=90, movable=False)

                    self.eventItems.append(eventItem)
                    self.plotWidget.plot.addItem(eventItem)
                    self.plotWidget.plot.addItem(self.eventItems[idx].vLine, ignoreBounds=True)
                    if not self.showEvents:
                        self.eventItems[idx].hide()
                        self.eventItems[idx].vLine.hide()

            clock = list(self.logger.getSignal(self.id)[0])
            if len(clock) > 0:
                lastTimestamp = self.plotWidget.lastUpdate - clock[-1]
                if lastTimestamp >= self.signalTimeOut and self.label.styleSheet() != "background-color: rgb(113, 100, 29)":
                    self.label.setStyleSheet("background-color: rgb(113, 100, 29)")
                elif lastTimestamp < self.signalTimeOut and self.label.styleSheet() == "background-color: rgb(113, 100, 29)":
                    self.label.setStyleSheet("background-color: #232629")
                if self.active:
                    offsetX = self.signalModifications[0]
                    offsetY = self.signalModifications[1]
                    scaleX = self.signalModifications[2]
                    scaleY = self.signalModifications[3]
                    if self.plotWidget.active and self.xTimeBase:
                        ctime = current_time - self.plotWidget.globalXOffset
                    elif self.xTimeBase:
                        ctime = self.plotWidget.lastActive - self.plotWidget.globalXOffset
                    else:
                        ctime = 0 - self.plotWidget.globalXOffset
                    if clock[len(clock)-1] <= current_time+10000 and clock[len(clock)-1] > current_time-10000:
                        for idx2 in range(len(clock)):
                            clock[idx2] = scaleX*(clock[idx2]-ctime+offsetX)
                        data = list(self.logger.getSignal(self.id)[1])
                        data = [scaleY*(y+offsetY) for y in data]
                        signalname = self.logger.getSignalNames(self.id)
                        if len(clock) == len(data):
                            if self.editWidget.xySwapButton.isChecked():
                                temp = data
                                data = clock
                                clock = temp
                            self.plot.setData(x=clock, y=data)
                            self.labelItem.setPos(clock[-1], data[-1])
                        else:
                            print(self.devicename+"."+self.signalname+": len(x) != len(y)")
                    else:
                        data = list(self.logger.getSignal(self.id)[1])
                        data = [scaleY*(y+offsetY) for y in data]
                        clockx = [scaleX*(x+offsetX)-self.plotWidget.globalXOffset for x in clock]
                        if len(clock) == len(data):
                            if self.editWidget.xySwapButton.isChecked():
                                temp = data
                                data = clock
                                clock = temp
                            self.plot.setData(x=clockx, y=data)
                        else:
                            print(self.devicename+"."+self.signalname+": len(x) != len(y)")
                        self.labelItem.setPos(clockx[-1], data[-1])

                    for idx, eventItem in enumerate(self.eventItems):
                        pos = scaleX*(self.events[idx][0]-ctime+offsetX)
                        eventItem.setPos(pos, 0)
                        self.eventItems[idx].vLine.setPos(pos)

    def toggleSignal(self):

        if self.isChecked() and not self.hidden:
            self.active = True
            self.plotWidget.legend.addItem(
                self.plot, self.legendName)
            self.setStyleSheet("QToolButton{background-color: rgb(44, 114, 29)}")
            self.labelItem.show()
            self.updatePlot()
            for event in self.eventItems:
                event.show()
                event.vLine.show()
        else:
            self.active = False
            self.plot.clear()
            self.plotWidget.legend.removeItem(self.legendName)
            self.setStyleSheet("QToolButton{background-color: rgb(114, 29, 29)}")
            self.labelItem.hide()
            for event in self.eventItems:
                event.hide()
                event.vLine.hide()

    def remove(self, cb=True, total=True):
        self.plotWidget.legend.removeItem(self.legendName)
        if total:
            idx = self.logger.removeSignal(self.id)
        self.labelItem.hide()
        self.menu().hide()
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
            l = len(x)
            maxlen = self.logger.maxLength
            return dt/l*maxlen
        else:
            return -1
