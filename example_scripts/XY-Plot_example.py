stream(np.sin(clock), "sinus1","no")
stream(np.sin(clock+1.7), "sinus3","no")
stream([no.sinus1.latest*Funktionsgenerator.Square.latest,no.sinus3.latest*Funktionsgenerator.Square.latest], "sinus2","no")
