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
            self, translate('RTOC', "Datenbank exportieren"), dir_path, "Datei (*)")
        if fname:
            fileName = fname
            if mask == 'Datei (*)':
                overwrite = False
                if os.path.exists(fileName):
                    overwrite = pyqtlib.alert_message(translate('RTOC', '\xdcberschreiben'), translate('RTOC', 'Wollen Sie die Datei \xfcberschreiben?'))
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
        pyqtlib.info_message(translate('RTOC', "RTOC_Web Fehler"), translate('RTOC', "RTOC_Web kann nicht mehr parallel mit der Benutzeroberfl\xe4che gestartet werden. Bitte beende RTOC und starte RTOC_Web mit 'python3 -m RTOC.RTLogger -w'"),
                             translate('RTOC', "Wenn du die GUI ben\xf6tigst, starte danach eine lokale Remote-Verbindung mit 'python3 -m RTOC -r 127.0.0.1'"))
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
            self, translate('RTOC', "Bot Token eingeben"), translate('RTOC', 'Bitte erzeugen sie in Telegram mit "Botfather" einen Bot,\n generiere einen Bot und f\xfcge dessen Token hier ein'), self.config['telegram']['token'])
        if ok and self.logger.telegramBot is not None:
            self.logger.telegramBot.setToken(ans)
            self.actionBotToken_2.setText(self.config['telegram']['token'])

    def setTCPPassword(self):
        ans, ok = pyqtlib.text_message(
            self, translate('RTOC', "TCP Passwort eingeben"), translate('RTOC', 'Sch\xfctze deine \xdcbertragung vor unerw\xfcnschten G\xe4sten\nLeer lassen, um Passwort zu deaktivieren'), self.config['tcp']['password'])
        if ok:
            self.logger.setTCPPassword(ans)
            if ans == '':
                self.actionTCPPassword_2.setText(translate('RTOC', 'Passwort-Schutz: Aus'))
            else:
                self.actionTCPPassword_2.setText(translate('RTOC', 'Passwort-Schutz: An'))

    def setTCPPort(self):
        ans, ok = pyqtlib.text_message(
            self, translate('RTOC', "TCP Port eingeben"), translate('RTOC', 'Gib den Port an, an welchem dein Rechner f\xfcr RTOC erreichbar ist.'), self.config['tcp']['port'])
        if ok:
            try:
                ans = int(ans)
                if ans >= 0 and ans <= 65535:
                    self.logger.setTCPPort(ans)
                    self.actionTCPPort_2.setText(translate('RTOC', 'Port: ')+str(ans))
                else:
                    pyqtlib.info_message(translate('RTOC', 'Fehler'), _(
                        'Bitte gib eine Zahl zwischen 0 und 65535 an'), '')
            except Exception:
                logging.debug(traceback.format_exc())
                pyqtlib.info_message(translate('RTOC', 'Fehler'), _(
                    'Bitte gib eine Zahl zwischen 0 und 65535 an'), translate('RTOC', 'Ihre Eingabe war ung\xfcltig.'))

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
        if pyqtlib.alert_message(translate('RTOC', "Warnung"), translate('RTOC', "Wollen Sie wirklich alle Daten l\xf6schen?"), translate('RTOC', "(Unwiederrufbar)")):

            if pyqtlib.alert_message(translate('RTOC', "Warnung"), translate('RTOC', "Wollen Sie auch die Daten in der Datenbank l\xf6schen?"), translate('RTOC', "(Unwiederrufbar!!)")):
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
            self, translate('RTOC', "Session laden"), dir_path, "Json (*.json)")
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
            self, translate('RTOC', "Session speichern"), dir_path, "JSON-Datei (*.json)")
        if fname:
            fileName = fname
            if mask == 'JSON-Datei (*.json)':
                overwrite = False
                if os.path.exists(fileName):
                    overwrite = pyqtlib.alert_message(translate('RTOC', '\xdcberschreiben'), translate('RTOC', 'Wollen Sie die Datei \xfcberschreiben oder beide Dateien zusammenf\xfchren?'), _(
                        'Bei "\xdcberschreiben" gehen die gespeicherten Daten verloren.'), "", translate('RTOC', '\xdcberschreiben'), translate('RTOC', 'Zusammenf\xfchren'))
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
            [translate('RTOC', "Excel-Tabelle (*.xlsx)"), translate('RTOC', "CSV-Datei (*.csv)")])
        fileBrowser.selectNameFilter("")
        fname, mask = fileBrowser.getSaveFileName(
            self, translate('RTOC', "Export"), dir_path, translate('RTOC', "Excel-Tabelle (*.xlsx);;CSV-Datei (*.csv)"))
        # if fileBrowser.exec_():
        if fname:
            fileName = fname
            if mask == translate('RTOC', 'Excel-Tabelle (*.xlsx)'):
                self.logger.exportData(fileName, "xlsx")
            elif mask == translate('RTOC', 'CSV-Datei (*.csv)'):
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
        pyqtlib.info_message(translate('RTOC', "\xdcber"), "RealTime OpenControl 2.0.1", _(
            "RealTime OpenControl (RTOC) ist eine freie OpenSource Software unter der BSD-3-Lizenz.\n\nAlle Symbole werden unter der 'Creative Commons Attribution-NoDerivs 3.0 Unported' Lizenz bereitgestellt von icons8 (https://icons8.de)\n\nCopyright (C) 2018 Sebastian Keller"))

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
                pyqtlib.info_message(translate('RTOC', "Sprache ge\xe4ndert"),
                                     translate('RTOC', "Bitte Programm neustarten"), "")

    def checkUpdates(self):
        current, available = self.logger.check_for_updates()
        if current is not None:
            text = translate('RTOC', 'Installierte Version: {}').format(current)
            if not available:
                info = _(
                    "Entschuldigung. Konnte RTOC bei PyPi nicht finden. Schau mal bei 'https://pypi.org/project/RTOC/'")
            else:
                text += translate('RTOC', ', Neuste Version: {}').format(available[0])
                if current == available[0]:
                    info = translate('RTOC', 'RTOC ist auf dem neusten Stand.')
                else:
                    info = _(
                        'Neue Version verf\xfcgbar. Update mit der Konsole:\n\n"pip3 install RTOC --upgrade"\n')
        else:
            text = translate('RTOC', 'RTOC wurde nicht mit PyPi installiert.')
            info = translate('RTOC', 'Um die Version zu \xfcberpr\xfcfen, installiere RTOC mit "pip3 install RTOC"')

        pyqtlib.info_message(translate('RTOC', 'Version'), text, info)

    def clearCache(self):
        ok = pyqtlib.alert_message(translate('RTOC', 'Cache leeren'), translate('RTOC', 'Wollen Sie wirklich den Cache leeren?'), _(
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
        #dict = self.logger.getPluginDict()
        # for sig in dict.keys():
        #     if dict[sig]['status']:
        #         for element in dict[sig]['functions']:
        #             ls =
        #             self.pluginCallWidget.addItem(sig+"."+element+'('+ls+')')
        #         for element in dict[sig]['parameters']:
        #             self.pluginCallWidget.addItem(sig+"."+element[0])
        for name in self.logger.devicenames.keys():
            if self.logger.pluginStatus[name] is True:
                for fun in self.logger.pluginFunctions.keys():
                    hiddenFuncs = ["loadGUI", "updateT", "stream", "plot", "event", "createTCPClient", "sendTCP", "close", "cancel", "start", "setSamplerate","setDeviceName",'setPerpetualTimer','setInterval','getDir']

                    if fun.startswith(name+'.') and fun not in [name+'.'+i for i in hiddenFuncs]:
                        parStr = ', '.join(self.logger.pluginFunctions[fun][1])
                        funStr = fun+'('+parStr+')'
                        self.pluginCallWidget.addItem(funStr)
                for fun in self.logger.pluginParameters.keys():
                    hiddenParams = ["run", "smallGUI", 'widget', 'samplerate','lockPerpetialTimer']

                    if fun.startswith(name+'.') and fun not in [name+'.'+i for i in hiddenParams]:
                        self.pluginCallWidget.addItem(fun)

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
        print(devsplit)
        if len(devsplit) == 2:
            plugin = devsplit[0]
            function = devsplit[1]
            print(function)
            if '(' in function and function.endswith(')'):
                text, ok = pyqtlib.text_message(self, _(
                    'Ger\xe4te-Funktion ausf\xfchren'), strung, translate('RTOC', 'Funktionsparameter'))
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
                        pyqtlib.info_message(translate('RTOC', 'Fehler'), _(
                            'Funktionsparameter sind nicht g\xfcltig'), translate('RTOC', "Bitte geben Sie g\xfcltige Parameter an"))
            else:
                if host == 'local':
                    ans = self.logger.handleTcpPlugins({plugin: {'get': [function]}})
                    text, ok = pyqtlib.text_message(self, _(
                        'Ger\xe4te-Parameter \xe4ndern'), strung, str(ans[plugin]['get'][0]))
                    if ok:
                        self.par = []
                        try:
                            exec('self.par = '+text)
                            dict = {plugin: {function: self.par}}
                            self.logger.handleTcpPlugins(dict)
                        except Exception:
                            tb = traceback.format_exc()
                            logging.debug(tb)
                            pyqtlib.info_message(translate('RTOC', 'Fehler'), _(
                                'Wert ung\xfcltig'), translate('RTOC', "Bitte geben Sie einen g\xfcltigen Wert an"))
                else:
                    # logging.info('remoteparameter')
                    current_value = self.logger.remote.getParam(host, plugin, function)
                    if current_value is not None:
                        text, ok = pyqtlib.text_message(self, _(
                            'Ger\xe4te-Parameter \xe4ndern'), strung, str(current_value))
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
                                pyqtlib.info_message(translate('RTOC', 'Fehler'), _(
                                    'Wert ung\xfcltig'), translate('RTOC', "Bitte geben Sie einen g\xfcltigen Wert an"))
                    else:
                        logging.error('Failed to load parameter')

    def updateNetworkMenu(self):
        self.menuMit_Remotehost_verbinden.clear()
        self.menuAktive_Verbindungen.clear()
        newAction = self.menuMit_Remotehost_verbinden.addAction(translate('RTOC', 'Neuer Host'))
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
                self, 'Name angeben', 'Gib einen Namen f\xfcr diesen Host an\n(Darf weder "." noch ":" enthalten)', 'RemoteRTOC')
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
            self, 'Remote Updaterate \xe4ndern', '\xc4ndere die Updaterate, mit der Remote-Ger\xe4te abgefragt werden', '1')
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
        pyqtlib.info_message(translate('RTOC', "Fertig"), translate('RTOC', "RTOC-Suche abgeschlossen"),
                             translate('RTOC', "{} Server gefunden:\n{}").format(len(hostlist)-1, strung))

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
                text, ok2 = pyqtlib.text_message(None, translate('RTOC', 'Passwort'), _(
                    "Der RTOC-Server {} ist passwortgesch\xfctzt. Bitte Passwort eintragen.").format(hostname),  translate('RTOC', 'TCP-Passwort'))
                if ok2:
                    self.logger.remote.getConnection(host).tcppassword = text
                    self.logger.remote.connect(host, port, name, text)
                    retry = True
                    ok3 = pyqtlib.alert_message(translate('RTOC', 'Password speichern'), _(
                        'M\xf6chtest du das Passwort speichern?'), '')
                    if ok3:
                        self.logger.config['tcp']['knownHosts'][hostname][1] = text
            elif status is "connected":
                pyqtlib.info_message(translate('RTOC', 'Verbindung hergestellt'), _(
                    'Verbindung zu {} an Port {} hergestellt.').format(host, port), '')

                self.addRemoteHostWidget(host, name)
                return True
            elif status is "wrongPassword":
                text, ok = pyqtlib.text_message(None, translate('RTOC', 'Gesch\xfctzt'), translate('RTOC', 'Verbindung zu {} an Port {} wurde nicht hergestellt').format(host, port), translate('RTOC', 'Passwort ist falsch.'))
                if ok:
                    self.logger.remote.getConnection(host).tcppassword = text
                    self.logger.remote.connect(host, port, name, text)
                    retry = True
                    ok3 = pyqtlib.alert_message(translate('RTOC', 'Password speichern'), _(
                        'M\xf6chtest du das Passwort speichern?'), '')
                    if ok3:
                        self.logger.config['tcp']['knownHosts'][hostname][1] = text
            elif status is "error":
                ok = pyqtlib.alert_message(translate('RTOC', 'Verbindungsfehler'), translate('RTOC', 'Fehler. Verbindung zu {} an Port {} konnte nicht hergestellt werden.').format(host, port), translate('RTOC', 'Erneut versuchen?'))
                if ok:
                    self.logger.remote.connect(host, port, name, password)
                    retry = True
            elif status is "connecting...":
                retry = False
                return True
            else:
                print(status)
                pyqtlib.info_message('End of the universe',
                                     'You reached the end of the universe', "This shouldn't happen")
        return False
