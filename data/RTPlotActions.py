import pyqtgraph as pg
# import pyqtgraph.exporters
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import uic
import time
import data.lib.pyqt_customlib as pyqtlib
from data.styleMultiPlotGUI import plotMultiStyler


class RTPlotActions:
    def connectButtons(self):
        self.pauseButton.clicked.connect(self.togglePause)
        self.searchEdit.textChanged.connect(self.filterDevices)

    def initPlotWidget(self):
        self.plot = pg.PlotWidget()
        self.plot.setBackground(None)
        self.plot.getPlotItem().setTitle(self.tr("Signale"))
        axis = pyqtlib.TimeAxisItem(orientation='bottom')
        axis.attachToPlotItem(self.plot.getPlotItem())  # THIS LINE CREATES A WARNING
        self.plot.getPlotItem().setLabel("bottom", self.tr("Vergangene Zeit"), "")

        self.plotLayout.addWidget(self.plot)
        self.legend = pg.LegendItem()
        self.legend.setParentItem(self.plot.getPlotItem())
        self.legend.anchor((1, 0), (1, 0), (-10, 10))
        self.plot.showGrid(x=self.grid[0], y=self.grid[1], alpha=self.grid[2])

        self.plotMouseLabel = pg.TextItem("", color=(200, 200, 200), fill=(200, 200, 200, 50), html=None)  # ,
        self.plot.addItem(self.plotMouseLabel)

    def initPlotViewWidget(self):
        self.plotViewWidget = QtWidgets.QWidget()
        uic.loadUi("data/ui/plotViewWidget.ui", self.plotViewWidget)
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
        self.plotViewWidget.xTimeBaseButton.clicked.connect(self.toggleXTimeBase)
        self.plotViewWidget.globalXOffsetSpinBox.valueChanged.connect(self.changeGlobalXOffset)
        self.plotViewWidget.timeAxisButton.clicked.connect(self.toggleAxisStyle)

        self.gridViewWidget = QtWidgets.QWidget()
        uic.loadUi("data/ui/gridViewWidget.ui", self.gridViewWidget)
        self.plotViewWidget.gridButton.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.plotViewWidget.gridButton.setMenu(QtWidgets.QMenu(self.plotViewWidget.gridButton))
        action = QtWidgets.QWidgetAction(self.plotViewWidget.gridButton)
        action.setDefaultWidget(self.gridViewWidget)
        self.plotViewWidget.gridButton.setStyleSheet(
            "QToolButton:checked, QToolButton:pressed,QToolButton::menu-button:pressed { background-color: #76797C;border: 1px solid #76797C;padding: 5px;}")
        self.plotViewWidget.gridButton.menu().addAction(action)
        #self.plotViewWidget.gridButton.clicked.connect(lambda: self.plotViewWidget.gridButton.menu().popup(
        #    self.plotViewWidget.gridButton.mapToGlobal(QtCore.QPoint(0, 35))))

        self.gridViewWidget.xCheckbox.clicked.connect(self.gridXAction)
        self.gridViewWidget.yCheckbox.clicked.connect(self.gridYAction)
        self.gridViewWidget.alphaSlider.valueChanged.connect(self.gridAlphaAction)

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
        self.config["grid"]= self.grid

    def toggleInverted(self):
        if self.plotViewWidget.invertPlotButton.isChecked():
            self.config["plotInverted"] = True
            self.plot.setBackground("w")
        else:
            self.config["plotInverted"] = False
            self.plot.setBackground(None)

    def toggleXTimeBase(self):
        if self.plotViewWidget.xTimeBaseButton.isChecked():
            self.config["xTimeBase"] = True
            for sig in self.signalObjects:
                sig.xTimeBase = True
                sig.editWidget.xTimeBaseButton.setChecked(True)
            self.xTimeBase = True
        else:
            self.config["xTimeBase"] = False
            for sig in self.signalObjects:
                sig.xTimeBase = False
                sig.editWidget.xTimeBaseButton.setChecked(False)
            self.xTimeBase = False

    def toggleAxisStyle(self):
        if self.plotViewWidget.timeAxisButton.isChecked():
            axis = pyqtlib.TimeAxisItem(orientation='bottom')
            axis.attachToPlotItem(self.plot.getPlotItem())  # THIS LINE CREATES A WARNING
            self.config["timeAxis"] = True
            self.plot.getPlotItem().setLabel("bottom", "Vergangene Zeit", "")
        else:
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
            self.config["timeAxis"] = False

    def initPlotToolsWidget(self):
        self.plotToolsWidget = QtWidgets.QWidget()
        uic.loadUi("data/ui/plotToolsWidget.ui", self.plotToolsWidget)

        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        self.toolButton.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.toolButton.setMenu(QtWidgets.QMenu(self.toolButton))
        action = QtWidgets.QWidgetAction(self.toolButton)
        action.setDefaultWidget(self.plotToolsWidget)
        self.toolButton.setStyleSheet(
            "QToolButton:checked, QToolButton:pressed,QToolButton::menu-button:pressed { background-color: #76797C;border: 1px solid #76797C;padding: 5px;}")
        self.toolButton.menu().addAction(action)
        self.toolButton.clicked.connect(lambda: self.toolButton.menu().popup(
            self.toolButton.mapToGlobal(QtCore.QPoint(0, 35))))

        self.plotToolsWidget.measureButton.clicked.connect(self.toggleROIS)
        self.plotToolsWidget.crosshairButton.clicked.connect(self.toggleCrosshair)
        self.plotToolsWidget.cutButton.clicked.connect(self.toggleCutTool)

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
        #self.CrossHairLabel = pg.LabelItem(justify='right')
        self.CrossHairLabel = pg.TextItem("", color=(200, 200, 200), fill=(200, 200, 200, 50), html=None)  # ,
        self.plot.addItem(self.vLine, ignoreBounds=True)
        self.plot.addItem(self.hLine, ignoreBounds=True)
        self.plot.addItem(self.CrossHairLabel)
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
        uic.loadUi("data/ui/messtoolDialog.ui", self.measureWidget)
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
        if not self.plotToolsWidget.cutButton.isChecked():
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
            self.config["plotGridEnabled"] = False
            self.plot.showGrid(x=False, y=False, alpha=0.3)

        else:
            self.config["plotGridEnabled"] = True
            self.plot.showGrid(x=self.grid[0], y=self.grid[1], alpha=self.grid[2])

    def togglePlotLegend(self):
        if not self.plotViewWidget.legendButton.isChecked():
            self.config["plotLegendEnabled"] = False
            self.legend.hide()
        else:
            self.config["plotLegendEnabled"] = True
            self.legend.show()

    def togglePlotLabels(self):
        if not self.plotViewWidget.labelButton.isChecked():
            self.config["plotLabelsEnabled"] = False
            for sig in self.signalObjects:
                sig.labelItem.hide()
                sig.editWidget.labelButton.setChecked(False)
        else:
            self.config["plotLabelsEnabled"] = True
            for sig in self.signalObjects:
                if sig.active:
                    sig.labelItem.show()
                    sig.editWidget.labelButton.setChecked(True)

    def toggleBlinkingIndicator(self):
        if not self.plotViewWidget.labelButton.isChecked():
            self.config["blinkingIdentifier"] = False
        else:
            self.config["blinkingIdentifier"] = True

    def toggleCrosshair(self):
        if not self.plotToolsWidget.crosshairButton.isChecked():
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
        if not self.plotToolsWidget.measureButton.isChecked():
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
        if self.plotToolsWidget.crosshairButton.isChecked():
            self.CrossHairLabel.setText("X: "+str(round(mousePoint.x(), 2)) +
                                        "s\nY:"+str(round(mousePoint.y(), 2)))
            self.CrossHairLabel.setPos(mousePoint.x(), mousePoint.y())
            # self.crosshairYLabel.setText(str(mousePoint.y()))
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())

    def filterDevices(self, tex):
        tex=tex+';'
        tex = tex.replace('; ',';')
        for item in self.signalTreeWidgetItems:
            sig = self.treeWidget.itemWidget(item,0)
            found = False
            for text in tex.split(';'):
                #print(text)
                if (text != "" or tex == ';') and found == False:
                    if text.lower() in sig.text().lower() or tex == ";":
                        item.setHidden(False)
                        sig.hidden = False
                        sig.toggleSignal()
                        found = True
                    else:
                        item.setHidden(True)
                        sig.hidden = True
                        sig.toggleSignal()

        # for sig in self.signalObjects:
        #     if text.lower() in sig.text().lower() or text == "":
        #         sig.show()
        #         sig.label.show()
        #     else:
        #         sig.hide()
        #         sig.label.hide()
        #         sig.resize(sig.sizeHint().width(), sig.minimumHeight())
        #         sig.label.resize(sig.label.sizeHint().width(), sig.label.minimumHeight())
