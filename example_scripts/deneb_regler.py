ki=0.001
kp=0.06
kd=0
global oldI=0
stream(value, "signal")
des = 800
regelung, newI = rtoc.PID(Engine1.brightness, des, kp, ki, kd, global.oldI)
global.oldI = newI
if self.regelung>255:
	self.regelung=255
if self.regelung<0:
	self.regelung=0
ret = Deneb.cmd("engine1:dc1="+str(regelung)+";"+"engine1:dc2="+str(regelung)+";"+"engine1:dc3="+str(regelung)+";"+"engine1:dc4="+str(regelung)+";")
stream(ki*global.oldI,"KI")
stream(kd*diff(noDevice.signal),"KD")
stream(regelung, "regler")