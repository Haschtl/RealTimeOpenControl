import os
# import csv
from PyQt5 import QtWidgets, QtGui, QtCore
from functools import partial
from PyQt5.QtCore import QCoreApplication
import traceback
from threading import Thread
import time
from ..lib import pyqt_customlib as pyqtlib
# from ..lib import general_lib as lib
from .remoteWidget import RemoteWidget
from . import settingsWidget
from .PluginDownloader import PluginDownloader
from ..RTLogger import RTLogger
import logging as log

log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

if True:
    translate = QCoreApplication.translate

    def _(text):
        return translate('rtoc', text)
else:
    import gettext
    _ = gettext.gettext


class Actions:
    def connectButtons(self):
        self.maxLengthSpinBox.editingFinished.connect(self.resizeLogger)
        self.clearButton.clicked.connect(self.clearDataAction)
        self.createGraphButton.clicked.connect(self.newPlotWidget)

        # Menubar
        self.loadSessionAction.triggered.connect(self.loadSessionTriggered)
        self.saveSessionAction.triggered.connect(self.saveSessionTriggered)
        self.importDataAction.triggered.connect(self.importDataTriggered)
        self.settingsAction.triggered.connect(self.settingsTriggered)
        self.exportDataAction.triggered.connect(self.exportDataTriggered)
        self.actionWebsocketServer.triggered.connect(self.toggleWebsocketServer)
        self.actionTelegramBot_2.triggered.connect(self.toggleTelegramBot)
        self.actionBotToken_2.triggered.connect(self.setBotToken)
        self.actionWebsocketPassword.triggered.connect(self.setWebsocketPassword)
        self.actionWebsocketPort.triggered.connect(self.setWebsocketPort)
        self.actionSearchRTOCServer.triggered.connect(self.searchRTOCServer)
        self.foundRTOCServerCallback.connect(self.foundRTOCServer, QtCore.Qt.QueuedConnection)

        self.getPluginsButton.triggered.connect(self.openPluginDownloader)

        self.systemTrayAction.triggered.connect(self.toggleSystemTray)

        self.menuFenster.aboutToShow.connect(self.updateWidgetCheckboxes)
        self.menuNetzwerk.aboutToShow.connect(self.updateNetworkMenu)
        self.deviceWidgetToggle.triggered.connect(self.toggleDeviceWidget)
        self.pluginsWidgetToggle.triggered.connect(self.togglePluginsWidget)
        self.scriptWidgetToggle.triggered.connect(self.toggleScriptWidget)
        self.eventWidgetToggle.triggered.connect(self.toggleEventWidget)
        self.deviceRAWWidgetToggle.triggered.connect(self.toggleRAWWidget)
        self.refreshDevicesButton.clicked.connect(self.reloadDevices)

        self.actionDeutsch.triggered.connect(
            partial(self.toggleLanguage, "de", self.actionDeutsch, [self.actionEnglish], False))
        self.actionEnglish.triggered.connect(
            partial(self.toggleLanguage, "en", self.actionEnglish, [self.actionDeutsch], False))
        if self.config['global']['language'] == 'de':
            self.toggleLanguage("de", self.actionDeutsch, [self.actionEnglish], True)
        else:
            self.toggleLanguage("en", self.actionEnglish, [self.actionDeutsch], True)

        self.helpAction.triggered.connect(self.showHelpWebsite)
        self.aboutAction.triggered.connect(self.showAboutMessage)
        self.checkUpdatesAction.triggered.connect(self.checkUpdates)
        self.pluginRepoAction.triggered.connect(self.showRepoWebsite)

        self.clearCacheAction.triggered.connect(self.clearCache)

        self.searchEdit.textChanged.connect(self.filterDevices)

        self.pluginSearchInput.textChanged.connect(self.filterDeviceRAW)

        self.pluginCallWidget.itemClicked.connect(self.deviceRAWCallback)

        self.pullFromDatabaseAction.triggered.connect(self.pushToDatabase)
        self.pushToDatabaseAction.triggered.connect(self.pullFromDatabase)
        self.exportDatabaseAction.triggered.connect(self.exportDatabase)

    def pullFromDatabase(self):
        self.clearData()
        self.logger.clear(False)
        self.logger.database.pullFromDatabase(True, True, True, True)
        for sigID in self.logger.database.signals().keys():
            name = self.logger.database.getSignalName(sigID)
            dataunit = self.logger.database.signals()[sigID][4]
            self.addNewSignal(sigID, name[0], name[1], dataunit)
        self.eventWidget.updateAllEvents()

    def pushToDatabase(self):
        self.logger.database.pushToDatabase()

    def exportDatabase(self):
        dir_path = self.config['global']['documentfolder']
        fileBrowser = QtWidgets.QFileDialog(self)
        fileBrowser.setDirectory(dir_path)
        fileBrowser.setNameFilters(
            ["File (*)"])
        fileBrowser.selectNameFilter("")
        fname, mask = fileBrowser.getSaveFileName(
            self, translate('RTOC', "Export database"), dir_path, "File (*)")
        if fname:
            fileName = fname
            if mask == 'File (*)':
                overwrite = False
                if os.path.exists(fileName):
                    overwrite = pyqtlib.alert_message(translate('RTOC', 'Overwrite'), translate('RTOC', 'Do you want to overwrite this file?'))
                self.logger.database.exportCSV(fileName, True)

    def toggleWebsocketServer(self):
        if self.config['websocket']['active']:
            self.config['websocket']['active'] = False
        else:
            self.config['websocket']['active'] = True
        self.logger.toggleWebsocketServer(self.config['websocket']['active'])
        self.actionWebsocketServer.setChecked(self.config['websocket']['active'])

    def toggleTelegramBot(self):
        if self.config['telegram']['active']:
            self.config['telegram']['active'] = False
        else:
            self.config['telegram']['active'] = True
        self.logger.toggleTelegramBot(self.config['telegram']['active'])
        self.actionTelegramBot_2.setChecked(self.config['telegram']['active'])

    def setBotToken(self):
        ans, ok = pyqtlib.text_message(
            self, translate('RTOC', "Enter bot token"), translate('RTOC', 'Please create a bot in Telegram with "Botfather",\ngenerate a bot and enter its token here'), self.config['telegram']['token'])
        if ok and self.logger.telegramBot is not None:
            self.logger.telegramBot.setToken(ans)
            self.actionBotToken_2.setText(self.config['telegram']['token'])

    def setWebsocketPassword(self):
        ans, ok = pyqtlib.text_message(
            self, translate('RTOC', "Enter Websocket-Password"), translate('RTOC', 'Protect your transfer from unauthorized users \nLeave empty to disable password'), self.config['websocket']['password'])
        if ok:
            self.logger.setWebsocketPassword(ans)
            if ans == '':
                self.actionWebsocketPassword.setText(translate('RTOC', 'Password protection: Off'))
            else:
                self.actionWebsocketPassword.setText(translate('RTOC', 'Password protection: On'))

    def setWebsocketPort(self):
        ans, ok = pyqtlib.text_message(
            self, translate('RTOC', "Enter Websocket Port"), translate('RTOC', 'Enter the port for Websocket-Communication with RTOC.'), str(self.config['websocket']['port']))
        if ok:
            try:
                ans = int(ans)
                if ans >= 0 and ans <= 65535:
                    self.logger.setWebsocketPort(ans)
                    self.actionWebsocketPort.setText(translate('RTOC', 'Port: ')+str(ans))
                else:
                    pyqtlib.info_message(translate('RTOC', 'Error'), translate('RTOC',
                        'Please enter a value between 0 and 65535'), '')
            except Exception:
                logging.debug(traceback.format_exc())
                pyqtlib.info_message(translate('RTOC', 'Error'), translate('RTOC',
                    'Please enter a value between 0 and 65535'), translate('RTOC', 'You input was invalid.'))

    def toggleSystemTray(self):
        if self.config['GUI']['systemTray']:
            self.config['GUI']['systemTray'] = False
        else:
            self.config['GUI']['systemTray'] = True
        self.systemTrayAction.setChecked(self.config['GUI']['systemTray'])

    def systemTrayClickAction(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Context:
            self.websocket_action.setChecked(self.config['websocket']['active'])
            self.hide_action.setChecked(self.config['GUI']['systemTray'])
        elif reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self.tray_icon.hide()
            self.show()

    def resizeLogger(self):
        newLength = self.maxLengthSpinBox.value()
        self.logger.database.resizeSignals(newLength)

    def clearDataAction(self):
        logging.info("deleting plot")
        if pyqtlib.alert_message(translate('RTOC', "Warning"), translate('RTOC', "Do you really want to delete all data?"), translate('RTOC', "(Irrevocably)")):

            if pyqtlib.alert_message(translate('RTOC', "Warning"), translate('RTOC', "Do you also want to delete the data in the database?"), translate('RTOC', "(Irrevocably!!)")):
                database=True
            else:
                database = False
            self.clearData()
            self.logger.clear(database)

    def loadSessionTriggered(self):
        dir_path = self.config['global']['documentfolder']
        fileBrowser = QtWidgets.QFileDialog(self)
        fileBrowser.setDirectory(dir_path)
        fileBrowser.setNameFilters(["Json (*.json)"])
        fileBrowser.selectNameFilter("")
        fname, mask = fileBrowser.getOpenFileName(
            self, translate('RTOC', "Load session"), dir_path, "Json (*.json)")
        # if fileBrowser.exec_():
        if fname:
            fileName = fname
            if mask == "Json (*.json)":
                self.loadSession(fileName)

    def saveSessionTriggered(self):
        dir_path = self.config['global']['documentfolder']
        fileBrowser = QtWidgets.QFileDialog(self)
        fileBrowser.setDirectory(dir_path)
        fileBrowser.setNameFilters(
            ["JSON-Datei (*.json)"])
        fileBrowser.selectNameFilter("")
        fname, mask = fileBrowser.getSaveFileName(
            self, translate('RTOC', "Save session"), dir_path, "JSON-Datei (*.json)")
        if fname:
            fileName = fname
            if mask == 'JSON-Datei (*.json)':
                overwrite = False
                if os.path.exists(fileName):
                    overwrite = pyqtlib.alert_message(translate('RTOC', 'Overwrite'), translate('RTOC', 'Do you want to overwrite the file or merge both files?'), translate('RTOC',
                        'With "Overwrite" the stored data will be lost.'), "", translate('RTOC', 'Overwrite'), translate('RTOC', 'Merge'))
                s = self.scriptWidget.getSession()
                self.logger.exportData(fileName, "json", overwrite=overwrite)

    def importData(self, filename):
        self.importer.loadCsv(filename)
        self.importer.show()

    def importCallback(self, signals):
        for sig in signals:
            self.logger.database.plot(*sig)

    def str2float(self, strung):
        # logging.debug(strung)
        strung = str(strung)
        strung = strung.replace(',', '.')
        if strung == '':
            return None
        return float(strung)

    def exportDataTriggered(self):
        dir_path = self.config['global']['documentfolder']
        fileBrowser = QtWidgets.QFileDialog(self)
        fileBrowser.setDirectory(dir_path)
        fileBrowser.setNameFilters(
            [translate('RTOC', "Excel-Table (*.xlsx)"), translate('RTOC', "CSV-File (*.csv)")])
        fileBrowser.selectNameFilter("")
        fname, mask = fileBrowser.getSaveFileName(
            self, translate('RTOC', "Export"), dir_path, translate('RTOC', "Excel-Table (*.xlsx);;CSV-File (*.csv)"))
        # if fileBrowser.exec_():
        if fname:
            fileName = fname
            if mask == translate('RTOC', 'Excel-Table (*.xlsx)'):
                self.logger.exportData(fileName, "xlsx")
            elif mask == translate('RTOC', 'CSV-File (*.csv)'):
                self.logger.exportData(fileName, "csv")

    def updateWidgetCheckboxes(self):
        self.scriptWidgetToggle.setChecked(self.scriptWidget.isVisible())
        self.pluginsWidgetToggle.setChecked(self.pluginsWidget.isVisible())
        self.deviceWidgetToggle.setChecked(self.deviceWidget.isVisible())
        self.eventWidgetToggle.setChecked(self.eventWidgets.isVisible())
        self.deviceRAWWidgetToggle.setChecked(self.deviceRAWWidget.isVisible())

    def toggleDeviceWidget(self):
        if self.deviceWidgetToggle.isChecked():
            self.deviceWidget.show()
            self.config['GUI']['deviceWidget'] = True
        else:
            self.deviceWidget.hide()
            self.config['GUI']['deviceWidget'] = False

    def toggleRAWWidget(self):
        if self.deviceRAWWidgetToggle.isChecked():
            self.deviceRAWWidget.show()
            self.config['GUI']['deviceRAWWidget'] = True
        else:
            self.deviceRAWWidget.hide()
            self.config['GUI']['deviceRAWWidget'] = False

    def toggleEventWidget(self):
        if self.eventWidgetToggle.isChecked():
            self.eventWidgets.show()
            self.config['GUI']['eventWidget'] = True
        else:
            self.eventWidgets.hide()
            self.config['GUI']['eventWidget'] = False

    def togglePluginsWidget(self):
        if self.pluginsWidgetToggle.isChecked():
            self.pluginsWidget.show()
            self.config['GUI']['pluginsWidget'] = True
        else:
            self.pluginsWidget.hide()
            self.config['GUI']['pluginsWidget'] = False

    def toggleScriptWidget(self):
        if self.scriptWidgetToggle.isChecked():
            self.scriptDockWidget.show()
            self.config['GUI']['scriptWidget'] = True
        else:
            self.scriptDockWidget.hide()
            self.config['GUI']['scriptWidget'] = False

    def importDataTriggered(self):
        dir_path = self.config['global']['documentfolder']
        fileBrowser = QtWidgets.QFileDialog(self)
        fileBrowser.setDirectory(dir_path)
        fileBrowser.setNameFilters(
            ["Table data (*.csv *.tsv, *.xls, *.xlsx, *.txt, *.mat, *.wav, *.wave, *)"])
        fileBrowser.selectNameFilter("")
        fname, mask = fileBrowser.getOpenFileName(
            self, "Export", dir_path, "Table data (*.csv *.tsv, *.xls, *.xlsx, *.txt, *.mat, *.wav, *.wave, *)")
        if fname:
            fileName = fname
            if mask == "Table data (*.csv *.tsv, *.xls, *.xlsx, *.txt, *.mat, *.wav, *.wave, *)":
                if fileName.endswith('.wav') or fileName.endswith('.wave'):
                    self.loadWav(fileName)
                else:
                    self.importData(fileName)

    def showAboutMessage(self):
        pyqtlib.info_message(translate('RTOC', "About"), "RealTime OpenControl ", translate('RTOC',
            "RealTime OpenControl (RTOC) is a free open source software under the BSD-3 license.\n\nAll icons are provided under the Creative Commons Attribution-NoDerivs 3.0 Unported license by icons8 (https://icons8.de)\n\nCopyright (C) 2018 Sebastian Keller"))

    def showHelpWebsite(self):
        url = "https://realtimeopencontrol.readthedocs.io/en/latest/"
        import webbrowser
        webbrowser.open(url, new=0, autoraise=True)

    def showRepoWebsite(self):
        url = "https://github.com/Haschtl/RTOC-Plugins"
        import webbrowser
        webbrowser.open(url, new=0, autoraise=True)

    def filterDevices(self, text):
        for idx in range(self.deviceLayout.count()):
            child = self.deviceLayout.itemAt(idx).widget()
            if text.lower() in child.text().lower() or text == "":
                child.show()
            else:
                child.hide()

    def filterDeviceRAW(self, tex):
        tex = tex+';'
        tex = tex.replace('; ', ';')
        for i in range(self.pluginCallWidget.count()):
            item = self.pluginCallWidget.item(i)
            found = False
            for text in tex.split(';'):
                # logging.debug(text)
                if (text != "" or tex == ';') and found is False:
                    if text.lower() in item.text().lower() or tex == ";":
                        item.setHidden(False)
                        found = True
                    else:
                        item.setHidden(True)

    def toggleLanguage(self, newlang, button, otherbuttons, force=False):
        button.setChecked(True)
        if newlang != self.config['global']['language'] or force is True:
            for b in otherbuttons:
                b.setChecked(False)
            self.config['global']['language'] = newlang
            if force is False:
                pyqtlib.info_message(translate('RTOC', "Language changed"),
                                     translate('RTOC', "Please restart RTOC"), "")

    def checkUpdates(self):
        current, available = self.logger.check_for_updates()
        if current is not None:
            text = translate('RTOC', 'Installed version: {}').format(current)
            if not available:
                info = translate('RTOC',
                    "Excuse me. I couldn't find RTOC on PyPi. Please have a look at 'https://pypi.org/project/RTOC/'.")
            else:
                text += translate('RTOC', ', Newest version: {}').format(available[0])
                if current == available[0]:
                    info = translate('RTOC', 'RTOC is up to date.')
                else:
                    info = translate('RTOC',
                        'New version available. Update in terminal:\n\n "pip3 install RTOC --upgrade"\n')
        else:
            text = translate('RTOC', 'RTOC was not installed with PyPi.')
            info = translate('RTOC', 'To check for new versions, install RTOC with "pip3 install RTOC".')

        pyqtlib.info_message(translate('RTOC', 'Version'), text, info)

    def clearCache(self):
        ok = pyqtlib.alert_message(translate('RTOC', 'Clear cache'), translate('RTOC', 'Are you sure you want to empty the cache?'), translate('RTOC',
            'This will cause all settings to be lost.'))
        if ok:
            self.plotStyles = {}
            self.logger.clearCache()

    def openPluginDownloader(self):
        self.pluginDownloader = PluginDownloader(
            self.config['global']['documentfolder'], 'Haschtl/RTOC-Plugins', self)
        self.pluginDownloader.show()

    def updateDeviceRAW(self):
        self.pluginCallWidget.clear()
        for name in self.logger.devicenames.keys():
            if self.logger.pluginStatus[name] is True:
                for fun in self.logger.pluginFunctions.keys():
                    hiddenFuncs = ["loadGUI", "updateT", "stream", "plot", "event", "close", "cancel", "start", "setSamplerate","setDeviceName",'setPerpetualTimer','setInterval','getDir', 'telegram_send_plot', 'telegram_send_photo', 'telegram_send_message', 'telegram_send_document']

                    if fun.startswith(name+'.') and fun not in [name+'.'+i for i in hiddenFuncs]:
                        parStr = ', '.join(self.logger.pluginFunctions[fun][1])
                        funStr = fun+'('+parStr+')'
                        self.pluginCallWidget.addItem(funStr)
                for fun in self.logger.pluginParameters.keys():
                    hiddenParams = ["run", "smallGUI", 'widget','lockPerpetialTimer', 'logger']

                    if fun.startswith(name+'.') and fun not in [name+'.'+i for i in hiddenParams]:
                        self.pluginCallWidget.addItem(fun)

        self.logger.remote.getDevices()
        dicti = self.logger.remote.devices
        # logging.debug(dict)
        for host in dicti.keys():  # iterating hosts
            for sig in dicti[host]:  # iterating RTRemote.SingleConn.pluglist (getPluginList)
                if dicti[host][sig]['status']:
                    for element in dicti[host][sig]['functions']:
                        # self.pluginCallWidget.addItem(host+":"+sig+"."+element+'()')
                        item = QtWidgets.QListWidgetItem(host+":"+sig+"."+element[0]+'()')
                        item.setBackground(QtGui.QColor(13, 71, 97))
                        self.pluginCallWidget.addItem(item)
                    for element in dicti[host][sig]['parameters']:
                        # self.pluginCallWidget.addItem(host+":"+sig+"."+element[0])
                        item = QtWidgets.QListWidgetItem(host+":"+sig+"."+element[0])
                        item.setBackground(QtGui.QColor(13, 71, 97))
                        self.pluginCallWidget.addItem(item)

    def deviceRAWCallback(self, strung):
        dict = {}

        strung = strung.text()
        a = strung.split(':')
        if len(a) < 2:  # if the device is local
            devsplit = strung.split('.')
            host = 'local'
        else:
            devsplit = a[1].split('.')
            host = a[0]
        print(devsplit)
        if len(devsplit) == 2:
            plugin = devsplit[0]
            function = devsplit[1]
            print(function)
            if '(' in function and function.endswith(')'):
                text, ok = pyqtlib.text_message(self, translate('RTOC',
                    'Call device-function'), strung, translate('RTOC', 'Function parameters'))
                if ok:
                    self.par = []
                    try:
                        exec('self.par = ['+text+"]")
                        function = function[:function.index('(')]+'()'
                        dict = {plugin: {function: self.par}}
                        if host == 'local':
                            self.logger.handleTcpPlugins(dict)
                        else:
                            # logging.info('remotefunction')
                            ans = self.logger.remote.callFuncOrParam(
                                host, plugin, function, self.par)
                    except Exception:
                        tb = traceback.format_exc()
                        logging.debug(tb)
                        pyqtlib.info_message(translate('RTOC', 'Error'), translate('RTOC',
                            'Function-arguments invalid'), translate('RTOC', "Please enter valid arguments"))
            else:
                if host == 'local':
                    ans = self.logger.handleTcpPlugins({plugin: {'get': [function]}})
                    text, ok = pyqtlib.text_message(self, translate('RTOC',
                        'Change device parameter'), strung, str(ans[plugin]['get'][0]))
                    if ok:
                        self.par = []
                        try:
                            exec('self.par = '+text)
                            dict = {plugin: {function: self.par}}
                            self.logger.handleTcpPlugins(dict)
                        except Exception:
                            tb = traceback.format_exc()
                            logging.debug(tb)
                            pyqtlib.info_message(translate('RTOC', 'Error'), translate('RTOC',
                                'Value invalid'), translate('RTOC', "Please enter a valid value for this parameter"))
                else:
                    # logging.info('remoteparameter')
                    current_value = self.logger.remote.getParam(host, plugin, function)
                    if current_value is not None:
                        text, ok = pyqtlib.text_message(self, translate('RTOC',
                            'Change device parameter'), strung, str(current_value))
                        if ok:
                            self.par = []
                            try:
                                exec('self.par = '+text)
                                # dict = {plugin: {function:self.par}}
                                # self.logger.handleTcpPlugins(dict)
                                ans = self.logger.remote.callFuncOrParam(
                                    host, plugin, function, self.par)
                            except Exception:
                                tb = traceback.format_exc()
                                logging.debug(tb)
                                pyqtlib.info_message(translate('RTOC', 'Error'), translate('RTOC',
                                    'Value invalid'), translate('RTOC', "Please enter a valid value for this parameter"))
                    else:
                        logging.error('Failed to load parameter')

    def updateNetworkMenu(self):
        self.menuMit_Remotehost_verbinden.clear()
        self.menuAktive_Verbindungen.clear()
        newAction = self.menuMit_Remotehost_verbinden.addAction(translate('RTOC', 'New Host'))
        self.menuMit_Remotehost_verbinden.addSeparator()
        activeConnections = self.logger.remote.activeConnections()
        for s in self.config['websocket']['knownHosts'].keys():
            if s not in activeConnections:
                action = self.menuMit_Remotehost_verbinden.addAction(
                    self.config['websocket']['knownHosts'][s][0]+' ('+s+')')
                action.triggered.connect(
                    partial(self.connectHost, s, self.config['websocket']['knownHosts'][s][0], self.config['websocket']['knownHosts'][s][1]))
        for s in activeConnections:
            action = self.menuAktive_Verbindungen.addAction(s)

            action.triggered.connect(partial(self.EditRemoteHost, s))
        newAction.triggered.connect(self.connectNewHost)

    def EditRemoteHost(self, host):
        for widget in self.remoteHostWidgets:
            if host == widget.widget().hostname:
                widget.show()

    def connectNewHost(self):
        ans, ok = pyqtlib.text_message(
            self, translate('RTOC', 'Connect with new host'), translate('RTOC', 'Connect to new remote RTOC. Enter a valid address\n(Including port ":")'), '127.0.0.1:5050')
        if ok:
            ans2, ok = pyqtlib.text_message(
                self, translate('RTOC', 'Enter name'), translate('RTOC', 'Enter a name for this host\n(May not contain "." or ":")'), 'RemoteRTOC')
            if ok:
                ans2 = ans2.replace('.', 'Dot').replace(':', 'DDot')
                if len(ans.split(':')) == 2:
                    if ans not in self.config['websocket']['knownHosts'].keys():
                        self.config['websocket']['knownHosts'][ans] = [ans2, '']
                        # self.logger.remote.connect(ans)
                    connected = self.connectHost(ans, ans2)
                elif len(ans.split(':')) == 1:
                    ans = ans+':5050'
                    if ans not in self.config['websocket']['knownHosts'].keys():
                        self.config['websocket']['knownHosts'][ans] = [ans2, '']
                        # self.logger.remote.connect(ans)
                    connected = self.connectHost(ans, ans2)
                return connected
        return False

    def addRemoteHostWidget(self, host, name, port):
        remoteHostWidget = QtWidgets.QDockWidget(name, self)
        widget = RemoteWidget(self, host, remoteHostWidget, name, port)
        remoteHostWidget.setWidget(widget)
        self.remoteHostWidgets.append(remoteHostWidget)
        # self.tabifyDockWidget(self.graphWidget, self.remoteHostWidgets[-1])
        self.tabifyDockWidget(self.deviceWidget, self.remoteHostWidgets[-1])
        self.remoteHostWidgets[-1].show()

    def settingsTriggered(self):
        default = RTLogger.defaultconfig
        self.settingsWidget = settingsWidget.SettingsWidget(self.config, default, self)
        self.settingsWidget.show()

    def searchRTOCServer(self):
        t = Thread(target=self.logger.remote.searchWebsocketHosts,
                   args=(5050, self.foundRTOCServerCallback,))
        t.start()

    def foundRTOCServer(self, hostlist):
        strung = '\n'.join(hostlist)
        pyqtlib.info_message(translate('RTOC', "Finished"), translate('RTOC', "RTOC-Search completed"),
                             translate('RTOC', "{} servers found:\n{}").format(len(hostlist)-1, strung))

    def connectHost(self, host, name, password=''):
        hostsplit = host.split(':')
        hostname = host
        host = hostsplit[0]
        port = int(hostsplit[1])
        self.logger.remote.connect(host, port, name, password)
        retry = True
        host = hostsplit[0]
        self.logger.remote.getConnection(host, port).__password = password
        while retry:
            retry = False
            status = self.logger.remote.getConnection(host, port).status
            if status == "protected":
                text, ok2 = pyqtlib.text_message(None, translate('RTOC', 'Password'), translate('RTOC',
                    "The RTOC server {} is password-protected. Please enter your password.").format(hostname),  translate('RTOC', 'Websocket-Password'))
                if ok2:
                    # self.logger.remote.getConnection(host, port).__password = text
                    self.logger.remote.connect(host, port, name, text)
                    retry = True
                    ok3 = pyqtlib.alert_message(translate('RTOC', 'Save password'), translate('RTOC',
                        'Do you want to save this password?'), '')
                    if ok3:
                        self.logger.config['websocket']['knownHosts'][hostname][1] = text
            elif status == "connected":
                pyqtlib.info_message(translate('RTOC', 'Connection established'), translate('RTOC',
                    'Connection to {} on port {} established.').format(host, port), '')

                self.addRemoteHostWidget(host, name, port)
                return True
            elif status == "wrongPassword":
                text, ok = pyqtlib.text_message(None, translate('RTOC', 'Protected'), translate('RTOC', 'Connection to {} on port {} not established').format(host, port), translate('RTOC', 'Password is wrong.'))
                if ok:
                    # self.logger.remote.getConnection(host, port).__password = text
                    self.logger.remote.connect(host, port, name, text)
                    retry = True
                    ok3 = pyqtlib.alert_message(translate('RTOC', 'Save password'), translate('RTOC',
                        'Do you want to save this password?'), '')
                    if ok3:
                        self.logger.config['websocket']['knownHosts'][hostname][1] = text
            elif status == "error":
                ok = pyqtlib.alert_message(translate('RTOC', 'Connection error'), translate('RTOC', 'Error. Connection to {} on port {} could not be established.').format(host, port), translate('RTOC', 'Retry?'))
                if ok:
                    self.logger.remote.connect(host, port, name, password)
                    retry = True
            elif status == "connecting...":
                retry = True
                # pyqtlib.info_message(translate('RTOC', 'Connection established'), translate('RTOC',
                #     'Connection to {} on port {} established.').format(host, port), '')
                time.sleep(0.1)
                # self.addRemoteHostWidget(host, name, port)
                # return True
            elif status == "closed":
                print(status)
                pyqtlib.info_message('Connection closed',
                                     'The connection has been accidently closed', "Maybe you're trying to connect to an SSL-encrypted port, which is not on Port 443.".format(status))
            else:
                print(status)
                pyqtlib.info_message('End of the universe',
                                     'You reached the end of the universe', "This shouldn't happen. Status {}".format(status))
        return False
