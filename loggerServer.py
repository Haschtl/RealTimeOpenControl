#!/usr/bin/python3 -u

import sys

#sys.path.insert(0,'/home/pi/kellerlogger/')

from RTOC.RTLogger.RTLogger import RTLogger

logger = RTLogger(True)
try:
	#logger.startPlugin('Heliotherm')
	#logger.getPlugin('Heliotherm').start('192.168.178.72')
	#logger.startPlugin('Futtertrocknung')
	a=logger.getThread()
	if a is not None:
		a.join()
except KeyboardInterrupt:
	logger.stop()
	print("LoggerServer stopped by user")
