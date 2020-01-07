import pyqtgraph as pg
import pyqtgraph.console as pgconsole
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import uic
import time
from ..lib import pyqt_customlib as pyqtlib
from .styleMultiPlotGUI import plotMultiStyler
import os
import traceback
import sys
from PyQt5.QtCore import QCoreApplication
import re
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

if True:
    translate = QCoreApplication.translate

    def _(text):
        return translate('plot', text)
else:
    import gettext
    _ = gettext.gettext


if getattr(sys, 'frozen', False):
    # frozen
    packagedir = os.path.dirname(sys.executable)+'/RTOC/RTOC_GUI'
else:
    # unfrozen
    packagedir = os.path.dirname(os.path.realpath(__file__))


class Console(pgconsole.ConsoleWidget):
    def __init__(self, parent=None, namespace=None, historyFile=None, text=None, editor=None):
        super(Console, self).__init__(parent, namespace, historyFile, text, editor)
        self.ui.exceptionBtn.hide()

    def runCmd(self, cmd):
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        encCmd = re.sub(r'>', '&gt;', re.sub(r'<', '&lt;', cmd))
        encCmd = re.sub(r' ', '&nbsp;', encCmd)

        self.ui.historyList.addItem(cmd)
        self.saveHistory(self.input.history[1:100])

        try:
            sys.stdout = self
            sys.stderr = self
            if self.multiline is not None:
                self.write("<br><b>%s</b>\n" % encCmd, html=True)
                self.execMulti(cmd)
            else:
                self.write("<br><div style='background-color: black;'><b>%s</b>\n" %
                           encCmd, html=True)
                self.inCmd = True
                self.execSingle(cmd)

            if not self.inCmd:
                self.write("</div>\n", html=True)

        finally:
            sys.stdout = self.stdout
            sys.stderr = self.stderr

            sb = self.output.verticalScrollBar()
            sb.setValue(sb.maximum())
            sb = self.ui.historyList.verticalScrollBar()
            sb.setValue(sb.maximum())

    def write(self, strn, html=False):
        isGuiThread = QtCore.QThread.currentThread() == QtCore.QCoreApplication.instance().thread()
        if not isGuiThread:
            self.stdout.write(strn)
            return
        self.output.moveCursor(QtGui.QTextCursor.End)
        if html:
            self.output.textCursor().insertHtml(strn)
        else:
            if self.inCmd:
                self.inCmd = False
                # self.output.textCursor().insertHtml("</div><br><div style='font-weight: normal; background-color: #FFF; color: black'>")
                self.output.textCursor().insertHtml("</div><br><div style='font-weight: normal;'>")

                # self.stdout.write("</div><br><div style='font-weight: normal; background-color: #FFF;'>")
            self.output.insertPlainText(strn)
        # self.stdout.write(strn)

    def execSingle(self, cmd):
        cmd = self.replaceLoggerFunctions(cmd)
        try:
            # logging.info(self.globals())
            output = eval(cmd, self.globals(), self.locals())
            self.write(repr(output) + '\n')
        except SyntaxError:
            logging.debug(traceback.format_exc())
            try:
                exec(cmd, self.globals(), self.locals())
            except SyntaxError as exc:
                logging.debug(traceback.format_exc())
                if 'unexpected EOF' in exc.msg:
                    self.multiline = cmd
                else:
                    self.displayException()
            except Exception:
                logging.debug(traceback.format_exc())
                self.displayException()
        except Exception:
            # try:
            #     exec(cmd, self.globals(), self.locals())
            # except SyntaxError as exc:
            #     if 'unexpected EOF' in exc.msg:
            #         self.multiline = cmd
            #     else:
            #         self.displayException()
            logging.debug(traceback.format_exc())
            self.displayException()

    def replaceLoggerFunctions(self, s):
        s = s.replace("stream(", "logger.database.addData(")

        s = s.replace("event(", "logger.database.addNewEvent(")
        s = s.replace("plot(", "logger.database.plot(")

        s = s.replace("print(", "prints += print(")

        s = s.replace("clearData()", "logger.clearCB()")
        s = s.replace("exportData(", "logger.exportData(")

        s = s.replace("while True:", "while logger.run:")
        s = s.replace("sendTCP(", "logger.sendTCP(")
        s = s.replace("sendWebsocket(", "logger.sendWebsocket(")
        return s


class RTPlotActions:
    def connectButtons(self):
        self.pauseButton.clicked.connect(self.togglePause)
        self.searchEdit.textChanged.connect(self.filterDevices)

    def initPlotWidget(self):
        pg.setConfigOptions(
            useOpenGL=self.config['GUI']['openGL'], useWeave=self.config['GUI']['useWeave'], antialias=self.config['GUI']['antiAliasing'])
        self.plot = pg.PlotWidget()
        self.plot.setBackground(None)
        self.plot.getPlotItem().setTitle(translate('RTOC', "Signals"))
        self.plot.getPlotItem().ctrlMenu = None  # get rid of 'Plot Options'
        axis = pyqtlib.TimeAxisItem(orientation='bottom')
        axis.attachToPlotItem(self.plot.getPlotItem())  # THIS LINE CREATES A WARNING
        # self.plot.getPlotItem().setLabel("bottom", translate('RTOC', "Elapsed time"), "")
        self.plotLayout.addWidget(self.plot)
        self.legend = pg.LegendItem()
        self.legend.setParentItem(self.plot.getPlotItem())
        self.legend.anchor((1, 0), (1, 0), (-10, 10))
        self.plot.showGrid(x=self.grid[0], y=self.grid[1], alpha=self.grid[2])

        self.plotMouseLabel = pg.TextItem("", color=(
            200, 200, 200), fill=(200, 200, 200, 50), html=None)  # ,
        self.plot.addItem(self.plotMouseLabel, ignoreBounds=True)

        self.hideSignalsButton.clicked.connect(self.hideSignalList)
        toggleConsole = self.plot.getPlotItem().getViewBox().menu.addAction('Toggle Console')
        toggleConsole.triggered.connect(self.toggleConsole)

        self.toggleEventButton.setChecked(self.logger.config['GUI']['showEvents'])

    def initConsoleWidget(self):
        ns = {}
        ns['logger'] = self.logger
        ns['RTOC'] = self.self
        self.console = Console(self.plot, ns)
        self.plotLayout.addWidget(self.console)
        self.console.hide()

    def toggleConsole(self):
        if self.console.isVisible():
            self.console.hide()
        else:
            self.console.show()

    def initPlotViewWidget(self):
        self.plotViewWidget = QtWidgets.QWidget()
        uic.loadUi(packagedir+"/ui/plotViewWidget.ui", self.plotViewWidget)
        self.plotViewButton.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.plotViewButton.setMenu(QtWidgets.QMenu(self.plotViewButton))
        action = QtWidgets.QWidgetAction(self.plotViewButton)
        action.setDefaultWidget(self.plotViewWidget)
        self.plotViewButton.setStyleSheet(
            "QToolButton:checked, QToolButton:pressed,QToolButton::menu-button:pressed { background-color: #76797C;border: 1px solid #76797C;padding: 5px;}")
        self.plotViewButton.menu().addAction(action)
        self.plotViewButton.clicked.connect(lambda: self.plotViewButton.menu().popup(
            self.plotViewButton.mapToGlobal(QtCore.QPoint(0, 35))))

        self.plotViewWidget.gridButton.clicked.connect(self.togglePlotGrid)
        self.plotViewWidget.legendButton.clicked.connect(self.togglePlotLegend)
        self.plotViewWidget.labelButton.clicked.connect(self.togglePlotLabels)
        self.plotViewWidget.plotRateSpinBox.valueChanged.connect(self.changePlotRateAction)
        self.plotViewWidget.stylePlotsButton.clicked.connect(self.stylePlots)
        self.plotViewWidget.blinkingButton.clicked.connect(self.toggleBlinkingIndicator)
        self.plotViewWidget.invertPlotButton.clicked.connect(self.toggleInverted)
        self.plotViewWidget.xTimeBaseButton.clicked.connect(self.toggleXRelative)
        self.plotViewWidget.globalXOffsetSpinBox.valueChanged.connect(self.changeGlobalXOffset)
        self.plotViewWidget.timeAxisButton.clicked.connect(self.toggleAxisStyle)

        self.gridViewWidget = QtWidgets.QWidget()
        uic.loadUi(packagedir+"/ui/gridViewWidget.ui", self.gridViewWidget)
        self.plotViewWidget.gridButton.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.plotViewWidget.gridButton.setMenu(QtWidgets.QMenu(self.plotViewWidget.gridButton))
        action = QtWidgets.QWidgetAction(self.plotViewWidget.gridButton)
        action.setDefaultWidget(self.gridViewWidget)
        self.plotViewWidget.gridButton.setStyleSheet(
            "QToolButton:checked, QToolButton:pressed,QToolButton::menu-button:pressed { background-color: #76797C;border: 1px solid #76797C;padding: 5px;}")
        self.plotViewWidget.gridButton.menu().addAction(action)
        # self.plotViewWidget.gridButton.clicked.connect(lambda: self.plotViewWidget.gridButton.menu().popup(
        #    self.plotViewWidget.gridButton.mapToGlobal(QtCore.QPoint(0, 35))))

        self.gridViewWidget.xCheckbox.clicked.connect(self.gridXAction)
        self.gridViewWidget.yCheckbox.clicked.connect(self.gridYAction)
        self.gridViewWidget.alphaSlider.valueChanged.connect(self.gridAlphaAction)

    def hideSignalList(self):
        if self.hideSignalsButton.isChecked():
            self.widget_2.show()
        else:
            self.widget_2.hide()

    def gridXAction(self):
        value = self.gridViewWidget.xCheckbox.isChecked()
        self.grid[0] = value
        self.updateGrid()

    def gridYAction(self):
        value = self.gridViewWidget.yCheckbox.isChecked()
        self.grid[1] = value
        self.updateGrid()

    def gridAlphaAction(self):
        alpha = self.gridViewWidget.alphaSlider.value()/100
        self.grid[2] = alpha
        self.updateGrid()

    def updateGrid(self):
        self.plot.showGrid(x=self.grid[0], y=self.grid[1], alpha=self.grid[2])
        self.config['GUI']['grid'] = self.grid

    def toggleInverted(self):
        if self.plotViewWidget.invertPlotButton.isChecked():
            self.config['GUI']['plotInverted'] = True
            self.plot.setBackground("w")
        else:
            self.config['GUI']['plotInverted'] = False
            self.plot.setBackground(None)

    def toggleXTimeBase(self, value):
        if value:
            self.config['GUI']['xTimeBase'] = True
            for sig in self.signalObjects:
                sig.xTimeBase = True
                sig.editWidget.xTimeBaseButton.setChecked(True)
            self.xTimeBase = True
        else:
            self.config['GUI']['xTimeBase'] = False
            for sig in self.signalObjects:
                sig.xTimeBase = False
                sig.editWidget.xTimeBaseButton.setChecked(False)
            self.xTimeBase = False

    def toggleAxisStyle(self):
        if self.plotViewWidget.timeAxisButton.isChecked():
            if self.config['GUI']['xRelative']:
                self.setXTicks(mode=0)
            else:
                self.setXTicks(mode=2)

            self.config['GUI']['timeAxis'] = True
            self.plot.getPlotItem().setLabel("bottom", translate('RTOC', "Elapsed time [s]"), "")
            self.toggleXTimeBase(True)
        else:
            self.setXTicks(mode=1)
            self.config['GUI']['timeAxis'] = False
            self.toggleXTimeBase(False)

    def setXTicks(self, mode=0):
        if mode == 0:
            axis = pyqtlib.TimeAxisItem(True, orientation='bottom')
            axis.attachToPlotItem(self.plot.getPlotItem())  # THIS LINE CREATES A WARNING
            self.config['GUI']['timeAxis'] = True
            self.plot.getPlotItem().setLabel("bottom", translate('RTOC', "Elapsed time [s]"), "")
        elif mode == 1:
            axis = pg.AxisItem(orientation='bottom')
            axis.setParentItem(self.plot.getPlotItem())
            viewBox = self.plot.getPlotItem().getViewBox()
            axis.linkToView(viewBox)
            axis._oldAxis = self.plot.getPlotItem().axes[axis.orientation]['item']
            axis._oldAxis.hide()
            self.plot.getPlotItem().axes[axis.orientation]['item'] = axis
            pos = self.plot.getPlotItem().axes[axis.orientation]['pos']
            self.plot.getPlotItem().layout.addItem(axis, *pos)
            axis.setZValue(-1000)
            self.plot.getPlotItem().setLabel("bottom", "", "")
        elif mode == 2:
            axis = pyqtlib.TimeAxisItem(False, orientation='bottom')
            axis.attachToPlotItem(self.plot.getPlotItem())  # THIS LINE CREATES A WARNING
            self.config['GUI']['timeAxis'] = True
            self.plot.getPlotItem().setLabel("bottom", translate('RTOC', "Date/Time"), "")

    def toggleXRelative(self):
        if self.plotViewWidget.xTimeBaseButton.isChecked():
            self.config['GUI']['xRelative'] = True
            # for sig in self.signalObjects:
                # sig.xTimeBase = True
                # sig.editWidget.xTimeBaseButton.setChecked(True)
            # self.xTimeBase = True
            if self.config['GUI']['xTimeBase']:
                self.setXTicks(mode=0)
        else:
            self.config['GUI']['xRelative'] = False
            # for sig in self.signalObjects:
                # sig.xTimeBase = False
                # sig.editWidget.xTimeBaseButton.setChecked(False)
            # self.xTimeBase = False
            if self.config['GUI']['xTimeBase']:
                self.setXTicks(mode=2)

    def initPlotToolsWidget(self):
        self.plotToolsWidget = QtWidgets.QWidget()
        self.toolButton.hide()
        self.measureButton.clicked.connect(self.toggleROIS)
        self.crosshairButton.clicked.connect(self.toggleCrosshair)
        self.cutButton.clicked.connect(self.toggleCutTool)
        self.toggleEventButton.clicked.connect(self.toggleEvents)

    def initROIS(self):
        self.rois = []
        self.rect = pg.RectROI(pos=(1, 1), size=(100, 100), removable=True,
                               pen=pg.mkPen(pg.mkColor(9, 169, 188),
                                            width=3,
                                            style=QtCore.Qt.SolidLine))

        self.rect.addRotateHandle([1, 0], [0.5, 0.5])
        self.rect.handleSize = 9
        # Add top and right Handles
        self.rect.addScaleHandle([0.5, 0], [0.5, 1])
        self.rect.addScaleHandle([0.5, 1], [0.5, 0])
        self.rect.addScaleHandle([0, 0.5], [1, 0.5])
        self.rect.addScaleHandle([1, 0.5], [0, 0.5])

        self.rois.append(self.rect)

        for roi in self.rois:
            roi.sigRegionChanged.connect(self.updateROI)
            self.plot.addItem(roi)
        self.rois[0].hide()

    def initCrosshair(self):
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        # self.CrossHairLabel = pg.LabelItem(justify='right')
        self.CrossHairLabel = pg.TextItem("", color=(
            200, 200, 200), fill=(200, 200, 200, 50), html=None)  # ,
        self.plot.addItem(self.vLine, ignoreBounds=True)
        self.plot.addItem(self.hLine, ignoreBounds=True)
        self.plot.addItem(self.CrossHairLabel, ignoreBounds=True)
        self.plot.scene().sigMouseMoved.connect(self.mouseMoved)
        self.toggleCrosshair()

    def initCutTool(self):
        self.cutVLine1 = pg.InfiniteLine(angle=90, movable=True, label='{value:0.2f}', labelOpts={
                                         'position': 0.1, 'color': (200, 200, 100), 'fill': (200, 200, 200, 50), 'movable': True})
        self.cutVLine2 = pg.InfiniteLine(angle=90, movable=True, label='{value:0.2f}', labelOpts={
                                         'position': 0.1, 'color': (200, 200, 100), 'fill': (200, 200, 200, 50), 'movable': True})
        self.plot.addItem(self.cutVLine1, ignoreBounds=True)
        self.plot.addItem(self.cutVLine2, ignoreBounds=True)
        self.toggleCutTool()

    def initMeasureTool(self):
        self.measureWidget = QtWidgets.QDialog()
        self.measureWidget.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        uic.loadUi(packagedir+"/ui/messtoolDialog.ui", self.measureWidget)
        self.measureWidget.setStyleSheet(self.styleSheet().replace(
            "background-color: rgba(49, 54, 59, .9)", "background-color: rgba(34, 36, 38, 0.9)"))
        self.measureWidget.mousePressEvent = self.mousePressEvents
        self.measureWidget.mouseMoveEvent = self.mouseMoveEvents

    def changePlotRateAction(self):
        self.updatePlotSamplerate = self.plotViewWidget.plotRateSpinBox.value()
        if self.updatePlotSamplerate != 0:
            self.updatePlotTimer.setInterval(int(1/self.updatePlotSamplerate*1000))
        else:
            self.updatePlotTimer.setInterval(99999999999999)

    def changeGlobalXOffset(self):
        self.globalXOffset = self.plotViewWidget.globalXOffsetSpinBox.value()

    def updateLabels(self):
        self.plotViewWidget.plotRateSpinBox.setValue(self.updatePlotSamplerate)

    def togglePause(self):
        if self.pauseButton.isChecked():
            self.active = False
            self.lastActive = time.time()
            self.pauseButton.setStyleSheet("background-color: rgb(114, 29, 29)")
        else:
            self.active = True
            self.pauseButton.setStyleSheet("")
            self.plotMouseLabel.hide()

    def toggleCutTool(self):
        if not self.cutButton.isChecked():
            self.cutVLine1.hide()
            self.cutVLine2.hide()
            self.pauseButton.setChecked(False)
            self.pauseButton.setEnabled(True)
            self.togglePause()

        else:
            self.cutVLine1.show()
            self.cutVLine2.show()
            self.pauseButton.setChecked(True)
            self.pauseButton.setEnabled(False)
            self.togglePause()

    def togglePlotGrid(self):
        if not self.plotViewWidget.gridButton.isChecked():
            self.config['GUI']['plotGridEnabled'] = False
            self.plot.showGrid(x=False, y=False, alpha=0.3)

        else:
            self.config['GUI']['plotGridEnabled'] = True
            self.plot.showGrid(x=self.grid[0], y=self.grid[1], alpha=self.grid[2])

    def togglePlotLegend(self):
        if not self.plotViewWidget.legendButton.isChecked():
            self.config['GUI']['plotLegendEnabled'] = False
            self.legend.hide()
        else:
            self.config['GUI']['plotLegendEnabled'] = True
            self.legend.show()

    def togglePlotLabels(self):
        if not self.plotViewWidget.labelButton.isChecked():
            self.config['GUI']['plotLabelsEnabled'] = False
            for sig in self.signalObjects:
                sig.labelItem.hide()
                sig.editWidget.labelButton.setChecked(False)
        else:
            self.config['GUI']['plotLabelsEnabled'] = True
            for sig in self.signalObjects:
                if sig.active:
                    sig.labelItem.show()
                    sig.editWidget.labelButton.setChecked(True)

    def toggleBlinkingIndicator(self):
        if not self.plotViewWidget.labelButton.isChecked():
            self.config['GUI']['blinkingIdentifier'] = False
        else:
            self.config['GUI']['blinkingIdentifier'] = True

    def toggleCrosshair(self):
        if not self.crosshairButton.isChecked():
            self.vLine.hide()
            self.hLine.hide()
            self.CrossHairLabel.hide()
        else:
            self.vLine.show()
            self.hLine.show()
            self.CrossHairLabel.show()

    def updateROI(self, roi):
        self.measureWidget.ROIAmplitudeLabel.setText(str(round(list(roi.size())[1], 4)))
        self.measureWidget.ROIDurationLabel.setText(str(round(list(roi.size())[0], 4))+"s")
        self.measureWidget.ROIXMinLabel.setText(str(round(list(roi.pos())[0], 4))+"s")
        self.measureWidget.ROIXMaxLabel.setText(
            str(round(list(roi.pos())[0]+list(roi.size())[0], 4))+"s")
        self.measureWidget.ROIYMinLabel.setText(str(round(list(roi.pos())[1], 4)))
        self.measureWidget.ROIYMaxLabel.setText(
            str(round(list(roi.pos())[1]+list(roi.size())[1], 4)))

    def toggleROIS(self):
        if not self.measureButton.isChecked():
            self.rois[0].hide()
            self.measureWidget.hide()
        else:
            [[xmin, xmax], [ymin, ymax]] = self.plot.getPlotItem().viewRange()
            f = 0.8
            self.rois[0].setPos(xmin*f, ymin*f)
            self.rois[0].setSize(abs(xmax-xmin)*f*f, abs(ymax-ymin)*f*f)
            self.measureWidget.show()
            self.rois[0].show()
            self.updateROI(self.rois[0])

    def stylePlots(self):
        signalnames = []
        plots = []
        for sig in self.signalObjects:
            plots.append(sig.plot)
            signalnames.append([sig.devicename, sig.signalname])
        if plots != []:
            d = plotMultiStyler(signalnames, plots, self.logger)
            d.exec_()

    def mousePressEvents(self, event):
        self.measureWidget.oldPos = event.globalPos()

    def mouseMoveEvents(self, event):
        delta = QtCore.QPoint(event.globalPos() - self.measureWidget.oldPos)
        self.measureWidget.move(self.measureWidget.x() + delta.x(),
                                self.measureWidget.y() + delta.y())
        self.measureWidget.oldPos = event.globalPos()

    def mouseMoved(self, evt):
        vb = self.plot.getPlotItem().vb
        mousePoint = vb.mapSceneToView(evt)
        self.mouseX = mousePoint.x()
        self.mouseY = mousePoint.y()
        if self.crosshairButton.isChecked():
            self.CrossHairLabel.setText("X: "+str(round(mousePoint.x(), 2)) + "s\nY:"+str(round(mousePoint.y(), 2)))
            self.CrossHairLabel.setPos(mousePoint.x(), mousePoint.y())
            # self.crosshairYLabel.setText(str(mousePoint.y()))
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())

    def filterDevices(self, tex):
        tex = tex+';'
        tex = tex.replace('; ', ';')
        for item in self.signalTreeWidgetItems:
            sig = self.treeWidget.itemWidget(item, 0)
            found = False
            for text in tex.split(';'):
                # logging.info(text)
                if (text != "" or tex == ';') and found is False:
                    if text.lower() in sig.button.text().lower() or tex == ";":
                        item.setHidden(False)
                        sig.hidden = False
                        sig.toggleSignal()
                        found = True
                    else:
                        item.setHidden(True)
                        sig.hidden = True
                        sig.toggleSignal()

    def toggleEvents(self, state):
        self.logger.config['GUI']['showEvents'] = state
        for sig in self.signalObjects:
            sig.toggleEvents(state)
