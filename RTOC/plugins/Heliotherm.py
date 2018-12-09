try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from ..LoggerPlugin import LoggerPlugin
import time
from threading import Thread
import traceback
import requests
from PyQt5 import uic
from PyQt5 import QtWidgets
import socket
import threading
import os

devicename = "Heliotherm"

HOST = "192.168.178.72"

from pymodbus3.client.sync import ModbusTcpClient
from pyModbusTCP.client import ModbusClient


############################# DO NOT EDIT FROM HERE ################################################

mappingWrite = [
[100, 'Betriebsart', 1, ''],
[101, 'HKR Soll_Raum', 10, '°C'],
[102, 'HKR Soll', 10, '°C'],
[103, 'HKR Soll aktiv', 1, ''],
[104, 'RLT min Kuehlen', 10, '°C'],
[105, 'WW Normaltemperatur', 10, '°C'],
[106, 'WW Minimaltemperatur', 10, '°C'],
[107, 'MKR1 Betriebsart', 1, ''],
[108, 'MKR1 Soll_Raum', 10, '°C'],
[109, 'MKR1 Soll', 10, '°C'],
[110, 'MKR1 Soll aktiv', 1, ''],
[111, 'MKR1 Kuehlen RLT min.', 10, '°C'],
[112, 'MKR2 Betriebsart', 1, ''],
[113, 'MKR2 Soll_Raum', 10, '°C'],
[114, 'MKR2 Soll', 10, '°C'],
[115, 'MKR2 Soll aktiv', 1, ''],
[116, 'MKR2 Kuehlen RLT min.', 10, '°C'],
[117, 'PV Anf', 1, ''],
[118, 'Unbekannt', 1, ''],
[119, 'Unbekannt', 1, ''],
[120, 'Unbekannt', 1, ''],
[121, 'Unbekannt', 1, ''],
[122, 'Unbekannt', 1, ''],
[123, 'Unbekannt', 1, ''],
[124, 'Unbekannt', 1, ''],
[125, 'Leistungsaufnahmevorgabe', 1, 'W'],
[126, 'Verdichterdrehzahlvorgabe', 1, '%°'],
[127, 'Ext. Anf', 1, ''],
[128, 'Entstoeren', 1, ''],
[129, 'Aussentemperatur Wert', 10, '°C'],
[130, 'Aussentemperatur aktiv', 1, ''],
[131, 'Puffertemperatur Wert', 10, '°C'],
[132, 'Puffertemperatur aktiv', 1, ''],
[133, 'Brauchwassertemperatur Wert', 10, '°C'],
[134, 'Brauchwassertemperatur aktiv', 1, ''],
[135, 'Unbekannt', 10, '°C'],
[136, 'Unbekannt', 10, '°C'],
[137, 'Unbekannt', 10, '°C'],
[138, 'Unbekannt', 10, '°C'],
[139, 'Unbekannt', 10, '°C'],
[140, 'Unbekannt', 10, '°C'],
[141, 'Unbekannt', 10, '°C'],
[142, 'Unbekannt', 10, '°C'],
[143, 'Unbekannt', 10, '°C'],
[144, 'Unbekannt', 10, '°C'],
[145, 'Unbekannt', 10, '°C'],
[146, 'Unbekannt', 10, '°C'],
]

mappingRead = [
[10, 'Temperatur Aussen', 10, '°C'],
[11, 'Temperatur Brauchwasser', 10, '°C'],
[12, 'Temperatur Vorlauf', 10, '°C'],
[13, 'Temperatur Ruecklauf', 10, '°C'],
[14, 'Temperatur Pufferspeicher', 10, '°C'],
[15, 'Temperatur EQ_Eintritt', 10, '°C'],
[16, 'Temperatur EQ_Austritt', 10, '°C'],
[17, 'Temperatur Sauggas', 10, '°C'],
[18, 'Temperatur Verdampfung', 10, '°C'],
[19, 'Temperatur Kondensation', 10, '°C'],
[20, 'Temperatur Heissgas', 10, '°C'],
[21, 'Niederdruck', 10, 'Bar'],
[22, 'Hochdruck', 10, 'Bar'],
[23, 'Heizkreispumpe', 1, ''],
[24, 'Pufferladepumpe', 1, ''],
[25, 'Verdichter', 1, ''],
[26, 'Stoerung', 1, ''],
[27, 'Vierwegeventil Luft', 1, ''],
[28, 'WMZ_Durchfluss', 10, 'l/min'],
[29, 'n-Soll Verdichter', 1, '%°'],
[30, 'COP', 10, ''],
[31, 'Temperatur Frischwasser', 10, '°C'],
[32, 'EVU Sperre', 1, ''],
[33, 'Aussentemperatur verzoegert', 10, '°C'],
[34, 'HKR verzoegert', 10, '°C'],
[35, 'MKR1_Solltemperatur', 10, '°C'],
[36, 'MKR2_Solltemperatur', 10, '°C'],
[37, 'EQ-Ventilator', 1, ''],
[38, 'WW-Vorrat', 1, ''],
[39, 'Kühlen UMV passiv', 1, ''],
[40, 'Expansionsventil', 1, '%°'],
[41, 'Verdichteranforderung', 1, ''],
[42, 'Betriebsstunden im WW-Betrieb', 1, 'h'],
[43, 'Unbekannt', 1, ''],
[44, 'Betriebsstunden im HZG-Betrieb', 1, 'h'],
[45, 'Unbekannt', 1, ''],
[46, 'Unbekannt', 1, ''],
[47, 'Unbekannt', 1, ''],
[48, 'Unbekannt', 1, ''],
[49, 'Unbekannt', 1, ''],
[50, 'Unbekannt', 1, ''],
[51, 'Unbekannt', 1, ''],
[52, 'Unbekannt', 1, ''],
[53, 'Unbekannt', 1, ''],
[54, 'Unbekannt', 1, ''],
[55, 'Unbekannt', 1, ''],
[56, 'Unbekannt', 1, ''],
[57, 'Unbekannt', 1, ''],
[58, 'Unbekannt', 1, ''],
[59, 'Unbekannt', 1, ''],
[60, 'WMZ_Heizung', 1, 'kW/h'],
[61, 'Unbekannt', 1, ''],
[62, 'Stromz_Heizung', 1, 'kW/h'],
[63, 'Unbekannt', 1, ''],
[64, 'WMZ_Brauchwasser', 1, 'kW/h'],
[65, 'Unbekannt', 1, ''],
[66, 'Stromz_Brauchwasser', 1, 'kW/h'],
[67, 'Unbekannt', 1, ''],
[68, 'Stromz_Gesamt', 1, 'kW/h'],
[69, 'Unbekannt', 1, ''],
[70, 'Stromz_Leistung', 1, 'W'],
[71, 'Unbekannt', 1, ''],
[72, 'WMZ_Gesamt', 1, 'kW/h'],
[73, 'Unbekannt', 1, ''],
[74, 'WMZ_Leistung', 1, 'kW'],
[75, 'Unbekannt', 1, ''],

]

class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        # Plugin setup
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)
        self.smallGUI = True

        # Data-logger thread
        self.run = False  # False -> stops thread
        self.__updater = Thread(target=self.updateT)    # Actualize data
        # self.updater.start()

        self.__base_address = ""
        self.samplerate = 0.2
        self.temp_des = 0
        self.__s = requests.Session()

    # THIS IS YOUR THREAD
    def updateT(self):
        diff = 0
        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            y, name, units = self.helio_get()
            if y is not None:
                self.stream(y, name, 'Heliotherm', units)

            diff = (time.time() - start_time)

    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir = self.getDir(__file__)
        uic.loadUi(packagedir+"/Deneb/deneb.ui", self.widget)
        # self.setCallbacks()
        self.widget.pushButton.clicked.connect(self.__openConnectionCallback)
        self.widget.samplerateSpinBox.valueChanged.connect(self.__changeSamplerate)
        self.widget.comboBox.setCurrentText(HOST)
        self.__openConnectionCallback()
        return self.widget

    def __openConnectionCallback(self):
        if self.run:
            self.run = False
            self.widget.pushButton.setText("Verbinden")
            self.__base_address = ""
        else:
            address = self.widget.comboBox.currentText()
            self.__base_address = address
            self.c = ModbusClient(host=self.__base_address, port=502, auto_open=True, auto_close=True)
            self.c.timeout(10)
            #self.helio_get()
            self.run = True
            self.__updater = Thread(target=self.updateT)
            self.__updater.start()
            self.widget.pushButton.setText("Beenden")

    def start(self, address):
        if self.run:
            self.run = False
            self.__base_address = ""
        else:
            self.__base_address = address
            self.c = ModbusClient(host=self.__base_address, port=502, auto_open=True, auto_close=True)
            self.c.timeout(10)
            #self.helio_get()
            self.run = True
            self.__updater = Thread(target=self.updateT)
            self.__updater.start()

    def helio_get(self):
        #client = ModbusTcpClient(self.__base_address)
        #client.write_coil(1, True)
        #result = client.read_coils(0,1)
        resultWrite = self.c.read_holding_registers(100, 47)
        resultRead = self.c.read_input_registers(10,65)
        for idx, d in enumerate(resultRead):
            if d>=2 **16/2:
                resultRead[idx] = 2 **16 - d
        for idx, d in enumerate(resultWrite):
            if d>=2 **16/2:
                resultWrite[idx] = 2 **16 - d
        if resultWrite is not None and resultRead is not None:
            y = []
            units = []
            snames = []
            for idx, value in enumerate(resultWrite):
                if mappingWrite[idx][1]=='Unbekannt':
                    #mappingWrite[idx][1] = str(mappingWrite[idx][0])
                    pass
                else:
                    snames.append(mappingWrite[idx][1])
                    y.append(resultWrite[idx]/mappingWrite[idx][2])
                    units.append(mappingWrite[idx][3])
            for idx, value in enumerate(resultRead):
                if mappingRead[idx][1]=='Unbekannt':
                    #mappingRead[idx][1] = str(mappingRead[idx][0])
                    pass
                else:
                    snames.append(mappingRead[idx][1])
                    y.append(resultRead[idx]/mappingRead[idx][2])
                    units.append(mappingRead[idx][3])
            return y, snames, units
        else:
            self.widget.pushButton.setText("Fehler")
            return None, None, None

    def __changeSamplerate(self):
        self.samplerate = self.widget.samplerateSpinBox.value()


if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
