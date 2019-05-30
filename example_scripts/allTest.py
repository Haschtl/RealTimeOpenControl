event("Loop", "Note", "one")
event("ten", "Note", "two", x=clock+10)
print("Loop")

global x=1
global.x += 1
stream(global.x, "Global","Test")

plot(Generator.Square, "klaus", "baum")
plot(Generator.Square, sname="klaus2", dname="baum",unit="rad")

#clearData()
#exportData()

x,y = rtoc.resample(Generator.Square,100)
plot(x,y, dname="Generator", sname="Resample",unit="rad")

x,y = rtoc.resampleFourier(Generator.Square,100)
plot(x,y, dname="Generator", sname="ResampleFourier",unit="rad")

y = rtoc.mean(Generator.Square,10)
print("Mean ",y)

x,y = rtoc.runningMean(Generator.Square,10)
plot(x,y, dname="Generator", sname="runningMean",unit="rad")

x,y, params = rtoc.lsfit(Generator.Square)#,"linear",0,100)
plot(x,y, dname="Generator", sname="Lsfit",unit="rad")

dydx = rtoc.d(Generator.Square)
print("\nDiff",dydx)

x,y = rtoc.diff(Generator.Square)
plot(x,y, dname="Generator", sname="diff",unit="rad")

y = rtoc.PID(Generator.Square,10)
print(y)