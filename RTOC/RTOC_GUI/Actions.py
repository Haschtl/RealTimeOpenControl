import os
# import csv
from PyQt5 import QtWidgets, QtGui, QtCore
from functools import partial
from PyQt5.QtCore import QCoreApplication
import traceback
from threading import Thread

from ..lib import pyqt_customlib as pyqtlib
# from ..lib import general_lib as lib
from .remoteWidget import RemoteWidget
from . import settingsWidget
from .PluginDownloader import PluginDownloader
from ..RTLogger import RTLogger
import logging as log

translate = QCoreApplication.translate
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)


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
        self.actionTCPServer_2.triggered.connect(self.toggleTcpServer)
        self.HTMLServerAction_2.triggered.connect(self.toggleHtmlServer)
        self.actionTelegramBot_2.triggered.connect(self.toggleTelegramBot)
        self.actionBotToken_2.triggered.connect(self.setBotToken)
        self.actionTCPPassword_2.triggered.connect(self.setTCPPassword)
        self.actionTCPPort_2.triggered.connect(self.setTCPPort)
        self.actionUpdate_Rate_1Hz_2.triggered.connect(self.setRemoteSamplerate)
        self.actionUpdate_Rate_1Hz_2.setText(
            'Update-Rate: '+str(self.config['tcp']['remoteRefreshRate'])+" Hz")
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
            ["Datei (*)"])
        fileBrowser.selectNameFilter("")
        fname, mask = fileBrowser.getSaveFileName(
            self, self.tr("Datenbank exportieren"), dir_path, "Datei (*)")
        if fname:
            fileName = fname
            if mask == 'Datei (*)':
                overwrite = False
                if os.path.exists(fileName):
                    overwrite = pyqtlib.alert_message(self.tr('Überschreiben'), self.tr('Wollen Sie die Datei überschreiben?'))
                self.logger.database.exportCSV(fileName, True)

    def toggleTcpServer(self):
        if self.config['tcp']['active']:
            self.config['tcp']['active'] = False
        else:
            self.config['tcp']['active'] = True
        self.logger.toggleTcpServer(self.config['tcp']['active'])
        self.actionTCPServer_2.setChecked(self.config['tcp']['active'])

    def toggleHtmlServer(self):
        # if self.config["rtoc_web"]:
        #     self.config["rtoc_web"] = False
        # else:
        #     self.config["rtoc_web"] = True
        pyqtlib.info_message(self.tr("RTOC_Web Fehler"), self.tr("RTOC_Web kann nicht mehr parallel mit der Benutzeroberfläche gestartet werden. Bitte beende RTOC und starte RTOC_Web mit 'python3 -m RTOC.RTLogger -w'"),
                             self.tr("Wenn du die GUI benötigst, starte danach eine lokale Remote-Verbindung mit 'python3 -m RTOC -r 127.0.0.1'"))
        # self.HTMLServerAction_2.setChecked(self.config["rtoc_web"])

    def toggleTelegramBot(self):
        if self.config['telegram']['active']:
            self.config['telegram']['active'] = False
        else:
            self.config['telegram']['active'] = True
        self.logger.toggleTelegramBot(self.config['telegram']['active'])
        self.actionTelegramBot_2.setChecked(self.config['telegram']['active'])

    def setBotToken(self):
        ans, ok = pyqtlib.text_message(
            self, self.tr("Bot Token eingeben"), self.tr('Bitte erzeugen sie in Telegram mit "Botfather" einen Bot,\n generiere einen Bot und füge dessen Token hier ein'), self.config['telegram']['token'])
        if ok and self.logger.telegramBot is not None:
            self.logger.telegramBot.setToken(ans)
            self.actionBotToken_2.setText(self.config['telegram']['token'])

    def setTCPPassword(self):
        ans, ok = pyqtlib.text_message(
            self, self.tr("TCP Passwort eingeben"), self.tr('Schütze deine Übertragung vor unerwünschten Gästen\nLeer lassen, um Passwort zu deaktivieren'), self.config['tcp']['password'])
        if ok:
            self.logger.setTCPPassword(ans)
            if ans == '':
                self.actionTCPPassword_2.setText(self.tr('Passwort-Schutz: Aus'))
            else:
                self.actionTCPPassword_2.setText(self.tr('Passwort-Schutz: An'))

    def setTCPPort(self):
        ans, ok = pyqtlib.text_message(
            self, self.tr("TCP Port eingeben"), self.tr('Gib den Port an, an welchem dein Rechner für RTOC erreichbar ist.'), self.config['tcp']['port'])
        if ok:
            try:
                ans = int(ans)
                if ans >= 0 and ans <= 65535:
                    self.logger.setTCPPort(ans)
                    self.actionTCPPort_2.setText(self.tr('Port: ')+str(ans))
                else:
                    pyqtlib.info_message(self.tr('Fehler'), self.tr(
                        'Bitte gib eine Zahl zwischen 0 und 65535 an'), '')
            except Exception:
                logging.debug(traceback.format_exc())
                pyqtlib.info_message(self.tr('Fehler'), self.tr(
                    'Bitte gib eine Zahl zwischen 0 und 65535 an'), self.tr('Ihre Eingabe war ungültig.'))

    def toggleSystemTray(self):
        if self.config['GUI']['systemTray']:
            self.config['GUI']['systemTray'] = False
        else:
            self.config['GUI']['systemTray'] = True
        self.systemTrayAction.setChecked(self.config['GUI']['systemTray'])

    def systemTrayClickAction(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Context:
            self.tcp_action.setChecked(self.config['tcp']['active'])
            self.hide_action.setChecked(self.config['GUI']['systemTray'])
        elif reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self.tray_icon.hide()
            self.show()

    def resizeLogger(self):
        newLength = self.maxLengthSpinBox.value()
        self.logger.database.resizeSignals(newLength)

    def clearDataAction(self):
        logging.info("deleting plot")
        if pyqtlib.alert_message(self.tr("Warnung"), self.tr("Wollen Sie wirklich alle Daten löschen?"), self.tr("(Unwiederrufbar)")):

            if pyqtlib.alert_message(self.tr("Warnung"), self.tr("Wollen Sie auch die Daten in der Datenbank löschen?"), self.tr("(Unwiederrufbar!!)")):
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
            self, self.tr("Session laden"), dir_path, "Json (*.json)")
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
            self, self.tr("Session speichern"), dir_path, "JSON-Datei (*.json)")
        if fname:
            fileName = fname
            if mask == 'JSON-Datei (*.json)':
                overwrite = False
                if os.path.exists(fileName):
                    overwrite = pyqtlib.alert_message(self.tr('Überschreiben'), self.tr('Wollen Sie die Datei überschreiben oder beide Dateien zusammenführen?'), self.tr(
                        'Bei "Überschreiben" gehen die gespeicherten Daten verloren.'), "", self.tr('Überschreiben'), self.tr('Zusammenführen'))
                s = self.scriptWidget.getSession()
                self.logger.exportData(fileName, "json", scripts=s, overwrite=overwrite)

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
            [self.tr("Excel-Tabelle (*.xlsx)"), self.tr("CSV-Datei (*.csv)")])
        fileBrowser.selectNameFilter("")
        fname, mask = fileBrowser.getSaveFileName(
            self, self.tr("Export"), dir_path, self.tr("Excel-Tabelle (*.xlsx);;CSV-Datei (*.csv)"))
        # if fileBrowser.exec_():
        if fname:
            fileName = fname
            if mask == self.tr('Excel-Tabelle (*.xlsx)'):
                self.logger.exportData(fileName, "xlsx")
            elif mask == self.tr('CSV-Datei (*.csv)'):
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
            ["Tabelle (*.csv *.tsv, *.xls, *.xlsx, *.txt, *.mat, *.wav, *.wave, *)"])
        fileBrowser.selectNameFilter("")
        fname, mask = fileBrowser.getOpenFileName(
            self, "Export", dir_path, "Tabelle (*.csv *.tsv, *.xls, *.xlsx, *.txt, *.mat, *.wav, *.wave, *)")
        if fname:
            fileName = fname
            if mask == "Tabelle (*.csv *.tsv, *.xls, *.xlsx, *.txt, *.mat, *.wav, *.wave, *)":
                if fileName.endswith('.wav') or fileName.endswith('.wave'):
                    self.loadWav(fileName)
                else:
                    self.importData(fileName)

    def showAboutMessage(self):
        pyqtlib.info_message(self.tr("Über"), "RealTime OpenControl 2.0b0", self.tr(
            "RealTime OpenControl (RTOC) ist eine freie OpenSource Software unter der BSD-3-Lizenz.\n\nAlle Symbole werden unter der 'Creative Commons Attribution-NoDerivs 3.0 Unported' Lizenz bereitgestellt von icons8 (https://icons8.de)\n\nCopyright (C) 2018 Sebastian Keller"))

    def showHelpWebsite(self):
        url = "https://github.com/Haschtl/RealTimeOpenControl/wiki"
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
                pyqtlib.info_message(self.tr("Sprache geändert"),
                                     self.tr("Bitte Programm neustarten"), "")

    def checkUpdates(self):
        current, available = self.logger.check_for_updates()
        if current is not None:
            text = self.tr('Installierte Version: ')+str(current)
            if not available:
                info = self.tr(
                    "Entschuldigung. Konnte RTOC bei PyPi nicht finden. Schau mal bei 'https://pypi.org/project/RTOC/'")
            else:
                text += self.tr(', Neuste Version: ')+str(available[0])
                if current == available[0]:
                    info = self.tr('RTOC ist auf dem neusten Stand.')
                else:
                    info = self.tr(
                        'Neue Version verfügbar. Update mit der Konsole:\n\n"pip3 install RTOC --upgrade"\n')
        else:
            text = self.tr('RTOC wurde nicht mit PyPi installiert.')
            info = self.tr('Um die Version zu überprüfen, installiere RTOC mit "pip3 install RTOC"')

        pyqtlib.info_message(self.tr('Version'), text, info)

    def clearCache(self):
        ok = pyqtlib.alert_message(self.tr('Cache leeren'), self.tr('Wollen Sie wirklich den Cache leeren?'), self.tr(
            'Dadurch gehen gespeicherte Ploteinstellungen sowie Einstellungen verloren.'))
        if ok:
            self.plotStyles = {}
            self.logger.clearCache()

    def openPluginDownloader(self):
        self.pluginDownloader = PluginDownloader(
            self.config['global']['documentfolder'], 'Haschtl/RTOC-Plugins', self)
        self.pluginDownloader.show()

    def updateDeviceRAW(self):
        self.pluginCallWidget.clear()
        dict = self.logger.getPluginDict()
        for sig in dict.keys():
            if dict[sig]['status']:
                for element in dict[sig]['functions']:
                    self.pluginCallWidget.addItem(sig+"."+element+'()')
                for element in dict[sig]['parameters']:
                    self.pluginCallWidget.addItem(sig+"."+element[0])

        self.logger.remote.getDevices()
        dict = self.logger.remote.devices
        # logging.debug(dict)
        for host in dict.keys():
            for sig in dict[host]:
                if dict[host][sig]['status']:
                    for element in dict[host][sig]['functions']:
                        # self.pluginCallWidget.addItem(host+":"+sig+"."+element+'()')
                        item = QtWidgets.QListWidgetItem(host+":"+sig+"."+element+'()')
                        item.setBackground(QtGui.QColor(13, 71, 97))
                        self.pluginCallWidget.addItem(item)
                    for element in dict[host][sig]['parameters']:
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

        if len(devsplit) == 2:
            plugin = devsplit[0]
            function = devsplit[1]

            if function.endswith('()'):
                text, ok = pyqtlib.text_message(self, self.tr(
                    'Geräte-Funktion ausführen'), strung, self.tr('Funktionsparameter'))
                if ok:
                    self.par = []
                    try:
                        exec('self.par = ['+text+"]")
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
                        pyqtlib.info_message(self.tr('Fehler'), self.tr(
                            'Funktionsparameter sind nicht gültig'), self.tr("Bitte geben Sie gültige Parameter an"))
            else:
                if host == 'local':
                    ans = self.logger.handleTcpPlugins({plugin: {'get': [function]}})
                    text, ok = pyqtlib.text_message(self, self.tr(
                        'Geräte-Parameter ändern'), strung, str(ans[plugin]['get'][0]))
                    if ok:
                        self.par = []
                        try:
                            exec('self.par = '+text)
                            dict = {plugin: {function: self.par}}
                            self.logger.handleTcpPlugins(dict)
                        except Exception:
                            tb = traceback.format_exc()
                            logging.debug(tb)
                            pyqtlib.info_message(self.tr('Fehler'), self.tr(
                                'Wert ungültig'), self.tr("Bitte geben Sie einen gültigen Wert an"))
                else:
                    # logging.info('remoteparameter')
                    current_value = self.logger.remote.getParam(host, plugin, function)
                    if current_value is not None:
                        text, ok = pyqtlib.text_message(self, self.tr(
                            'Geräte-Parameter ändern'), strung, str(current_value))
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
                                pyqtlib.info_message(self.tr('Fehler'), self.tr(
                                    'Wert ungültig'), self.tr("Bitte geben Sie einen gültigen Wert an"))
                    else:
                        logging.error('Failed to load parameter')

    def updateNetworkMenu(self):
        self.menuMit_Remotehost_verbinden.clear()
        self.menuAktive_Verbindungen.clear()
        newAction = self.menuMit_Remotehost_verbinden.addAction(self.tr('Neuer Host'))
        self.menuMit_Remotehost_verbinden.addSeparator()
        activeConnections = self.logger.remote.activeConnections()
        for s in self.config['tcp']['knownHosts'].keys():
            if s not in activeConnections:
                action = self.menuMit_Remotehost_verbinden.addAction(
                    self.config['tcp']['knownHosts'][s][0]+' ('+s+')')
                action.triggered.connect(
                    partial(self.connectHost, s, self.config['tcp']['knownHosts'][s][0], self.config['tcp']['knownHosts'][s][1]))
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
            self, 'Verbinde mit neuem Host', 'Verbinde RTOC mit einem neuen Host\n(Inklusive Port ":")', '127.0.0.1')
        if ok:
            ans2, ok = pyqtlib.text_message(
                self, 'Name angeben', 'Gib einen Namen für diesen Host an\n(Darf weder "." noch ":" enthalten)', 'RemoteRTOC')
            if ok:
                ans2 = ans2.replace('.', 'Dot').replace(':', 'DDot')
                if len(ans.split(':')) == 2:
                    if ans not in self.config['tcp']['knownHosts'].keys():
                        self.config['tcp']['knownHosts'][ans] = [ans2, '']
                        # self.logger.remote.connect(ans)
                    connected = self.connectHost(ans, ans2)
                elif len(ans.split(':')) == 1:
                    ans = ans+':5050'
                    if ans not in self.config['tcp']['knownHosts'].keys():
                        self.config['tcp']['knownHosts'][ans] = [ans2, '']
                        # self.logger.remote.connect(ans)
                    connected = self.connectHost(ans, ans2)
                return connected
        return False

    def addRemoteHostWidget(self, host, name):
        remoteHostWidget = QtWidgets.QDockWidget(name, self)
        widget = RemoteWidget(self, host, remoteHostWidget, name)
        remoteHostWidget.setWidget(widget)
        self.remoteHostWidgets.append(remoteHostWidget)
        self.tabifyDockWidget(self.graphWidget, self.remoteHostWidgets[-1])
        self.remoteHostWidgets[-1].show()

    def setRemoteSamplerate(self):
        ans, ok = pyqtlib.text_message(
            self, 'Remote Updaterate ändern', 'Ändere die Updaterate, mit der Remote-Geräte abgefragt werden', '1')
        if ok:
            try:
                samplerate = int(ans)
                self.logger.remote.setSamplerate(samplerate)
                self.actionUpdate_Rate_1Hz_2.setText('Update-Rate: '+str(samplerate))
            except ValueError:
                logging.debug(traceback.format_exc())
                pyqtlib.info_message('Fehler', 'Deine Eingabe war falsch.', '')

    def settingsTriggered(self):
        default = RTLogger.defaultconfig
        self.settingsWidget = settingsWidget.SettingsWidget(self.config, default, self)
        self.settingsWidget.show()

    def searchRTOCServer(self):
        t = Thread(target=self.logger.remote.searchTCPHosts,
                   args=(5050, self.foundRTOCServerCallback,))
        t.start()

    def foundRTOCServer(self, hostlist):
        strung = '\n'.join(hostlist)
        pyqtlib.info_message(self.tr("Fertig"), self.tr("RTOC-Suche abgeschlossen"),
                             str(len(hostlist)-1)+self.tr(" Server gefunden:")+'\n'+strung)

    def connectHost(self, host, name, password=''):
        hostsplit = host.split(':')
        hostname = host
        host = hostsplit[0]
        port = int(hostsplit[1])
        self.logger.remote.connect(host, port, name, password)
        retry = True
        host = hostsplit[0]
        self.logger.remote.getConnection(host).tcppassword = password
        while retry:
            retry = False
            status = self.logger.remote.getConnection(host).status
            if status is "protected":
                text, ok2 = pyqtlib.text_message(None, self.tr('Passwort'), self.tr(
                    "Der RTOC-Server ")+hostname + self.tr(" ist passwortgeschützt. Bitte Passwort eintragen"),  self.tr('TCP-Passwort'))
                if ok2:
                    self.logger.remote.getConnection(host).tcppassword = text
                    self.logger.remote.connect(host, port, name, text)
                    retry = True
                    ok3 = pyqtlib.alert_message(self.tr('Password speichern'), self.tr(
                        'Möchtest du das Passwort speichern?'), '')
                    if ok3:
                        self.logger.config['tcp']['knownHosts'][hostname][1] = text
            elif status is "connected":
                pyqtlib.info_message(self.tr('Verbindung hergestellt'), self.tr(
                    'Verbindung zu ')+host+self.tr(' an Port ')+str(port)+self.tr(' hergestellt.'), '')

                self.addRemoteHostWidget(host, name)
                return True
            elif status is "wrongPassword":
                text, ok = pyqtlib.text_message(None, self.tr('Geschützt'), self.tr('Verbindung zu ')+host+self.tr(
                    ' an Port ')+str(port)+self.tr(' wurde nicht hergestellt.'), self.tr('Passwort ist falsch.'))
                if ok:
                    self.logger.remote.getConnection(host).tcppassword = text
                    self.logger.remote.connect(host, port, name, text)
                    retry = True
                    ok3 = pyqtlib.alert_message(self.tr('Password speichern'), self.tr(
                        'Möchtest du das Passwort speichern?'), '')
                    if ok3:
                        self.logger.config['tcp']['knownHosts'][hostname][1] = text
            elif status is "error":
                ok = pyqtlib.alert_message(self.tr('Verbindungsfehler'), self.tr('Fehler. Verbindung zu ')+host+self.tr(
                    ' an Port ')+str(port)+self.tr(' konnte nicht hergestellt werden.'), self.tr('Erneut versuchen?'))
                if ok:
                    self.logger.remote.connect(host, port, name, password)
                    retry = True
            elif status is "connecting...":
                retry = False
                return True
            else:
                pyqtlib.info_message('End of the universe',
                                     'You reached the end of the universe', "This shouldn't happen")
        return False
