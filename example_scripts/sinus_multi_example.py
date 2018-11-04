stream(np.sin(clock), "sinus1","no")
no.sinus1.latest = 2*no.sinus1.latest
stream(np.sin(clock+2), "sinus2","no")
stream(no.sinus1.latest+no.sinus2.latest,"sinus3","no")

# Start this script three times to plot all three lines