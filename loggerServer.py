#!/usr/bin/python3 -u

import sys
import os
import json
import logging
import traceback

# sys.path.insert(0,'/home/pi/kellerlogger/')

from RTOC.RTLogger.RTLogger import RTLogger

try:
    from PyQt5 import QtCore

    app = QtCore.QCoreApplication(sys.argv)
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
        translator.load(packagedir+"/RTOC/locales/de_de.qm")
        app.installTranslator(translator)
        # QtCore.QCoreApplication.installTranslator(translator)
        print('German language selected')
except (ImportError, SystemError):
    logging.warning('Cannot set language')

logger = RTLogger(True)
try:
    # logger.startPlugin('Heliotherm')
    # logger.getPlugin('Heliotherm').start('192.168.178.72')
    # logger.startPlugin('Futtertrocknung')
    a = logger.getThread()
    if a is not None:
        a.join()
except (KeyboardInterrupt, SystemExit):
    logger.stop()
    print("LoggerServer stopped by user")
