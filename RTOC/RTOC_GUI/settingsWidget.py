from PyQt5 import QtWidgets
from PyQt5.QtCore import QCoreApplication
from PyQt5 import QtCore
from PyQt5 import uic
import os
import sys
from functools import partial
try:
    import psycopg2
except Exception:
    psycopg2 = None

from ..lib import pyqt_customlib as pyqtlib
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

translate = QCoreApplication.translate


class SettingsWidget(QtWidgets.QWidget):
    refresh = QtCore.pyqtSignal()

    def __init__(self, config, defaultconfig, parent=None):
        super(SettingsWidget, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/RTOC_GUI'
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/ui/settingsWidget.ui", self)

        self.self = parent
        self.defaultconfig = defaultconfig
        self.config = config

        self.languageComboBox.currentIndexChanged.connect(self.setLang)
        self.signalDropDownComboBox.currentIndexChanged.connect(self.changeSignalDropDownStyle)
        self.refreshRateSpinBox.valueChanged.connect(self.changeRefreshrate)
        self.timeOutSpinBox.valueChanged.connect(self.changeTimeOut)
        self.telegramNameLineEdit.textChanged.connect(self.changeTelegramName)

        self.darkmodeCheckBox.stateChanged.connect(
            partial(self.toggle, self.darkmodeCheckBox, ['GUI', 'darkmode']))
        self.autoShowCheckBox.stateChanged.connect(
            partial(self.toggle, self.autoShowCheckBox, ['GUI', 'autoShowGraph']))
        self.antialiasingCheckBox.stateChanged.connect(
            partial(self.toggle, self.antialiasingCheckBox, ['GUI', 'antiAliasing']))
        self.openGLCheckBox.stateChanged.connect(
            partial(self.toggle, self.openGLCheckBox, ['GUI', 'openGL']))
        self.weaveCheckBox.stateChanged.connect(
            partial(self.toggle, self.weaveCheckBox, ['GUI', 'useWeave']))
        self.restoreWidgetPositionCheckBox.stateChanged.connect(
            partial(self.toggle, self.weaveCheckBox, ['GUI', 'restoreWidgetPosition']))

        self.clearSignalStylesButton.clicked.connect(self.clearSignalStyles)
        self.clearLastEditedListButton.clicked.connect(partial(self.clear, 'lastSessions'))
        self.clearTelegramClientListButton.clicked.connect(
            partial(self.clear, ['telegram', 'chat_ids']))
        self.clearTCPHostListButton.clicked.connect(partial(self.clear, ['tcp', 'knownHosts']))

        self.resetButton.clicked.connect(self.reset)
        self.abortButton.clicked.connect(self.abort)
        self.saveButton.clicked.connect(self.save)

        self.backupCheckbox.stateChanged.connect(self.toggleBackup)
        self.backupTimeEdit.dateTimeChanged.connect(self.setBackupIntervall)
        self.backupDirButton.clicked.connect(self.setBackupDir)
        self.backupIfFullCheckbox.stateChanged.connect(self.setBackupIfFullOption)
        self.backupClearCheckbox.stateChanged.connect(self.setBackupClearOption)
        self.backupAutoOnCloseCheckbox.stateChanged.connect(
            partial(self.toggle, self.postgresqlCheckbox, ['backup', 'autoOnClose']))
        self.backupLoadOnOpenCheckbox.stateChanged.connect(
            partial(self.toggle, self.postgresqlCheckbox, ['backup', 'loadOnOpen']))

        self.postgresqlCheckbox.stateChanged.connect(
            partial(self.toggle, self.postgresqlCheckbox, ['postgresql', 'active']))
        self.postgresqlUserLineEdit.textChanged.connect(
            partial(self.changeName, ['postgresql', 'user']))
        self.postgresqlPasswordLineEdit.textChanged.connect(
            partial(self.changeName, ['postgresql', 'password']))
        self.postgresqlHostLineEdit.textChanged.connect(
            partial(self.changeName, ['postgresql', 'host']))
        self.postgresqlNameLineEdit.textChanged.connect(
            partial(self.changeName, ['postgresql', 'database']))
        self.postgresqlPortSpinBox.valueChanged.connect(
            partial(self.changeValue, ['postgresql', 'port']))
        self.postgresqlCheckButton.clicked.connect(self.checkPostgreSQL)

        self.initView()

    def initView(self):
        if self.config['global']['language'] == 'en':
            idx = 0
        elif self.config['global']['language'] == 'de':
            idx = 1
        else:
            idx = 0
            self.config['global']['language'] = 'en'
        self.languageComboBox.setCurrentIndex(idx)

        if self.config['GUI']['newSignalSymbols']:
            idx = 0
        else:
            idx = 1
        self.signalDropDownComboBox.setCurrentIndex(idx)

        self.refreshRateSpinBox.setValue(self.config['GUI']['plotRate'])
        self.timeOutSpinBox.setValue(self.config['GUI']['signalInactivityTimeout'])
        self.telegramNameLineEdit.setText(self.config['global']['name'])

        self.darkmodeCheckBox.setChecked(self.config['GUI']['darkmode'])
        self.autoShowCheckBox.setChecked(self.config['GUI']['autoShowGraph'])
        self.antialiasingCheckBox.setChecked(self.config['GUI']['antiAliasing'])
        self.openGLCheckBox.setChecked(self.config['GUI']['openGL'])
        self.weaveCheckBox.setChecked(self.config['GUI']['useWeave'])
        self.restoreWidgetPositionCheckBox.setChecked(self.config['GUI']['restoreWidgetPosition'])

        self.backupDirButton.setText(self.config['backup']['path'])
        self.backupCheckbox.setChecked(self.config['backup']['active'])
        self.backupClearCheckbox.setChecked(self.config['backup']['clear'])
        self.backupIfFullCheckbox.setChecked(self.config['backup']['autoIfFull'])
        self.backupAutoOnCloseCheckbox.setChecked(self.config['backup']['autoOnClose'])
        self.backupLoadOnOpenCheckbox.setChecked(self.config['backup']['loadOnOpen'])
        self.postgresqlCheckbox.setChecked(self.config['postgresql']['active'])
        self.postgresqlUserLineEdit.setText(self.config['postgresql']['user'])
        self.postgresqlPasswordLineEdit.setText(self.config['postgresql']['password'])
        self.postgresqlHostLineEdit.setText(self.config['postgresql']['host'])
        self.postgresqlNameLineEdit.setText(self.config['postgresql']['database'])
        self.postgresqlPortSpinBox.setValue(int(self.config['postgresql']['port']))

        timestamp = self.config['backup']['intervall']
        day = timestamp//(24*60*60)
        hour = (timestamp-day*24*60*60)//(60*60)
        min = (timestamp-day*24*60*60-hour*60*60)//60
        datetime = QtCore.QDateTime()
        time = QtCore.QTime(hour, min, day)
        datetime.setTime(time)

    def checkPostgreSQL(self):
        if self.config['postgresql']['active']:
            if psycopg2 is not None:
                try:
                    connection = psycopg2.connect(
                        user=self.config['postgresql']['user'],
                        password=self.config['postgresql']['password'],
                        host=self.config['postgresql']['host'],
                        port=self.config['postgresql']['port'],
                        database=self.config['postgresql']['database'])
                    cursor = connection.cursor()
                    # Print PostgreSQL Connection properties
                    print(connection.get_dsn_parameters(), "\n")
                    # Print PostgreSQL version
                    query = "SELECT version();"
                    connection.commit()
                    cursor.execute(query)
                    cursor.fetchall()
                    # record = self.cursor.fetchone()
                    # logging.info("You are connected to - "+ str(record)+ "\n")
                    ok = True
                except (Exception, psycopg2.Error) as error:
                    logging.error("Error while connecting to PostgreSQL", error)
                    ok = False
                if ok:
                    title = translate('settings', 'Verbunden')
                    strung = translate('settings', 'PostgreSQL korrekt eingerichtet')
                else:
                    title = translate('settings', 'Fehler')
                    strung = translate(
                        'settings', 'Fehler in PostgreSQL-Konfiguration\nVielleicht ist PostgreSQL auf Ihrem Rechner nicht installiert bzw. die Datenbank existiert nicht oder die Logindaten/Port sind falsch.')
            else:
                title = translate('settings', 'Import-Fehler')
                strung = translate(
                    'settings', 'Pythonbibliothek psycopg2 ist nicht installiert.\nBitte installiere es mit "pip3 install psycopg2" und versichere, dass PostgreSQL korrekt eingerichtet ist.')
        else:
            title = translate('settings', 'PostgreSQL deaktiviert')
            strung = translate(
                'settings', 'PostgreSQL ist deaktiviert. Bitte schalte PostgreSQL an.')
        pyqtlib.info_message(title, strung, '')

    def setLang(self, value):
        if value == 1:
            lang = 'de'
        else:
            lang = 'en'
        self.config['global']['language'] = lang

    def changeSignalDropDownStyle(self, value):
        if value == 1:
            newStyle = False
        else:
            newStyle = True
        self.config['GUI']['newSignalSymbols'] = newStyle
        # newSignalSymbols=True,False

    def changeRefreshrate(self, value):
        self.config['GUI']['plotRate'] = value
        # plotRate = 8

    def changeTimeOut(self, value):
        self.config['GUI']['signalInactivityTimeout'] = value
        # plotRate = 8

    def changeTelegramName(self, value):
        self.config['global']['name'] = value
        # telegram_name

    def clearSignalStyles(self):
        self.self.clearCache()

    def clear(self, key):
        if type(key) == list:
            self.config[key[0]][key[1]] = {}
        else:
            self.config[key] = {}

    def toggle(self, button, key):
        value = button.isChecked()
        if type(key) == list:
            self.config[key[0]][key[1]] = value
        else:
            self.config[key] = value
        self.toggleButtonText(button, value)

    def changeName(self, key, value):
        if type(key) == list:
            self.config[key[0]][key[1]] = value
        else:
            self.config[key] = value

    def changeValue(self, key, value):
        if type(key) == list:
            self.config[key[0]][key[1]] = value
        else:
            self.config[key] = value

    def toggleBackup(self, value):
        self.backupDirButton.setEnabled(value)
        self.backupCheckbox.setEnabled(value)
        self.backupClearCheckbox.setEnabled(value)
        self.backupIfFullCheckbox.setEnabled(value)
        self.config['backup']['active'] = value

    def setBackupDir(self):
        dir_path = self.config['backup']['path']
        fileBrowser = QtWidgets.QFileDialog(self)
        fileBrowser.setDirectory(dir_path)
        fileBrowser.setNameFilters(
            ["JSON-Datei (*.json)"])
        fileBrowser.selectNameFilter("")

        # fname, mask = fileBrowser.getSaveFileName(
        #    self, self.tr("Backup-Verzeichnis festlegen"), dir_path, "JSON-Datei (*.json)")
        fname, mask = fileBrowser.getExistingDirectory(
            self, self.tr("Backup-Verzeichnis festlegen"), dir_path)

        # if self.dir_name:
        #     self.btn_file.setText(self.dir_name)
        if fname:
            self.config['backup']['path'] = fname
            self.self.logger.setBackupIntervall(self.config['backup']['intervall'])
            self.backupDirButton.setText(fname)

    def setBackupIntervall(self, qdatetime):
        # date = qdatetime.date()
        time = qdatetime.time()
        days = time.second()
        hours = time.hour()
        minutes = time.minute()

        intervall = days*24*60*60+hours*60*60+minutes*60
        # intervall = 0
        # items = [self.tr('Aus'), self.tr('stündlich'), self.tr('täglich'), self.tr(
        #     '2x täglich'), self.tr('wöchentlich'), self.tr('Monatlich')]
        # item, ok = pyqtlib.item_message(self, self.tr('Backup Intervall setzen'), self.tr(
        #     'Wähle den Zeitabstände zwischen den Backups'), items)
        # if ok:
        #     if item == self.tr('stündlich'):
        #         intervall = 60*60
        #     elif item == self.tr('täglich'):
        #         intervall = 60*60*24
        #     elif item == self.tr('2x täglich'):
        #         intervall = 60*60*12
        #     elif item == self.tr('wöchentlich'):
        #         intervall = 60*60*24*7
        #     elif item == self.tr('Monatlich'):
        #         intervall = 60*60*24*30.5
        #
        #     if intervall == 0:
        #         self.actionSetBackupIntervall.setText(self.tr('Backup deaktiviert'))
        #     else:
        #         self.actionSetBackupIntervall.setText(self.tr('Intervall: ')+item)

        self.self.logger.database.setBackupIntervall(intervall)

    def setBackupIfFullOption(self, value):
        self.config['backup']['autoIfFull'] = value

    def setBackupClearOption(self, value):
        self.config['backup']['clear'] = value

    def toggleButtonText(self, button, value):
        if value:
            button.setText(translate('settings', 'An'))
        else:
            button.setText(translate('settings', 'Aus'))

    def abort(self):
        self.close()

    def save(self):
        ok = pyqtlib.alert_message(translate('settings', 'Speichern'), translate('settings', 'Wollen Sie die Einstellungen wirklich überschreiben?'), translate(
            'settings', 'Danach sollte RTOC neu gestartet werden.'), "", translate('settings', 'Speichern'), translate('settings', 'Abbrechen'))
        if ok:
            self.self.config = self.config
            self.close()

    def reset(self):
        self.config = self.defaultconfig
        self.initView()
