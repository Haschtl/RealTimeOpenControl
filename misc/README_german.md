# RealTime OpenControl (RTOC)

### Version 1.8

[**This README is available in ENGLISH here.**](README.md)

[Dokumentation](https://github.com/Haschtl/RealTimeOpenControl/wiki/(GERMAN)-RealTime-OpenControl-(RTOC))

RealTime OpenControl ermöglicht die einfache Echtzeit-Datenaufzeichnung, -darstellung und Bearbeitung.  Die Aufzeichnung kann mit lokale Python-Skripten oder über TCP lokal oder aus dem Netzwerk erfolgen. Darstellung und Bearbeitung ist lokal, im Netzwerk (TCP und HTML) und über Telegram am Smartphone verfügbar.

Neben Datenaufzeichnung können auch Events/Ergeignisse aufgezeichnet werden. Diese können z.B. eine Telegram-Mitteilung auslösen.

Mögliche Einsatzbereiche:

- Zentrale Messdatenaufzeichnung von Laborgeräten mit PC-Anbindung (z.B. Netzteil, Multimeter, Sensoren, Microcontroller)
- Zentrale Messdatenaufzeichnung von Internetgeräten (z.B. mobilen Wetterstationen, Drohnen, Smartphones)
- Remote-Überwachung und Steuerung von Prozessen und Geräten mit PC und Smartphone (Telegram) (z.B. 3D-Druck, Heizung, Custom-SmartHome)
- Steuerung und Regelung zwischen mehreren Geräten (z.B.: Leistungsregelung eines Netzteils auf Temperatursensor eines Multimeters)
- Dezentrale Datenaufzeichnung (z.B auf Raspberry) und Zugriff über Netzwerkverbindung (Smarte Projekte)

![Übersicht](screenshots/overview.png)

## Getting Started

RTOC ist geschrieben in Python 3.  Getestet unter Windows und Linux.

Python 3 (und pip3) muss dazu auf dem Rechner installiert sein.

### Installing with Python3 (recommended)

RTOC ist verfügbar im Python-Paketmanager PIP:

```
pip3 install RTOC
```

Jetzt kann RTOC gestartet werden

```
// Für lokale RTOC-Instanz mit GUI
python3 -m RTOC
// Für lokale RTOC-Instanz ohne GUI (nur TCP-Server, [HTTP-Server, Telegram-Bot])
python3 -m RTOC -s
// Für remote RTOC-Instanz mit GUI
python3 -m RTOC -r <ADRESSE>
```

Nach dem ersten Start erzeugt RTOC ein Verzeichnis für Benutzerplugins, temporäre Nutzerdaten und Einstellungen.

```
user@rtoc-server:~$ ls Documents/RTOC
config.json  // Einstellungsdatei für RTOC
devices/ 	 // Verzeichnis für Nutzerplugins
plotStyles.json // Angepasste Plotstile werden gespeichert
```

### Installing with Builds (not tested well)

Lade die aktuellen Release-Builds für Windows (bald auch Linux) hier herunter.

Entpacke die .zip-Datei in ein Verzeichnis. RTOC wird mit Doppelklick auf "RTOC.exe" gestartet. Alternativ über die Kommandozeile

```
// Für lokale RTOC-Instanz mit GUI
./RTOC
// Für lokale RTOC-Instanz ohne GUI (nur TCP-Server, [HTTP-Server, Telegram-Bot])
./RTOC -s
// Für remote RTOC-Instanz mit GUI
./RTOC -r <ADRESSE>
```

Nach dem ersten Start erzeugt RTOC ein Verzeichnis für Benutzerplugins, temporäre Nutzerdaten und Einstellungen.

```
user@rtoc-server:~$ ls Documents/RTOC
config.json  // Einstellungsdatei für RTOC
devices/ 	 // Verzeichnis für Nutzerplugins
plotStyles.json // Angepasste Plotstile werden gespeichert
```

### Manuelle Installation

Um RTOC zu benutzen müssen folgende Abhängigkeiten vorhanden sein

```python
pip3 install numpy pyqt5 pyqtgraph markdown2 xslxwriter scipy qtmodern
```

Folgende Pakete sollten ebenfalls installiert werden

```
pip3 install python-telegram-bot matplotlib requests python-nmap bokeh pycryptdomex
```

Für das DPS5020-Plugin ist noch folgende Abhängigkeit zu installieren

```python
pip3 install minimalmodbus
```

Dann kann die RTOC-Repository geklont werden mit

```shell
git@github.com:Haschtl/RealTimeOpenControl.git
```

Nun kann RTOC gestartet werden:

```shell
cd RTOC
// Für lokale RTOC-Instanz mit GUI
python3 RTOC
// Für lokale RTOC-Instanz ohne GUI (nur TCP-Server, [HTTP-Server, Telegram-Bot])
python3 RTOC -s
// Für remote RTOC-Instanz mit GUI
python3 RTOC -r <ADRESSE>
```

Nach dem ersten Start erzeugt RTOC ein Verzeichnis für Benutzerplugins, temporäre Nutzerdaten und Einstellungen.

```
user@rtoc-server:~$ ls Documents/RTOC
config.json  // Einstellungsdatei für RTOC
devices/ 	 // Verzeichnis für Nutzerplugins
plotStyles.json // Angepasste Plotstile werden gespeichert
```



## First steps

![Beispielschematik](screenshots/RTOC-schematik.png)

### Wiki
[Lese die Dokumentation](https://github.com/Haschtl/RealTimeOpenControl/wiki/(GERMAN)-RealTime-OpenControl-(RTOC))

### Standart/Beispiel Plugins:

- Funktionsgenerator: Erzeugt Sinus, Square, Sawtooth, Random, AC, DC
- System: Zur Aufzeichnung vieler Systemvariablen (CPU, Memory, Network,...)
- Octoprint: Aufzeichnung für 3D-Drucker
- DPS5020: Netzgerät-Aufzeichnung und Steuerung (evtl. auch DPS5005, ...)
- HoldPeak VC820: Multimeter Messaufzeichnung (wahrsch. auch andere VC820)
- NetWoRTOC: Steuerung und Datenaustausch zwischen mehreren RTOC's im Netzwerk

### First GUI-Run

Die graphische Oberfläche von RTOC bietet eine Fülle an Funktionen zur Datendarstellung und Bearbeitung.

- Messwerkzeuge
- Plotstile anpassen und speichern
- Session speichern und laden
- Mehrere Plots erzeugen
- Im Hintergrund laufen
- Daten importieren und exportieren
- Skripte:
  - Multi-Tab Skript-Editor
  - Der Nutzer kann während der Laufzeit mit den Signalen und Plugins interagieren:
    - Pluginfunktionen ausführen oder Pluginparameter setzen
    - Signale bearbeiten, neue Signale erzeugen, zuschneiden, überlagern, ...
    - Skalieren, verschieben von Signalen
  - Mehrere Skripte parallel laufen lassen

[Vollständige Anleitung zur GUI hier.](https://github.com/Haschtl/RealTimeOpenControl/wiki/GUI)

### Write simple Python-Plugin

Python-Plugins werden in RTOC integriert und können

- Daten als Stream(=append) oder Plot(=replace) an RTOC senden
- Events senden

Aber **nicht** auf Messdaten zugreifen. Hierzu muss das Plugin per TCP auf RTOC zugreifen.

[Beispiel-Plugins hier.](https://github.com/Haschtl/RealTimeOpenControl/wiki/PlugIns)

### Einfacher lokaler TCP-Datensender

TCP-Clients können am selben Rechner oder im Netzwerk (Firewall-Einstellungen prüfen) eine Verbindung zum RTOC-Server herstellen. Mit den nötigen Port-Freigaben am Router und dynamischer DNS kann auf den RTOC-Server auch aus dem Internet zugegriffen werden.

Die TCP-Kommunikation findet mit JSONs statt. Dadurch lässt sich die Kommunikation in allen Programmiersprachen und auch z.B. mit einem ESP8266/ESP32-Microcontroller realisieren. Der Client kann

- Daten als Stream(=append) oder Plot(=replace) an RTOC senden
- Events senden
- Auf alle Messdaten und Events des RTOC-Servers zugreifen
- Auf RTOC-Server-Funktionen zugreifen
- Auf RTOC-Server-Pluginfunktionen und -parameter zugreifen

Die Verbindung zwischen RTOC-Server und Client kann mit einem Passwort Ende-zu-Ende verschlüsstelt werden (AES).

[Beispiele für TCP hier.]https://github.com/Haschtl/RealTimeOpenControl/wiki/clientCommunication)

### Telegram einbinden

[Anleitung zu Telegram hier.](https://github.com/Haschtl/RealTimeOpenControl/wiki/telegram)

## Screenshots

#### MultiWindow

![multiWindow](screenshots/multiWindow.png)

#### Crosshair-Tool

![multiWindow](screenshots/crosshair.png)

#### Cutting-Tool

![multiWindow](screenshots/cut.png)

#### Rechteck-Messtool

![multiWindow](screenshots/rect.png)

#### Plotstile anpassen

![multiWindow](screenshots/plotStyleEdit.png)

#### Plot-Tools-DropDown

![multiWindow](screenshots/plotTools.png)

#### Plot-Ansicht-Dropdown

![multiWindow](screenshots/plotView.png)

#### Signal

![multiWindow](screenshots/signalWidget.png)

#### Plot

![multiWindow](screenshots/plotWidget.png)

#### Scripte

![multiWindow](screenshots/scriptWidget.png)

## Built With

* [cx_freeze](https://anthony-tuininga.github.io/cx_Freeze/)

## Externe Bibliotheken und Skripte

- [Jsonsocket von mdebbar](https://github.com/mdebbar/jsonsocket)
- [Taurus PyQtGraph](https://github.com/taurus-org/taurus_pyqtgraph.git)
- [ImportCode Script von avtivestate.com](http://code.activestate.com/recipes/82234-importing-a-dynamically-generated-module/)
- [VC820Py von adnidor (für das HoldPeak_VC820 Plugin)](https://github.com/adnidor/vc820py)

Alle Icons, die in dieser Software (inklusive Plugins) benutzt werden, werden freundlicherweise zur Verfügung gestellt von [Icons8](

## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## License

This project is licensed under the  **GNU General Public License v3.0** - see the [LICENSE](LICENSE) file for details
