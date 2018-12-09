x, y = rtoc.combine([Generator.Square, Generator2.Sinus], n=2000)

ycom = y[0]-y[1]

plot(x,ycom)