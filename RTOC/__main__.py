import sys
import os
from PyQt5 import QtCore
from PyQt5 import QtWidgets
import json
import getopt
import traceback
import time

try:
    from .RTOC import RTOC, RTOC_TCP
    from .RTLogger import RTLogger
except:
    from RTOC import RTOC, RTOC_TCP
    from RTLogger import RTLogger


def main():
    opts, args = getopt.getopt(sys.argv[1:], "hsp:r:", ["remote=","port="])
    if len(opts) == 0:
        startRTOC()
    else:
        for opt, arg in opts:
            if opt == '-p':
                port = int(arg)
                break
            else:
                port = 5050
        for opt, arg in opts:
            if opt == '-h':
                print(
                    'RTOC.py [-h, -s] [-r <Remoteadress>]\n -h: Hilfe\n-s: TCP-Server ohne GUI\n-r <Remoteadresse>: TCP-Client zu RTOC-Server\n-p: Starte TCP-Server auf anderem Port (Standart: 5050)')
                sys.exit()
            elif opt == '-s':
                logger = RTLogger(True, port)
                #runInBackground()
                while logger.run:
                    time.sleep(1)
                sys.exit(0)
            elif opt in ("-r", "--remote"):
                remotepath = arg
                startRemoteRTOC(remotepath)
                sys.exit(0)
        startRTOC(None, port)

def setStyleSheet(app, myapp):
    if os.name == 'posix':
        type = 'QDarkStyle'
    else:
        type = 'QtModern'

    if type == 'QtModern':
        try:
            import qtmodern.styles
            import qtmodern.windows
            packagedir = os.path.dirname(os.path.realpath(__file__))
            with open(packagedir+"/data/ui/qtmodern.qss", 'r') as myfile:
                stylesheet = myfile.read().replace('\n', '')
            app.setStyleSheet(stylesheet)
            qtmodern.styles.dark(app)
            #mw = qtmodern.windows.ModernWindow(myapp)

            mw = myapp
            return app, mw
        except ImportError:
            tb = traceback.format_exc()
            print(tb)
            print("QtModern not installed")
            type = 'QDarkStyle'
    if type == 'QDarkStyle':
        try:
            import qdarkstyle
            dark_stylesheet = qdarkstyle.load_stylesheet_pyqt5()
            app.setStyleSheet(dark_stylesheet)
            return app, myapp
        except ImportError:
            tb = traceback.format_exc()
            print(tb)
            print("QtModern not installed")
            type == 'qdarkgraystyle'
    if type == 'qdarkgraystyle':
        try:
            import qdarkgraystyle
            dark_stylesheet = qdarkgraystyle.load_stylesheet()
            app.setStyleSheet(dark_stylesheet)
            return app, myapp
        except ImportError:
            tb = traceback.format_exc()
            print(tb)
            print("QtModern not installed")
    packagedir = os.path.dirname(os.path.realpath(__file__))
    with open(packagedir+"/data/ui/darkmode.html", 'r') as myfile:
        stylesheet = myfile.read().replace('\n', '')
    app.setStyleSheet(stylesheet)
    return app, myapp


def setLanguage(app):
    try:
        userpath = os.path.expanduser('~/.RTOC')
        with open(userpath+"/config.json", encoding="UTF-8") as jsonfile:
            config = json.load(jsonfile, encoding="UTF-8")
    except:
        config={'language':'en'}
    if config['language'] == 'en':
        translator = QtCore.QTranslator()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        translator.load(packagedir+"/lang/en_en.qm")
        app.installTranslator(translator)
    # more info here: http://kuanyui.github.io/2014/09/03/pyqt-i18n/
    # generate translationfile: % pylupdate5 RTOC.py -ts lang/de_de.ts
    # compile translationfile: % lrelease-qt5 lang/de_de.ts
    # use self.tr("TEXT TO TRANSLATE") in the code

def runInBackground():
    app = QtWidgets.QApplication(sys.argv)
    myapp = RTOC_TCP()
    app, myapp = setStyleSheet(app, myapp)

    app.exec_()


def startRemoteRTOC(remotepath):
    app = QtWidgets.QApplication(sys.argv)
    try:
        userpath = os.path.expanduser('~/.RTOC')
        with open(userpath+"/config.json", encoding="UTF-8") as jsonfile:
            config = json.load(jsonfile, encoding="UTF-8")
    except:
        config={'language':'en'}
    if config['language'] == 'en':
        print("English language selected")
        translator = QtCore.QTranslator()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        translator.load(packagedir+"/lang/en_en.qm")
        app.installTranslator(translator)
    myapp = RTOC(False)
    myapp.config["tcpserver"] = True

    app, myapp = setStyleSheet(app, myapp)
    print(remotepath)
    myapp.show()
    myapp.pluginsWidget.show()
    myapp.scriptDockWidget.hide()
    myapp.deviceWidget.hide()
    myapp.eventWidgets.show()
    button = QtWidgets.QPushButton()
    button.setCheckable(True)
    button.setChecked(True)
    myapp.toggleDevice('NetWoRTOC', button)
    myapp.logger.getPlugin('NetWoRTOC').start(remotepath)
    myapp.logger.getPlugin('NetWoRTOC').widget.comboBox.setCurrentText(remotepath)
    myapp.logger.getPlugin('NetWoRTOC').widget.streamButton.setChecked(True)
    app.exec_()


def startRTOC(tcp = None, port = None):
    app = QtWidgets.QApplication(sys.argv)
    try:
        userpath = os.path.expanduser('~/.RTOC')
        with open(userpath+"/config.json", encoding="UTF-8") as jsonfile:
            config = json.load(jsonfile, encoding="UTF-8")
    except:
        config={'language':'en'}
    if config['language'] == 'en':
        print("English language selected")
        translator = QtCore.QTranslator()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        translator.load(packagedir+"/lang/en_en.qm")
        app.installTranslator(translator)
        # more info here: http://kuanyui.github.io/2014/09/03/pyqt-i18n/
        # generate translationfile: % pylupdate5 RTOC.py -ts lang/de_de.ts
        # compile translationfile: % lrelease-qt5 lang/de_de.ts
        # use self.tr("TEXT TO TRANSLATE") in the code
    myapp = RTOC(tcp, port)
    app, myapp = setStyleSheet(app, myapp)

    myapp.show()
    app.exec_()


if __name__ == '__main__':
    main()
    sys.exit()
