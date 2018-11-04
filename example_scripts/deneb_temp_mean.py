x0,y0 = rtoc.combine([Engine0.Driver,Engine0.LED],10000)
x1,y1 = rtoc.combine([Engine1.Driver,Engine1.LED],10000)

plot(x0,(y0[0]+y1[1])/2,"Engine0Mittel","Skript","°C")
plot(x1,(y1[1]+y1[1])/2,"Engine1Mittel","Skript","°C")

N=34

x, y= rtoc.runningMean(Deneb.Engine0Driver,N)
plot(x,y,"a")
x, y= rtoc.runningMean(Deneb.Engine0LED,N)
plot(x,y,"b")
