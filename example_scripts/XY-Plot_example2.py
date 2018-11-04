stream(np.sin(clock), "sinus1","no")
stream(np.sin(clock+math.pi/2), "sinus3","no")
stream([no.sinus1.latest,no.sinus3.latest], "sinus2","no")
