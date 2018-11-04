plotLine("Loop", "Note", "one")
plotLine("ten", "Note", "two", x=clock+10)
print("Loop")

global x=1
self.x += 1
stream(self.x, "Global","Test")

plot(Funktionsgenerator.Square, "klaus", "baum")
plot(Funktionsgenerator.Square, sname="klaus2", dname="baum",unit="rad")

#clearData()
#exportData()

x,y = rtoc.resample(Funktionsgenerator.Square,100)
plot(x,y, dname="Funktionsgenerator", sname="Resample",unit="rad")

x,y = rtoc.resampleFourier(Funktionsgenerator.Square,100)
plot(x,y, dname="Funktionsgenerator", sname="ResampleFourier",unit="rad")

y = rtoc.mean(Funktionsgenerator.Square,10)
print("Mean ",y)

x,y = rtoc.runningMean(Funktionsgenerator.Square,10)
plot(x,y, dname="Funktionsgenerator", sname="runningMean",unit="rad")

x,y, params = rtoc.lsfit(Funktionsgenerator.Square)#,"linear",0,100)
plot(x,y, dname="Funktionsgenerator", sname="Lsfit",unit="rad")

dydx = rtoc.d(Funktionsgenerator.Square)
print("\nDiff",dydx)

x,y = rtoc.diff(Funktionsgenerator.Square)
plot(x,y, dname="Funktionsgenerator", sname="diff",unit="rad")

y = rtoc.PID(Funktionsgenerator.Square,10)
print(y)