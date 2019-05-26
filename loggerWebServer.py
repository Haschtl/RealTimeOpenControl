#!/usr/bin/python3 -u

import sys

#sys.path.insert(0,'/home/pi/kellerlogger/')

from RTOC.RTLogger import RTOC_Web_standalone

try:
	RTOC_Web_standalone.start(debug=False)
	# a=logger.getThread()
	# if a is not None:
	# 	a.join()
except KeyboardInterrupt:
	#logger.close()
	print("LoggerWebServer stopped by user")
