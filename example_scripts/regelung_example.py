ki=0
kp=0
kd=1
desired = 0
global oldI=0
value = math.sin(clock)
global.oldI=value
stream(value, "signal")
regelung, newI =rtoc.PID(noDevice.signal, desired, kp, ki, kd, global.oldI)
global.oldI = newI
stream(regelung, "regler")
