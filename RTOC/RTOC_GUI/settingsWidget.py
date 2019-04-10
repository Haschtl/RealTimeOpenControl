from PyQt5 import QtWidgets
from PyQt5.QtCore import QCoreApplication
from PyQt5 import QtCore
from PyQt5 import uic
import os
import sys
from functools import partial

from ..lib import pyqt_customlib as pyqtlib

translate = QCoreApplication.translate


class SettingsWidget(QtWidgets.QWidget):
    refresh = QtCore.pyqtSignal()

    def __init__(self, config, defaultconfig, parent=None):
        super(SettingsWidget, self).__init__()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)+'/RTOC/data'
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
        self.telegramNameLineEdit.textChanged.connect(self.changeTelegramName)

        self.darkmodeCheckBox.stateChanged.connect(
            partial(self.toggle, self.darkmodeCheckBox, 'darkmode'))
        self.autoShowCheckBox.stateChanged.connect(
            partial(self.toggle, self.autoShowCheckBox, 'autoShowGraph'))
        self.antialiasingCheckBox.stateChanged.connect(
            partial(self.toggle, self.antialiasingCheckBox, 'antiAliasing'))
        self.openGLCheckBox.stateChanged.connect(
            partial(self.toggle, self.openGLCheckBox, 'openGL'))
        self.weaveCheckBox.stateChanged.connect(
            partial(self.toggle, self.weaveCheckBox, 'useWeave'))
        self.restoreWidgetPositionCheckBox.stateChanged.connect(
            partial(self.toggle, self.weaveCheckBox, 'restoreWidgetPosition'))

        self.clearSignalStylesButton.clicked.connect(self.clearSignalStyles)
        self.clearLastEditedListButton.clicked.connect(partial(self.clear, 'lastSessions'))
        self.clearTelegramClientListButton.clicked.connect(partial(self.clear, 'telegram_chat_ids'))
        self.clearTCPHostListButton.clicked.connect(partial(self.clear, 'knownHosts'))

        self.resetButton.clicked.connect(self.reset)
        self.abortButton.clicked.connect(self.abort)
        self.saveButton.clicked.connect(self.save)

        self.initView()

    def initView(self):
        if self.config['language'] == 'en':
            idx = 0
        elif self.config['language'] == 'de':
            idx = 1
        else:
            idx = 0
            self.config['language'] = 'en'
        self.languageComboBox.setCurrentIndex(idx)

        if self.config['newSignalSymbols']:
            idx = 0
        else:
            idx = 1
        self.signalDropDownComboBox.setCurrentIndex(idx)

        self.refreshRateSpinBox.setValue(self.config['plotRate'])
        self.telegramNameLineEdit.setText(self.config['telegram_name'])

        self.darkmodeCheckBox.setChecked(self.config['darkmode'])
        self.autoShowCheckBox.setChecked(self.config['autoShowGraph'])
        self.antialiasingCheckBox.setChecked(self.config['antiAliasing'])
        self.openGLCheckBox.setChecked(self.config['openGL'])
        self.weaveCheckBox.setChecked(self.config['useWeave'])
        self.restoreWidgetPositionCheckBox.setChecked(self.config['restoreWidgetPosition'])

    def setLang(self, value):
        if value == 1:
            lang = 'de'
        else:
            lang = 'en'
        self.config['language'] = lang

    def changeSignalDropDownStyle(self, value):
        if value == 1:
            newStyle = False
        else:
            newStyle = True
        self.config['newSignalSymbols'] = newStyle
        # newSignalSymbols=True,False

    def changeRefreshrate(self, value):
        self.config['plotRate'] = value
        # plotRate = 8

    def changeTelegramName(self, value):
        self.config['telegram_name'] = value
        # telegram_name

    def clearSignalStyles(self):
        self.self.clearCache()

    def clear(self, key):
        self.config[key] = []

    def toggle(self, button, key):
        value = button.isChecked()
        self.config[key] = value
        self.toggleButtonText(button, value)

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
