#!/usr/bin/python3 -u

"""
You can run a RTOC.RTLogger instance with ``python3 -m RTOC.RTLogger``.

To start RTOC in a background thread, run ``python3 -m RTOC.RTLogger -s start``. You can than stop it with ``python3 -m RTOC.RTLogger -s stop``.

To open the minimal console editor, run ``python3 -m RTOC.RTLogger -c``

"""

import sys
import getopt
import os
import json
import time
# import traceback
import logging as log
from .Daemon import Daemon
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

__package__ = "RTOC.RTLogger"
__main__ = __name__

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



class RTOCDaemon(Daemon):
    def __init__(self, pidfile, port=5050):
        # super(RTOCDaemon, self).__init__(pidfile)
        self.pidfile = pidfile
        self.port = 5050

    def run(self):
        # Or simply merge your code with MyDaemon.
        from .RTLogger import RTLogger
        logger = RTLogger(True, self.port)
        return logger


def main():
    opts, args = getopt.getopt(sys.argv[1:], "hvdws:p:c", [
                               "server=", "port=", 'config', 'logger', 'database'])
    if len(opts) == 0:
        startRTLogger(True)
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
                    'RTOC.RTLogger [-h, -s, -l, -w]\n -h: Hilfe\n-s (--server) [COMMAND]: Websocket-Server ohne GUI\n\t- start: Starts the RTOC-daemon\n\t- stop: Stops the RTOC-daemon\n\t- restart: Restarts the RTOC-daemon\n-p (--port): Starte Websocket-Server auf anderem Port (Standart: 5050)\n-c (--config [OPTION=value]): Configure RTOC, type "-c list" to see all options')
                sys.exit(0)
            elif opt == '-v':
                logging.info("3.0")
            elif opt in ('-s', '--server'):
                if os.name == 'nt':
                    logging.info(
                        'Running RTOC as a service is not supported on windows. Running just in background')
                    from .RTLogger import RTLogger
                    logger = RTLogger(True, port)
                    # runInBackground()
                    try:
                        while logger.run:
                            time.sleep(1)
                    finally:
                        logger.stop()
                    sys.exit(0)
                command = arg
                daemon = RTOCDaemon('/tmp/RTOCDaemon.pid')
                if command == 'stop':
                    daemon.stop()
                elif command == 'restart':
                    daemon.restart()
                elif command == 'start':
                    daemon.start()
                else:
                    logging.error('Unknown server command: '+str(command) + '\nUse "start", "stop" or "restart"')
                    sys.exit(1)
            elif opt in ('-c', '--config'):
                from . import Console
                Console.main()
                # configureRTOC(arg)
            elif opt in ('-d', '--database'):
                from . import RT_data
                # logger = RTLogger()
                RT_data.main()  # logger)
                # configureRTOC(arg)
        # startRTOC(None, port)

def startRTLogger(websocket, port=None):
    try:
        from .RTLogger import RTLogger
        logger = RTLogger(websocket, port)
        a = logger.getThread()
        if a is not None:
            a.join()
    except KeyboardInterrupt:
        logger.stop()
        print("LoggerServer stopped by user")

if __name__ == '__main__':
    main()
    sys.exit()
