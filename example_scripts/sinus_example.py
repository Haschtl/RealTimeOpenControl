Funktionsgenerator.gen_level = abs(Funktionsgenerator.Sinus.latest)
print(Funktionsgenerator.gen_level)
if Funktionsgenerator.gen_level < 0.01:
	Funktionsgenerator.gen_level = 1