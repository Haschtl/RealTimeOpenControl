import os
import csv
from PyQt5 import QtWidgets
from functools import partial

from .lib import pyqt_customlib as pyqtlib
from .lib import general_lib as lib
try:
    from ..PluginDownloader import PluginDownloader
except (ImportError, ValueError):
    from PluginDownloader import PluginDownloader


class Actions:
    def connectButtons(self):
        self.maxLengthSpinBox.editingFinished.connect(self.resizeLogger)
        self.clearButton.clicked.connect(self.clearDataAction)
        self.createGraphButton.clicked.connect(self.newPlotWidget)

        # Menubar
        self.loadSessionAction.triggered.connect(self.loadSessionTriggered)
        self.saveSessionAction.triggered.connect(self.saveSessionTriggered)
        self.importDataAction.triggered.connect(self.importDataTriggered)
        self.exportDataAction.triggered.connect(self.exportDataTriggered)
        self.actionTCPServer_2.triggered.connect(self.toggleTcpServer)
        self.HTMLServerAction_2.triggered.connect(self.toggleHtmlServer)
        self.actionTelegramBot_2.triggered.connect(self.toggleTelegramBot)
        self.actionBotToken_2.triggered.connect(self.setBotToken)
        self.actionTCPPassword_2.triggered.connect(self.setTCPPassword)
        self.actionTCPPort_2.triggered.connect(self.setTCPPort)

        self.getPluginsButton.triggered.connect(self.openPluginDownloader)

        self.systemTrayAction.triggered.connect(self.toggleSystemTray)

        self.menuFenster.aboutToShow.connect(self.updateWidgetCheckboxes)
        self.deviceWidgetToggle.triggered.connect(self.toggleDeviceWidget)
        self.pluginsWidgetToggle.triggered.connect(self.togglePluginsWidget)
        self.scriptWidgetToggle.triggered.connect(self.toggleScriptWidget)
        self.eventWidgetToggle.triggered.connect(self.toggleEventWidget)

        self.actionDeutsch.triggered.connect(
            partial(self.toggleLanguage, "de", self.actionDeutsch, [self.actionEnglish], False))
        self.actionEnglish.triggered.connect(
            partial(self.toggleLanguage, "en", self.actionEnglish, [self.actionDeutsch], False))
        if self.config['language'] == 'de':
            self.toggleLanguage("de", self.actionDeutsch, [self.actionEnglish], True)
        else:
            self.toggleLanguage("en", self.actionEnglish, [self.actionDeutsch], True)

        self.helpAction.triggered.connect(self.showHelpWebsite)
        self.aboutAction.triggered.connect(self.showAboutMessage)
        self.checkUpdatesAction.triggered.connect(self.checkUpdates)
        self.pluginRepoAction.triggered.connect(self.showRepoWebsite)

        self.clearCacheAction.triggered.connect(self.clearCache)

        self.searchEdit.textChanged.connect(self.filterDevices)

    def toggleTcpServer(self):
        if self.config["tcpserver"]:
            self.config["tcpserver"] = False
        else:
            self.config["tcpserver"] = True
        self.logger.toggleTcpServer(self.config["tcpserver"])
        self.actionTCPServer_2.setChecked(self.config["tcpserver"])

    def toggleHtmlServer(self):
        if self.config["rtoc_web"]:
            self.config["rtoc_web"] = False
        else:
            self.config["rtoc_web"] = True
            pyqtlib.info_message(self.tr("RTOC - Web gestartet"), self.tr("RTOC - Web ist jetzt unter localhost:5006 erreichbar"), self.tr("Diese Seite kann im gesamten Netzwerk geöffnet werden"))
        self.logger.toggleHTMLPage(self.config["rtoc_web"])
        self.HTMLServerAction_2.setChecked(self.config["rtoc_web"])

    def toggleTelegramBot(self):
        if self.config["telegram_bot"]:
            self.config["telegram_bot"] = False
        else:
            self.config["telegram_bot"] = True
        self.logger.toggleTelegramBot(self.config["telegram_bot"])
        self.actionTelegramBot_2.setChecked(self.config["telegram_bot"])

    def setBotToken(self):
        ans, ok = pyqtlib.text_message(
            self, self.tr("Bot Token eingeben"), self.tr('Bitte erzeugen sie in Telegram mit "Botfather" einen Bot,\n generiere einen Bot und füge dessen Token hier ein'), self.config['telegram_token'])
        if ok:
            self.logger.telegramBot.setToken(ans)
            self.actionBotToken_2.setText(self.config['telegram_token'])

    def setTCPPassword(self):
        ans, ok = pyqtlib.text_message(
            self, self.tr("TCP Passwort eingeben"), self.tr('Schütze deine Übertragung vor unerwünschten Gästen\nLeer lassen, um Passwort zu deaktivieren'), self.config['tcppassword'])
        if ok:
            self.logger.setTCPPassword(ans)
            if ans=='':
                self.actionTCPPassword_2.setText(self.tr('Passwort-Schutz: Aus'))
            else:
                self.actionTCPPassword_2.setText(self.tr('Passwort-Schutz: An'))

    def setTCPPort(self):
        ans, ok = pyqtlib.text_message(
            self, self.tr("TCP Passwort eingeben"), self.tr('Schütze deine Übertragung vor unerwünschten Gästen\nLeer lassen, um Passwort zu deaktivieren'), self.config['tcppassword'])
        if ok:
            try:
                ans = int(ans)
                if ans >= 0 and ans <= 65535:
                    self.logger.setTCPPort(ans)
                    self.actionTCPPort_2.setText(self.tr('Port: ')+str(ans))
                else:
                    pyqtlib.info_message(self.tr('Fehler'), self.tr('Bitte gib eine Zahl zwischen 0 und 65535 an'), '')
            except:
                pyqtlib.info_message(self.tr('Fehler'), self.tr('Bitte gib eine Zahl zwischen 0 und 65535 an'), self.tr('Ihre Eingabe war ungültig.'))

    def toggleSystemTray(self):
        if self.config["systemTray"]:
            self.config["systemTray"] = False
        else:
            self.config["systemTray"] = True
        self.systemTrayAction.setChecked(self.config["systemTray"])

    def systemTrayClickAction(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Context:
            self.tcp_action.setChecked(self.config['tcpserver'])
            self.hide_action.setChecked(self.config['systemTray'])
        elif reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self.tray_icon.hide()
            self.show()

    def resizeLogger(self):
        newLength = self.maxLengthSpinBox.value()
        self.logger.resizeSignals(newLength)

    def clearDataAction(self):
        #print("deleting plot")
        if pyqtlib.alert_message(self.tr("Warnung"), self.tr("Wollen Sie wirklich alle Daten löschen?"), self.tr("(Unwiederrufbar)")):
            self.clearData()
            self.logger.clear()

    def loadSessionTriggered(self):
        dir_path = self.config['documentfolder']
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
        dir_path = self.config['documentfolder']
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
                s = self.scriptWidget.getSession()
                self.logger.exportData(fileName, "json", scripts=s)

    def importData(self, filename):
        ff = open(filename, 'r')
        mytext = ff.read()
#            print(mytext)
        ff.close()

        with open(filename, 'r') as f:
            if mytext.count(';') <= mytext.count('\t'):
                reader = csv.reader(f, delimiter = '\t')
            else:
                reader = csv.reader(f, delimiter = ';')
            reader = [list(r) for r in reader]
            reader2 = []
            print(len(reader))
            for idx, r in enumerate(reader[0]):
                reader2.append(lib.column(reader,idx))
            reader = reader2
            print(len(reader))
            for idx, row in enumerate(reader):
                if idx<len(reader)-2 and idx % 2 == 0:
                    if len(reader[idx])==len(reader[idx+1]):
                        x=[]
                        y=[]
                        for idx2, data in enumerate(reader[idx]):
                            xdat = self.str2float(reader[idx][idx2])
                            ydat = self.str2float(reader[idx+1][idx2])
                            if xdat != None and ydat != None:
                                x.append(xdat)
                                y.append(ydat)

                        self.logger.plot(x, y, "data"+str(int(idx/2)), filename.split(".")[0].split("/")[-1], "")
                    else:
                        y=[]
                        for idx2, data in enumerate(reader[idx]):
                            y.append(self.str2float(reader[idx][idx2]))

                        #self.logger.plot(y=y, sname="data"+str(int(idx/2)), dname=filename.split(".")[0].split("/")[-1], unit="")
                # elif idx==len(reader)-1:
                #     y=[]
                #     for idx2, data in enumerate(reader[idx]):
                #         y.append(self.str2float(reader[idx][idx2]))
                #     self.logger.plot(y=y, sname="data"+str(int(idx/2)), dname=filename.split(".")[0].split("/")[-1], unit="")

        # if len(data) % 2 == 0:
        #     for idx, values in enumerate(data):
        #         if idx % 2 == 0:
        #             if len(values) == len(data[idx+1]):
        #                 self.logger.plot([float(i) for i in values], [float(
        #                     i) for i in data[idx+1]], "data"+str(int(idx/2)), filename.split(".")[0].split("/")[-1], "")

    def str2float(self, strung):
        #print(strung)
        strung = str(strung)
        strung = strung.replace(',','.')
        if strung == '':
            return None
        return float(strung)

    def exportDataTriggered(self):
        dir_path = self.config['documentfolder']
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

    def toggleDeviceWidget(self):
        if self.deviceWidgetToggle.isChecked():
            self.deviceWidget.show()
            self.config["deviceWidget"] = True
        else:
            self.deviceWidget.hide()
            self.config["deviceWidget"] = False

    def toggleEventWidget(self):
        if self.eventWidgetToggle.isChecked():
            self.eventWidgets.show()
            self.config["eventWidget"] = True
        else:
            self.eventWidgets.hide()
            self.config["eventWidget"] = False

    def togglePluginsWidget(self):
        if self.pluginsWidgetToggle.isChecked():
            self.pluginsWidget.show()
            self.config["pluginsWidget"] = True
        else:
            self.pluginsWidget.hide()
            self.config["pluginsWidget"] = False

    def toggleScriptWidget(self):
        if self.scriptWidgetToggle.isChecked():
            self.scriptDockWidget.show()
            self.config["scriptWidget"] = True
        else:
            self.scriptDockWidget.hide()
            self.config["scriptWidget"] = False

    def importDataTriggered(self):
        dir_path = self.config['documentfolder']
        fileBrowser = QtWidgets.QFileDialog(self)
        fileBrowser.setDirectory(dir_path)
        fileBrowser.setNameFilters(["CSV (*.csv)"])
        fileBrowser.selectNameFilter("")
        fname, mask = fileBrowser.getOpenFileName(
            self, "Export", dir_path, "CSV (*.csv)")
        if fname:
            fileName = fname
            if mask == "CSV (*.csv)":
                self.importData(fileName)

    def showAboutMessage(self):
        pyqtlib.info_message(self.tr("Über"), "RealTime OpenControl 1.8", self.tr(
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

    def toggleLanguage(self, newlang, button, otherbuttons, force=False):
        button.setChecked(True)
        if newlang != self.config["language"] or force == True:
            for b in otherbuttons:
                b.setChecked(False)
            self.config["language"] = newlang
            if force == False:
                pyqtlib.info_message(self.tr("Sprache geändert"),
                                     self.tr("Bitte Programm neustarten"), "")

    def checkUpdates(self):
        current, available = self.logger.check_for_updates()
        if current != None:
            text =self.tr( 'Installierte Version: ')+str(current)
            if not available:
                info = self.tr("Entschuldigung. Konnte RTOC bei PyPi nicht finden. Schau mal bei 'https://pypi.org/project/RTOC/'")
            else:
                text += self.tr(', Neuste Version: ')+str(available[0])
                if current == available[0]:
                    info = self.tr('RTOC ist auf dem neusten Stand.')
                else:
                    info = self.tr('Neue Version verfügbar. Update mit der Konsole:\n\n"pip3 install RTOC --upgrade"\n')
        else:
            text = self.tr('RTOC wurde nicht mit PyPi installiert.')
            info = self.tr('Um die Version zu überprüfen, installiere RTOC mit "pip3 install RTOC"')

        pyqtlib.info_message(self.tr('Version'), text, info)

    def clearCache(self):
        ok = pyqtlib.alert_message(self.tr('Cache leeren'), self.tr('Wollen Sie wirklich den Cache leeren?'), self.tr('Dadurch gehen gespeicherte Ploteinstellungen sowie Einstellungen verloren.'))
        if ok:
            self.plotStyles = {}
            self.logger.clearCache()

    def openPluginDownloader(self):
        self.pluginDownloader = PluginDownloader(self.config['documentfolder'])
        self.pluginDownloader.show()
