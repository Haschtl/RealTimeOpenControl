from LoggerPlugin import LoggerPlugin

import time
from threading import Thread
import motion
from objc_util import *
import location

devicename = "Iphone"


class Plugin(LoggerPlugin):
		def __init__(self, stream=None, plot= None, event=None):
				# Plugin setup
				super(Plugin, self).__init__(stream, plot, event)
				self.samplerate = 10         
				self.createTCPClient('192.168.178.103')
				# Data-logger thread
				self.run = True  # False -> stops thread
				self.UIDevice = ObjCClass('UIDevice')
				self.UIScreen = ObjCClass('UIScreen')
				print(str(self.UIDevice.currentDevice().name()))
				self.createTCPClient()
				self.setDeviceName(str(self.UIDevice.currentDevice().name()))
				self.device = self.UIDevice.currentDevice()

		def start(self, dev='192.168.178.103'):
				self.run = True
				print(dev)
				self.tcpaddress =dev
				motion.start_updates()
				location.start_updates()
				print('Device '+dev)
				self.device.setBatteryMonitoringEnabled_(True)
				self.__updater = Thread(target=self.__updateT)
				self.__updater.start()
				print("Stream started")
			
		# THIS IS YOUR THREAD
		def __updateT(self):
				diff = 0
				self.gen_start = time.time()
				while self.run:
						print('updatethread')
						if diff < 1/self.samplerate:
								time.sleep(1/self.samplerate-diff)
						start_time = time.time()
						y, snames, units = self.sendData()
						#print(y)
						self.sendTCP(y=y, sname=snames, unit=units)
						diff = (time.time() - start_time)
			
		def sendData(self):
				g = motion.get_gravity()
				acc = motion.get_user_acceleration()
				att = motion.get_attitude()
				mag = motion.get_magnetic_field()
				bat = self.device.batteryLevel()*100
				batState = self.device.batteryState()
				loc = location.get_location()
				bri = 	self.UIScreen.mainScreen().brightness()
				
				y = []
				snames = []
				units = []
				
				y += [g[0],g[1],g[2]]
				snames += ['GravityX','GravityY','GravityZ']
				units += ['m/s^2', 'm/s^2', 'm/s^2']
				
				y += [acc[0],acc[1],acc[2]]
				snames += ['AccelerationX','AccelerationY','AccelerationZ']
				units += ['m/s^2', 'm/s^2', 'm/s^2']

				y += [att[0],att[1],att[2]]
				snames += ['Roll','Pitch','Yawn']
				units += ['°','°','°']
				
				y += [mag[0],mag[1],mag[2], mag[3]]
				snames += ['MagneticX','MagneticY','MagneticZ', 'MagneticAccuracy']
				units += ['A/m','A/m','A/m','%']
				
				y += [bat]
				snames += ['Battery']
				units += ['%']
				
				y += [batState]
				snames += ['BatteryState']
				units += ['%']
				
				y += [bri*100]
				snames += ['Brightness']
				units += ['%']
				
				y += [loc['latitude']]
				snames += ['Latitude']
				units += ['"']
				y += [loc['longitude']]
				snames += ['Longitude']
				units += ['"']
				y += [loc['altitude']]
				snames += ['Altitude']
				units += ['"']
				y += [loc['horizontal_accuracy']]
				snames += ['HorizontalAccuracy']
				units += ['%']
				y += [loc['vertical_accuracy']]
				snames += ['VerticalAccuracy']
				units += ['%']
				y += [loc['speed']]
				snames += ['Speed']
				units += ['m/s']
				y += [loc['course']]
				snames += ['Course']
				units += ['']
				
				return y, snames, units
		
		def stop(self):
				self.run = False
				motion.stop_updates()
				location.stop_updates()
				self.device.setBatteryMonitoringEnabled_(False)
				print('Stream stopped')

if __name__ == "__main__":
		standalone = Plugin()
		standalone.sendData()
		standalone.stop()
