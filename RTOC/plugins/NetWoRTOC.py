try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from ..LoggerPlugin import LoggerPlugin

import time
from threading import Thread
import traceback

from plugins.netWoRTOC.gui import GUI
import data.lib.pyqt_customlib as pyqtlib
from PyQt5.QtCore import QCoreApplication

translate = QCoreApplication.translate
devicename = "NetWoRTOC"
HOST = "127.0.0.1"


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        # Plugin setup
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)
        self.smallGUI = False

        # Data-logger thread
        self.run = False  # False -> stops thread
        self.__updater = Thread(target=self.updateT)    # Actualize data
        # self.updater.start()

        self.samplerate = 1
        self.__siglist = []
        self.__pluglist = []
        self.__eventlist = {}
        self.maxLength = 0

    # THIS IS YOUR THREAD
    def updateT(self):
        diff = 0
        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            ans = self.sendTCP(getSignalList= True, getPluginList = True, logger={'info': True}, getEventList= True)
            if ans:
                if 'signalList' in ans.keys():
                    if ans['signalList'] != self.__siglist:
                        self.__siglist = ans['signalList']
                        self.updateList()
                if 'pluginList' in ans.keys():
                    if ans['pluginList'] != self.__pluglist:
                        self.__pluglist = ans['pluginList']
                        self.widget.updateDevices.emit(self.__pluglist)
                if self.widget.streamButton.isChecked():
                    self.plotSignals()
                if 'logger' in ans.keys():
                    maxLength = ans['logger']['info']['recordLength']
                    if maxLength != self.maxLength:
                        self.maxLength = maxLength
                        self.widget.maxLengthSpinBox.setValue(self.maxLength)
                if 'events' in ans.keys():
                    if ans['events'] != self.__eventlist:
                        #self.widget.updateDevices.emit(self.__eventlist)
                        self.updateEvents(ans['events'])
            diff = time.time() - start_time

    def plotSignals(self):
        if self.widget.checkBox.isChecked():
            selection = self.__siglist
            selection = [".".join(i) for i in selection]
        else:
            selection = []
            for o in self.widget.listWidget.selectedItems():
                selection.append(o.text())
        if selection != []:
            ans = self.sendTCP(getSignal= selection)
            if ans != False:
                if 'signals' in ans.keys():
                    for sig in ans['signals'].keys():
                        signame = sig.split('.')
                        s = ans['signals'][sig]
                        if s[2] != []:
                            u = s[2][-1]
                        else:
                            u = ''
                        self.plot(s[0],s[1],sname = signame[1], dname=signame[0]+"_Remote", unit=u)

    def toggleDevice(self, plugin, button):
        state = button.isChecked()
        ans = self.sendTCP(plugin={plugin: {'start':state}})
        print(ans)

    def updateList(self):
        t = []
        for o in self.widget.listWidget.selectedItems():
            t.append(o.text())
        self.widget.listWidget.clear()
        for sig in self.__siglist:
            self.widget.listWidget.addItem('.'.join(sig))
        for idx in range(self.widget.listWidget.count()):
            sig = self.widget.listWidget.item(idx)
            if sig.text() in t:
                self.widget.listWidget.item(idx).setSelected(True)

    def updateEvents(self, newEventList):
        for dev in newEventList.keys():
            if dev not in self.__eventlist.keys():
                self.__eventlist[dev]=[[],[]]
            for idx, ev in enumerate(newEventList[dev][0]):
                if ev not in self.__eventlist[dev][0]:
                    device = dev.split('.')
                    self.event(x = ev, text = newEventList[dev][1][idx], sname=device[1], dname=device[0]+"_Remote", priority=0)
        self.__eventlist = newEventList

    def loadGUI(self):
        self.widget = GUI(self)
        self.widget.connectButton.clicked.connect(self.__openConnectionCallback)
        self.widget.doubleSpinBox.valueChanged.connect(self.__changeSamplerate)
        self.widget.singleButton.clicked.connect(self.plotSignals)
        self.widget.pluginCallWidget.itemClicked.connect(self.__callPluginFunction)
        self.widget.clearButton.clicked.connect(self.__clear)
        self.widget.maxLengthSpinBox.editingFinished.connect(self.__resizeLogger)
        return self.widget

    def __resizeLogger(self):
        ans = self.sendTCP(logger={'resize':self.widget.maxLengthSpinBox.value()})
        if ans:
            self.maxLength = self.widget.maxLengthSpinBox.value()
    def __clear(self):
        ok = pyqtlib.alert_message(translate('NetWoRTOC','Warnung'), translate('NetWoRTOC','Möchten sie wirklich alle Daten am RTOC-Server löschen?'), translate('NetWoRTOC',"(Unwiederrufbar)"))
        if ok:
            ans = self.sendTCP(logger={'clear': 'all'})
            print(ans)

    def __callPluginFunction(self, strung):
        strung = strung.text()
        a = strung.split('.')
        if len(a) == 2:
            plugin = a[0]
            function = a[1]

            if function.endswith('()'):
                text, ok = pyqtlib.text_message(self.widget, translate('NetWoRTOC','Remote-Funktion ausführen'), strung+translate('NetWoRTOC'," an Host ")+self.tcpaddress+translate('NetWoRTOC'," ausführen."), translate('NetWoRTOC','Funktionsparameter'))
                if ok:
                    self.par = []
                    try:
                        exec('self.par = ['+text+"]")
                        ans = self.sendTCP(plugin={plugin: {function:self.par}})
                        print(ans)
                    except:
                        tb = traceback.format_exc()
                        print(tb)
                        pyqtlib.info_message(translate('NetWoRTOC','Fehler'), translate('NetWoRTOC','Funktionsparameter sind nicht gültig'), translate('NetWoRTOC',"Bitte geben Sie gültige Parameter an"))
            else:
                ans = self.sendTCP(plugin={plugin: {'get':[function]}})
                text, ok = pyqtlib.text_message(self.widget, translate('NetWoRTOC','Remote-Parameter ändern'), strung+translate('NetWoRTOC'," an Host ")+self.tcpaddress+translate('NetWoRTOC'," ändern."), str(ans['plugin'][plugin]['get'][0]))
                if ok:
                    self.par = []
                    try:
                        exec('self.par = '+text)
                        ans = self.sendTCP(plugin={plugin: {function:self.par}})
                        print(ans)
                    except:
                        tb = traceback.format_exc()
                        print(tb)
                        pyqtlib.info_message(translate('NetWoRTOC','Fehler'), translate('NetWoRTOC','Wert ungültig'), translate('NetWoRTOC',"Bitte geben Sie einen gültigen Wert an"))
        else:
            print(a)
        # self.widget.pluginCallWidget.clearSelection()

    def __openConnectionCallback(self):
        if self.run:
            self.run = False
            self.widget.connectButton.setText(translate('NetWoRTOC',"Verbinden"))
            self.__clearAll()
        else:
            address = self.widget.comboBox.currentText()
            self.createTCPClient(address)
            self.run = True
            try:
                ok = self.sendTCP()
                if ok != False:
                    ok = True
            except:
                ok = False
            if ok:
                self.run = True
                self.__updater = Thread(target=self.updateT)
                self.__updater.start()
                self.widget.connectButton.setText(translate('NetWoRTOC',"Beenden"))
            else:
                self.__base_address = ""
                self.run = False
                self.widget.connectButton.setText(translate('NetWoRTOC',"Fehler"))
                self.__clearAll()
        self.enableGUI(self.run)

    def __clearAll(self):
        for i in reversed(range(self.widget.deviceLayout.count())):
            self.widget.deviceLayout.itemAt(i).widget().setParent(None)
        self.widget.listWidget.clear()
        self.widget.pluginCallWidget.clear()
        self.__siglist = []
        self.__pluglist = []
        self.maxLength = 0
        self.widget.maxLengthSpinBox.setValue(self.maxLength)
        self.widget.streamButton.setChecked(False)

    def enableGUI(self, value = True):
        self.widget.groupBox_2.setEnabled(value)
        self.widget.groupBox.setEnabled(value)
        self.widget.groupBox_3.setEnabled(value)
        self.widget.maxLengthSpinBox.setEnabled(value)
        self.widget.clearButton.setEnabled(value)

    def start(self, address):
        if self.run:
            self.run = False
        else:
            self.createTCPClient(address)
            self.run = True
            try:
                ok = self.sendTCP()
                if ok != False:
                    ok = True
            except:
                ok = False
            if ok:
                self.run = True
                self.__updater = Thread(target=self.updateT)
                self.__updater.start()
                self.widget.connectButton.setText(translate('NetWoRTOC',"Beenden"))
            else:
                self.__base_address = ""
                self.run = False
                self.widget.connectButton.setText(translate('NetWoRTOC',"Fehler"))


    def __changeSamplerate(self):
        self.samplerate = self.widget.doubleSpinBox.value()
