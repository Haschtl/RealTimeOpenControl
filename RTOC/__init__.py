
import sys
import os
import json
import getopt
import traceback

import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

# __package__ = "RTOC"
# __main__ = __name__
name = "RTOC"
__version__ = "3.0"


def main():
    """
    An example docstring for a main definition.
    """
    opts, args = getopt.getopt(sys.argv[1:], "hlr:", [
                               "remote="])
    if len(opts) == 0:
        startRTOC()
    else:
        for opt, arg in opts:
            if opt in ('-p', '--port'):
                port = int(arg)
                break
            else:
                port = 5050
        for opt, arg in opts:
            if opt == '-h':
                logging.info(
                    'RTOC.py [-h] [-r <Remoteadress>]\n -h: Help\n-r (--remote) <Remoteadress>: Websocket client for RTOC server\nFor options without GUI, run "python3 -m RTOC.RTLogger -h"')
                sys.exit(0)
            elif opt == '-v':
                logging.info("")
            elif opt in ("-r", "--remote"):
                remotepath = arg
                startRemoteRTOC(remotepath)
                sys.exit(0)
            elif opt == '-l':
                startRTOC(local =True)
                sys.exit(0)


def configureRTOC(arg):
    userpath = os.path.expanduser('~/.RTOC')
    if os.path.exists(userpath+"/config.json"):
        try:
            with open(userpath+"/config.json", encoding="UTF-8") as jsonfile:
                config = json.load(jsonfile, encoding="UTF-8")
        except Exception:
            config = {}
            logging.debug(traceback.format_exc())
            logging.error('Could not load config')
    else:
        logging.error('No config-file found in ~/.RTOC/\nPlease start RTOC at least once.')
        sys.exit(1)
    if arg == 'list':
        logging.info('This is your current configuration:')
        for key in config.keys():
            if key not in ['csv_profiles', 'telegram_chat_ids', 'lastSessions', 'grid', 'plotLegendEnabled', 'blinkingIdentifier', 'scriptWidget', 'deviceWidget', 'signalsWidget', 'pluginsWidget', 'eventWidget', 'newSignalSymbols', 'plotLabelsEnabled', 'plotGridEnabled', 'plotLegendEnabled', 'signalStyles', 'plotInverted', 'plotRate', 'xTimeBase', 'timeAxis', 'systemTray', 'documentfolder', 'language']:
                logging.info(key+"\t"+str(config[key]))

    else:
        splitted = arg.split('=')
        if len(splitted) != 2:
            logging.info(
                'Please provide options like this: "python3 -m RTOC -c websocketserver=False\nYour entry didn\'t include a "="')
            sys.exit(1)
        else:
            if splitted[0] not in config.keys():
                logging.warning('The config file has no option '+splitted[0])
                sys.exit(1)
            t = type(config[splitted[0]])
            try:
                if t != bool:
                    newValue = t(splitted[1])
                elif splitted[1].lower() in ['true', '1', 't', 'y', 'yes', 'yeah', 'yup', 'certainly', 'uh-huh', 'ja', 'j', 'jupp', 'jawohl']:
                    newValue = True
                else:
                    newValue = False

                oldValue = config[splitted[0]]
                config[splitted[0]] = newValue
                with open(userpath+"/config.json", 'w', encoding="utf-8") as fp:
                    json.dump(config, fp,  sort_keys=False, indent=4, separators=(',', ': '))
                logging.info('Option "'+splitted[0]+'" was changed from "' + str(oldValue)+'" to "'+str(newValue)+'"')
            except Exception:
                logging.warning('Your entered value "'+splitted[1]+'" is not of the correct type.')
                sys.exit(1)


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
            with open(packagedir+"/RTOC_GUI/ui/qtmodern.qss", 'r') as myfile:
                stylesheet = myfile.read().replace('\n', '')
            app.setStyleSheet(stylesheet)
            qtmodern.styles.dark(app)
            # mw = qtmodern.windows.ModernWindow(myapp)

            mw = myapp
            return app, mw
        except (ImportError, SystemError):
            tb = traceback.format_exc()
            logging.debug(tb)
            logging.warning("QtModern not installed")
            type = 'QDarkStyle'
    if type == 'QDarkStyle':
        try:
            import qdarkstyle
            dark_stylesheet = qdarkstyle.load_stylesheet_pyqt5()
            app.setStyleSheet(dark_stylesheet)
            return app, myapp
        except (ImportError, SystemError):
            tb = traceback.format_exc()
            logging.debug(tb)
            logging.warning("QtModern not installed")
            type == 'qdarkgraystyle'
    if type == 'qdarkgraystyle':
        try:
            import qdarkgraystyle
            dark_stylesheet = qdarkgraystyle.load_stylesheet()
            app.setStyleSheet(dark_stylesheet)
            return app, myapp
        except (ImportError, SystemError):
            tb = traceback.format_exc()
            logging.debug(tb)
            logging.warning("QtModern not installed")
    packagedir = os.path.dirname(os.path.realpath(__file__))
    with open(packagedir+"/RTOC_GUI/ui/darkmode.html", 'r') as myfile:
        stylesheet = myfile.read().replace('\n', '')
    stylesheet = stylesheet.replace(
        '/RTOC_GUI/ui/icons', os.path.join(packagedir, 'data', 'ui', 'icons').replace('\\', '/'))
    # stylesheet = stylesheet.replace('/RTOC_GUI/ui/icons','./RTOC_GUI/ui/icons')
    app.setStyleSheet(stylesheet)
    return app, myapp


# def setLanguage(app):
#
#     import gettext
#     from PyQt5 import QtCore
#     # from PyQt5 import QtWidgets
#     userpath = os.path.expanduser('~/.RTOC')
#     if os.path.exists(userpath+"/config.json"):
#         try:
#             with open(userpath+"/config.json", encoding="UTF-8") as jsonfile:
#                 config = json.load(jsonfile, encoding="UTF-8")
#         except Exception:
#             logging.debug(traceback.format_exc())
#             config = {'global': {'language': 'en'}}
#     else:
#         config = {'global': {'language': 'en'}}
#     if config['global']['language'] == 'de':
#         translator = QtCore.QTranslator()
#         if getattr(sys, 'frozen', False):
#             # frozen
#             packagedir = os.path.dirname(sys.executable)
#         else:
#             # unfrozen
#             packagedir = os.path.dirname(os.path.realpath(__file__))
#         translator.load(packagedir+"/locales/de_de.qm")
#         app.installTranslator(translator)

        # el = gettext.translation('base', localedir='locales', languages=['de'])
        # el.install()
        # _ = el.gettext
    # more info here: http://kuanyui.github.io/2014/09/03/pyqt-i18n/
    # generate translationfile: % pylupdate5 RTOC.py -ts lang/de_de.ts
    # compile translationfile: % lrelease-qt5 lang/de_de.ts
    # use self.tr("TEXT TO TRANSLATE") in the code


def startRemoteRTOC(remotepath):

    from PyQt5 import QtCore
    from PyQt5 import QtWidgets

    from .RTOC import RTOC

    app = QtWidgets.QApplication(sys.argv)

    # app = setLanguage(app)
    from PyQt5 import QtCore
    # from PyQt5 import QtWidgets
    userpath = os.path.expanduser('~/.RTOC')
    if os.path.exists(userpath+"/config.json"):
        try:
            with open(userpath+"/config.json", encoding="UTF-8") as jsonfile:
                config = json.load(jsonfile, encoding="UTF-8")
        except Exception:
            logging.debug(traceback.format_exc())
            config = {'global': {'language': 'en'}}
    else:
        config = {'global': {'language': 'en'}}
    if config['global']['language'] == 'de':
        translator = QtCore.QTranslator()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        translator.load(packagedir+"/locales/de_de.qm")
        app.installTranslator(translator)


    myapp = RTOC(False)
    myapp.config['websocket']['active'] = True

    app, myapp = setStyleSheet(app, myapp)
    logging.info(remotepath)
    myapp.show()
    myapp.logger.remote.connect(hostname=remotepath, port=5050)
    app.exec_()


def startRTOC(websocket=None, port=None, local =False, customConfigPath=None):

    from PyQt5 import QtCore
    from PyQt5 import QtWidgets

    from .RTOC import RTOC

    app = QtWidgets.QApplication(sys.argv)

    # app = setLanguage(app)
    from PyQt5 import QtCore
    # from PyQt5 import QtWidgets
    userpath = os.path.expanduser('~/.RTOC')
    if os.path.exists(userpath+"/config.json"):
        try:
            with open(userpath+"/config.json", encoding="UTF-8") as jsonfile:
                config = json.load(jsonfile, encoding="UTF-8")
        except Exception:
            logging.debug(traceback.format_exc())
            config = {'global': {'language': 'en'}}
    else:
        config = {'global': {'language': 'en'}}
    if config['global']['language'] == 'de':
        translator = QtCore.QTranslator()
        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        translator.load(packagedir+"/locales/de_de.qm")
        app.installTranslator(translator)


    myapp = RTOC(websocket, port, local, customConfigPath)
    app, myapp = setStyleSheet(app, myapp)

    myapp.show()
    app.exec_()
