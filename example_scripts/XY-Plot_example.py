stream(np.sin(clock), "sinus1","no")
stream(np.sin(clock+1.7), "sinus3","no")
print(no.sinus1.latest*Generator.Square.latest)
stream([no.sinus1.latest*Generator.Square.latest, no.sinus3.latest*Generator.Square.latest], sname="sinus2",dname="no")
