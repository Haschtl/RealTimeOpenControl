try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from ..LoggerPlugin import LoggerPlugin

import time
from threading import Thread
import Adafruit_DHT
import time
import board
import busio
import adafruit_ccs811

devicename = "Futtertrocknung"

dht22 = Adafruit_DHT.DHT22
# css811: sudo nano /boot/config.txt for i2c baudrate
i2c = busio.I2C(board.SCL, board.SDA)
ccs1 = adafruit_ccs811.CCS811(i2c)
ccs2 = adafruit_ccs811.CCS811(i2c, 0x5B)


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)

        self.run = True
        self.samplerate = 1            # Function frequency in Hz (1/sec)
        self.datanames = ['in2coolCO2', 'in2coolTVOC', 'out2coolCO2', 'out2coolTVOC', 'in2coolTemp', 'in2coolHumid', 'out2coolTemp', 'out2coolHumid']
        self.dataunits = ['ppm', 'ppm','ppm','ppm','°C','%','°C','%']
        self.data = [0,0,0,0,0,0,0,0]

        ccs1t = Thread(target=self.getCCS1Data)
        ccs1t.start()
        ccs2t = Thread(target=self.getCCS2Data)
        ccs2t.start()

        dht22_1 = Thread(target=self.getDHT22_1)
        dht22_1.start()
        dht22_2 = Thread(target=self.getDHT22_2)
        dht22_2.start()

        self.__updater = Thread(target=self.__updateT)    # Actualize data
        self.__updater.start()

    def __updateT(self):
        diff = 0
        self.gen_start = time.time()
        while self.run:  # All should be inside of this while-loop, because self.run == False should stops this plugin
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            devname='Futtertrocknung'
            #self.getControllerData()
            self.stream(self.data, self.datanames, devname, self.dataunits)
            diff = (time.time() - start_time)

    def getCCS1Data(self):
        # Wait for the sensor to be ready and calibrate the thermistor
        while not ccs1.data_ready:
            pass
        temp = ccs1.temperature
        ccs1.temp_offset = temp - 25.0

        while self.run:
            time.sleep(1/self.samplerate)
            try:
                self.data[0] = ccs1.eco2
                self.data[1] = ccs1.tvoc
                #temp2 = ccs1.temperature
                print('reading')
                if self.data[0]>2000:
                    print('event')
                    self.event('CO2 Gehalt hoch', sname="CO2", dname="Futtertrocknung", priority=2)
            except:
                print("Error reading CCS811 [1]")

    def getCCS2Data(self):
        # Wait for the sensor to be ready and calibrate the thermistor
        while not ccs2.data_ready:
            pass
        temp = ccs2.temperature
        ccs2.temp_offset = temp - 25.0

        while self.run:
            time.sleep(1/self.samplerate)
            try:
                self.data[2] = ccs2.eco2
                self.data[3] = ccs2.tvoc
                #temp2 = ccs2.temperature
            except:
                print("Error reading CCS811 [2]")

    def getDHT22_1(self):
        pin = 27
        while self.run:
            time.sleep(1/self.samplerate)
            humidity, temperature = Adafruit_DHT.read_retry(dht22, pin)
            self.data[4] = temperature
            self.data[5] = humidity

    def getDHT22_2(self):
        pin = 17
        while self.run:
            time.sleep(1/self.samplerate)
            humidity, temperature = Adafruit_DHT.read_retry(dht22, pin)
            self.data[6] = temperature
            self.data[7] = humidity

    def getControllerData(self):
        self.data['fanVelocity'] = '?'
        self.data['fanMode'] = "Druck"
        self.data['active'] = False
        self.data['fan2heuPressure'] = '?'
        self.data['fan2heuVelocity'] = '?'
        self.data['fan2heuPressureDes'] = 0
        self.data['fan2heuVelocityDes'] = 0
        self.data['fanManualDes'] = 0

    def setActive(self, active = True):
        pass

    def setMode(self, mode = 0): # manuell, druck, durchfluss
        pass

    def setDesired(self, mode, value):
        pass
