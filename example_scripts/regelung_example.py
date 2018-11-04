global ki=0.8
global kp=0.4
global kd=1
global oldI=0
global error=0
global regelung=0
value = math.sin(clock)
stream(value, "signal")
self.oldI = self.error +  value-self.regelung
self.error = value-self.regelung
self.regelung = self.ki*self.oldI+self.kp*self.error+rtoc.d(noDevice.signal)+self.regelung
stream(self.regelung, "regler")
