x,y = rtoc.combine([Engine0.Driver,Engine0.LED,Engine1.Driver,Engine1.LED],10000)

plot(x,(y[0]+y[1])/2,"Engine0Mittel","Skript","°C")
plot(x,(y[2]+y[3])/2,"Engine1Mittel","Skript","°C")

N=34

x, y= rtoc.runningMean(Deneb.Engine0Driver,N)
plot(x,y,"a")
x, y= rtoc.runningMean(Deneb.Engine0LED,N)
plot(x,y,"b")
