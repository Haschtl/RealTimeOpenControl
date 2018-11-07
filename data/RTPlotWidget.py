from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import uic
import time
from functools import partial

from data.RTPlotActions import RTPlotActions
from data.signalWidget import SignalWidget
import data.define as define

class RTPlotWidget(QtWidgets.QWidget, RTPlotActions):
    droppedTree = QtCore.pyqtSignal(dict)
    addSignal2 = QtCore.pyqtSignal(str, str, int, str)
    def __init__(self, logger, selfself, id):
        super(RTPlotWidget, self).__init__()
        #print("creating new plot widget")
        uic.loadUi("data/ui/plotWidget.ui", self)
        self.setAcceptDrops(True)
        self.setObjectName("RTPlotWidget"+str(id))
        self.self = selfself
        self.id = id
        self.logger = logger
        self.config= self.self.config
        self.plotStyles = self.self.plotStyles
        self.active = True
        self.lastActive = time.time()
        self.updatePlotSamplerate = 10
        self.signalObjects = []
        self.lastUpdate = time.time()
        self.deviceTreeWidgetItems = []
        self.signalTreeWidgetItems = []
        self.devices = []
        self.updatePlotTimer = QtCore.QTimer()
        self.updatePlotTimer.timeout.connect(self.updatePlot)
        self.updatePlotTimer.start(int(1/self.updatePlotSamplerate*1000))
        self.xTimeBase = True
        self.globalXOffset = 0
        self.grid=self.config["grid"]
        self.mouseX = 0
        self.mouseY = 0
        self.lastSignalClick = [0,0]
        self.addSignal2.connect(self.addSignal, QtCore.Qt.QueuedConnection)
        self.signalHeight = define.signalButtonHeight

        self.connectButtons()

        self.initPlotWidget()
        self.initPlotToolsWidget()
        self.initPlotViewWidget()

        self.gridViewWidget.xCheckbox.setChecked(self.grid[0])
        self.gridViewWidget.yCheckbox.setChecked(self.grid[1])
        self.gridViewWidget.alphaSlider.setValue(self.grid[2]*100)

        self.initROIS()
        self.initCrosshair()
        self.initCutTool()
        self.initMeasureTool()

        self.updateLabels()

        self.treeWidget.startDrag = self.startDragTreeWidget
        self.treeWidget.dropEvent = self.dropEventTreeWidget

        self.plotViewWidget.labelButton.setChecked(self.config["plotLabelsEnabled"])
        self.plotViewWidget.gridButton.setChecked(self.config["plotGridEnabled"])
        self.plotViewWidget.legendButton.setChecked(self.config["plotLegendEnabled"])
        self.plotViewWidget.blinkingButton.setChecked(self.config["blinkingIdentifier"])
        self.plotViewWidget.invertPlotButton.setChecked(self.config["plotInverted"])
        self.plotViewWidget.xTimeBaseButton.setChecked(self.config["xTimeBase"])
        self.plotViewWidget.timeAxisButton.setChecked(self.config["timeAxis"])

        self.togglePlotLegend()
        self.togglePlotLabels()
        self.toggleInverted()
        self.togglePlotLabels()
        self.toggleXTimeBase()
        self.toggleAxisStyle()
        self.togglePlotGrid()

    def clear(self):
        # for p in self.signalObjects:
        while len(self.signalObjects) > 0:
            p = self.signalObjects[0]
            # self.plot.getPlotItem().removeItem(p.plot)
            p.remove()

        self.signalNames = []
        self.signalObjects = []

    def updatePlot(self):
        # if self.active:
        if self.self.isVisible():
            for signal in self.signalObjects:
                signal.updatePlot()
            self.lastUpdate = time.time()

    def stop(self):
        self.clear()
        self.measureWidget.hide()
        self.measureWidget.close()
        self.updatePlotTimer.stop()

    def deleteSignal(self, id, devicename, signalname):
        idx = self.getSignalIdx(id)
        self.signalObjects[idx].remove(True, False)

    def getSignalIdx(self, id):
        for idx, sig in enumerate(self.signalObjects):
            if sig.id == id:
                return idx
        return -1

    def removeSignal(self, id, devicename, signalname):
        idx = self.getSignalIdx(id)
        popped = self.signalObjects.pop(idx)
        #self.removeSignal(idx, devicename, signalname)
        self.treeWidget.removeItemWidget(self.signalTreeWidgetItems[idx], 0)
        self.treeWidget.removeItemWidget(self.signalTreeWidgetItems[idx], 1)
        self.deviceTreeWidgetItems[self.devices.index(
            devicename)].removeChild(self.signalTreeWidgetItems[idx])

        if self.deviceTreeWidgetItems[self.devices.index(devicename)].childCount() == 0:
            #print("Deleting Devicegroup")
            self.treeWidget.removeItemWidget(
                self.deviceTreeWidgetItems[self.devices.index(devicename)], 0)
            self.treeWidget.takeTopLevelItem(self.devices.index(devicename))
            self.deviceTreeWidgetItems.pop(self.devices.index(devicename))
            self.devices.pop(self.devices.index(devicename))
        self.signalTreeWidgetItems.pop(idx)

        #for idx, sig in enumerate(self.signalObjects):
        #    sig.id = idx
        # self.signalListWidget.clear()
        # self.triggerWidget.triggerSignals.clear()
        # self.updateListWidget()
        self.countLabel.setText(self.tr("Signale: ")+str(len(self.signalObjects)))

    def addSignalRAW(self, signalObject):
        idx = len(self.signalObjects)
        self.signalObjects.append(signalObject)
        self.plot.addItem(self.signalObjects[idx].plot)
        self.plot.addItem(self.signalObjects[idx].labelItem)
        if not self.plotViewWidget.labelButton.isChecked():
            self.signalObjects[idx].labelItem.hide()

        devicename = signalObject.devicename
        #self.legend.addItem(self.signalObjects[idx].plot,signalname+" ["+unit+"]")
        # self.signalListWidget.addItem(devicename+"."+signalname)
        # self.triggerWidget.triggerSignals.addItem(devicename+"."+signalname)
        # self.triggerSignals.findItems(devicename+"."+signalname).setSelected(True)
        self.signalTreeWidgetItems.append(QtWidgets.QTreeWidgetItem())
        self.signalObjects[idx].setMinimumHeight(self.signalHeight)
        self.signalObjects[idx].setMaximumHeight(self.signalHeight)
        # item.setSizeHint(sizeHint)
        if devicename not in self.devices:
            self.devices.append(devicename)
            treeWidgetItem = QtWidgets.QTreeWidgetItem()
            #treeWidgetItem.setText(0, devicename)
            button = QtWidgets.QPushButton(devicename)
            button.setCheckable(True)
            button.setChecked(True)
            self.deviceTreeWidgetItems.append(treeWidgetItem)
            self.treeWidget.addTopLevelItem(treeWidgetItem)
            self.treeWidget.setItemWidget(treeWidgetItem,0, button)
            button.clicked.connect(partial(self.toggleDevice, button, treeWidgetItem))
            #self.treeWidget.setItemWidget(treeWidgetItem, 0, item2)
        #child = QtWidgets.QTreeWidgetItem()
        self.signalTreeWidgetItems[idx].setMinimumHeight(0)
        self.deviceTreeWidgetItems[self.devices.index(
            devicename)].addChild(self.signalTreeWidgetItems[idx])
        self.treeWidget.setItemWidget(self.signalTreeWidgetItems[idx], 0, self.signalObjects[idx])
        self.treeWidget.setItemWidget(
            self.signalTreeWidgetItems[idx], 1, self.signalObjects[idx].label)
        self.deviceTreeWidgetItems[self.devices.index(devicename)].setExpanded(True)
        # self.treeWidget.setItemWidget(item, 0, item2)# self.signalObjects[idx])
        # self.listWidget.addWidget(self.signalObjects[idx])
        self.countLabel.setText(self.tr("Signale: ")+str(len(self.signalObjects)))

    def signalClickedAction(self, devicename, signalname):
        r = 0.001
        if abs(self.mouseX-self.lastSignalClick[0])<r and abs(self.mouseY-self.lastSignalClick[1])<r:
            self.plotMouseLabel.hide()
        elif self.pauseButton.isChecked():
            self.plotMouseLabel.show()
            self.plotMouseLabel.setText(devicename+"."+signalname)
            self.plotMouseLabel.setPos(self.mouseX, self.mouseY)
        self.lastSignalClick = [self.mouseX, self.mouseY]

    def toggleDevice(self, button, treeItem):
        state = button.isChecked()
        for idx in range(treeItem.childCount()):
            item = treeItem.child(idx)
            widget = self.treeWidget.itemWidget(item,0)
            widget.setChecked(state)
            widget.toggleSignal()

    def addSignal(self, devicename, signalname, id, unit):
        idx = len(self.signalObjects)
        self.signalObjects.append(SignalWidget(self, self.logger, devicename, signalname, id, unit))
        self.plot.addItem(self.signalObjects[idx].plot)
        self.plot.addItem(self.signalObjects[idx].labelItem)
        if not self.plotViewWidget.labelButton.isChecked():
            self.signalObjects[idx].labelItem.hide()

        #self.legend.addItem(self.signalObjects[idx].plot,signalname+" ["+unit+"]")
        # self.signalListWidget.addItem(devicename+"."+signalname)
        # self.triggerWidget.triggerSignals.addItem(devicename+"."+signalname)
        # self.triggerSignals.findItems(devicename+"."+signalname).setSelected(True)
        self.signalTreeWidgetItems.append(QtWidgets.QTreeWidgetItem())
        self.signalObjects[idx].setMinimumHeight(self.signalHeight)
        self.signalObjects[idx].setMaximumHeight(self.signalHeight)
        # item.setSizeHint(sizeHint)
        if devicename not in self.devices:
            self.devices.append(devicename)
            treeWidgetItem = QtWidgets.QTreeWidgetItem()
            button = QtWidgets.QPushButton(devicename)
            button.setCheckable(True)
            button.setChecked(True)
            #treeWidgetItem.setText(0, devicename)
            self.deviceTreeWidgetItems.append(treeWidgetItem)
            self.treeWidget.addTopLevelItem(treeWidgetItem)
            self.treeWidget.setItemWidget(treeWidgetItem,0, button)
            button.clicked.connect(partial(self.toggleDevice, button, treeWidgetItem))
            #self.treeWidget.setItemWidget(treeWidgetItem, 0, item2)
        #child = QtWidgets.QTreeWidgetItem()
        self.deviceTreeWidgetItems[self.devices.index(
            devicename)].addChild(self.signalTreeWidgetItems[idx])
        self.treeWidget.setItemWidget(self.signalTreeWidgetItems[idx], 0, self.signalObjects[idx])
        self.treeWidget.setItemWidget(
            self.signalTreeWidgetItems[idx], 1, self.signalObjects[idx].label)
        self.deviceTreeWidgetItems[self.devices.index(devicename)].setExpanded(True)
        # self.treeWidget.setItemWidget(item, 0, item2)# self.signalObjects[idx])
        # self.listWidget.addWidget(self.signalObjects[idx])
        self.countLabel.setText(self.tr("Signale: ")+str(len(self.signalObjects)))
    # def closeEvent(self, event, *args, **kwargs):
    #     if self.id == 0:
    #         self.stop()
    #     else:
    #         for signalObject in self.signalObjects:
    #             self.self.plotWidgets[0].addSignalRAW(signalObject)
    #             self.self.deletePlotWidget(self.id)
    #
    #     super(RTPlotWidget, self).closeEvent(event)

    #_drag_info = {"oldWidget":"", "newWidget":"", "signalObjects":[]}

    def startDragTreeWidget(self, actions):
        self.self._drag_info = {"oldWidget":"", "newWidget":"", "signalObjects":[]}
        self.self._drag_info["oldWidget"] = self.id
        for item in self.treeWidget.selectedItems():
            self.self._drag_info["signalObjects"].append(item)
        super(QtWidgets.QTreeWidget, self.treeWidget).startDrag(actions)

    def dropEventTreeWidget(self, event):
        #if event.mimeData().hasUrls():
        #    ...
        if self.self._drag_info:
            event.setDropAction(QtCore.Qt.MoveAction)
            event.setDropAction(QtCore.Qt.IgnoreAction)
            super(RTPlotWidget, self).dropEvent(event)
            #self.emit(QtCore.SIGNAL("dropped"), list(self._drag_info))
            self.self._drag_info["newWidget"] = self.id
            self.droppedTree.emit(self.self._drag_info)

    def mousePressEvent(self, event):
        self.self.activePlotWidgetIndex = self.id
        #super(RTPlotWidget, self).mousePressEvent(event)
