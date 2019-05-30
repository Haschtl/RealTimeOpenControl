#!/usr/bin/python3 -u

"""
You can run a RTOC.RTLogger instance with ``python3 -m RTOC.RTLogger``.

To start RTOC in a background thread, run ``python3 -m RTOC.RTLogger -s start``. You can than stop it with ``python3 -m RTOC.RTLogger -s stop``.

To open the minimal console editor, run ``python3 -m RTOC.RTLogger -c``

To run the webserver, run ``python3 -m RTOC.RTLogger -w``.
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
    opts, args = getopt.getopt(sys.argv[1:], "hvdws:p:cw:", [
                               "server=", "port=", 'config', 'logger', 'web', 'database'])
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
                    'RTOC.RTLogger [-h, -s, -l, -w]\n -h: Hilfe\n-s (--server) [COMMAND]: TCP-Server ohne GUI\n\t- start: Starts the RTOC-daemon\n\t- stop: Stops the RTOC-daemon\n\t- restart: Restarts the RTOC-daemon\n-w Startet RTLogger mit Website\n-p (--port): Starte TCP-Server auf anderem Port (Standart: 5050)\n-c (--config [OPTION=value]): Configure RTOC, type "-c list" to see all options')
                sys.exit(0)
            elif opt == '-v':
                logging.info("2.0.1")
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
            elif opt in ('-w', '--web'):
                startRTOC_Web(port)
        # startRTOC(None, port)


def startRTOC_Web(port, standalone=True):
    userpath = os.path.expanduser('~/.RTOC')
    if os.path.exists(userpath+"/config.json"):
        try:
            with open(userpath+"/config.json", encoding="UTF-8") as jsonfile:
                config = json.load(jsonfile, encoding="UTF-8")
        except Exception:
            return False
    standalone = config['postgresql']['active']
    if standalone:
        from . import RTOC_Web_standalone
        RTOC_Web_standalone.start(debug=False)
    else:
        from . import RTOC_Web
        RTOC_Web.start(debug=False)


def startRTLogger(tcp, port=None):
    try:
        from .RTLogger import RTLogger
        logger = RTLogger(tcp, port)
        # logger.startPlugin('Heliotherm')
        # logger.getPlugin('Heliotherm').start('192.168.178.72')
        # logger.startPlugin('Futtertrocknung')
        a = logger.getThread()
        if a is not None:
            a.join()
    except KeyboardInterrupt:
        logger.stop()
        print("LoggerServer stopped by user")


# def configureRTOC(arg):
#     userpath = os.path.expanduser('~/.RTOC')
#     if os.path.exists(userpath+"/config.json"):
#         try:
#             with open(userpath+"/config.json", encoding="UTF-8") as jsonfile:
#                 config = json.load(jsonfile, encoding="UTF-8")
#         except Exception:
#             config = {}
#             logging.debug(traceback.format_exc())
#             logging.error('Could not load config')
#     else:
#         logging.error('No config-file found in ~/.RTOC/\nPlease start RTOC at least once.')
#         sys.exit(1)
#     if arg == 'list':
#         logging.info('This is your current configuration:')
#         for key in config.keys():
#             if key not in ['csv_profiles', 'telegram_chat_ids', 'lastSessions', 'grid', 'plotLegendEnabled', 'blinkingIdentifier', 'scriptWidget', 'deviceWidget', 'signalsWidget', 'pluginsWidget', 'eventWidget', 'newSignalSymbols', 'plotLabelsEnabled', 'plotGridEnabled', 'plotLegendEnabled', 'signalStyles', 'plotInverted', 'plotRate', 'xTimeBase', 'timeAxis', 'systemTray', 'documentfolder', 'language']:
#                 logging.info(key+"\t"+str(config[key]))
#
#     else:
#         splitted = arg.split('=')
#         if len(splitted) != 2:
#             logging.info(
#                 'Please provide options like this: "python3 -m RTOC -c tcpserver=False\nYour entry didn\'t include a "="')
#             sys.exit(1)
#         else:
#             if splitted[0] not in config.keys():
#                 logging.warning('The config file has no option '+splitted[0])
#                 sys.exit(1)
#             t = type(config[splitted[0]])
#             try:
#                 if t != bool:
#                     newValue = t(splitted[1])
#                 elif splitted[1].lower() in ['true', '1', 't', 'y', 'yes', 'yeah', 'yup', 'certainly', 'uh-huh', 'ja', 'j', 'jupp', 'jawohl']:
#                     newValue = True
#                 else:
#                     newValue = False
#
#                 oldValue = config[splitted[0]]
#                 config[splitted[0]] = newValue
#                 with open(userpath+"/config.json", 'w', encoding="utf-8") as fp:
#                     json.dump(config, fp,  sort_keys=False, indent=4, separators=(',', ': '))
#                 logging.info('Option "'+splitted[0]+'" was changed from "' +
#                              str(oldValue)+'" to "'+str(newValue)+'"')
#             except Exception:
#                 logging.warning('Your entered value "'+splitted[1]+'" is not of the correct type.')
#                 sys.exit(1)


if __name__ == '__main__':
    main()
    sys.exit()
