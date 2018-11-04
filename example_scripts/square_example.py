print(round(Funktionsgenerator.Square.latest-Funktionsgenerator.offset))
if(round(Funktionsgenerator.Square.latest-Funktionsgenerator.offset)>= 1):
	Funktionsgenerator.offset += 0.1
Funktionsgenerator.setLabels()