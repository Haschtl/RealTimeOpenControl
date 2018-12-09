print(round(Generator.Square.latest-Generator.offset))
if(round(Generator.Square.latest-Generator.offset)>= 1):
	Generator.offset += 0.1
Generator.setLabels()