global ki=0.001
global kp=0.06
global kd=0
global oldI=0
global error=0
global regelung=0
value = Deneb.engine1:brightness.latest
stream(value, "signal")
des = 800
self.oldI = self.oldI + ( value-des)
#self.error = value-self.regelung
self.error = value-des
self.regelung = self.ki*self.oldI+self.kp*self.error+diff(noDevice.signal)*self.kd+self.regelung
if self.regelung>255:
	self.regelung=255
if self.regelung<0:
	self.regelung=0
ret = Deneb.cmd("engine1:dc1="+str(self.regelung)+";"+"engine1:dc2="+str(self.regelung)+";"+"engine1:dc3="+str(self.regelung)+";"+"engine1:dc4="+str(self.regelung)+";")
stream(self.ki*self.oldI,"KI")
stream(self.kd*diff(noDevice.signal),"KD")
stream(self.kp*self.error,"KP")
stream(self.regelung, "regler")