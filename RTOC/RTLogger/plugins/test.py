from ...LoggerPlugin import LoggerPlugin

import time
import math
import random
from threading import Thread
from PyQt5 import uic
from PyQt5 import QtWidgets
import datetime as dt
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)
devicename = "test"

class Plugin(LoggerPlugin):
    def __init__(self, *args, **kwargs):
        # Plugin setup
        super(Plugin, self).__init__(*args, **kwargs)
        self.setDeviceName(devicename)
        self.smallGUI = True
        self._startTime = time.time()
        self.setPerpetualTimer(self.__updateT, samplerate=10)
        self.gen_start = time.time()
        self.start()

        self._sampleT = Thread(target=self.sampler)
        self._sampleT.start()

    def __updateT(self):
        timedelta = time.time()-self._startTime
        delta = dt.timedelta(seconds=timedelta)
        #print('Total time: {}'.format(delta))
        error = 1/self.samplerate-timedelta
        self._startTime = time.time()
        delay = random.random()*1/self.samplerate
        #print('Taking data took {}s'.format(round(delay,2)))
        # if self.samplerate == 1:
        #     self.samplerate = 10
        # else:
        #     self.samplerate= 1
        self.stream(
            y=[self.samplerate, timedelta, delay, error],
            snames=['Samplerate.a', 'Delta', 'Delay', 'Error'],
            )
        time.sleep(delay)

    def sampler(self):
        while self.run:
            print('changing samplerate')
            time.sleep(5)
            if self.samplerate == 2:
                self.samplerate = 10
            else:
                self.samplerate= 2
