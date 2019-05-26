import ui
from RTOC import Plugin as rtoc

def switchOn(sender):
	if sender.value:
		dev=sender.superview['textfield1']
		r.start(dev.text)
	else:
		r.stop()
		
def changeSamplerate(sender):
	try:
		r.samplerate=float(sender.text)
		print('Samplerate changed')
	except Exception:
		print('Not a float')


v = ui.load_view()
r = rtoc()
v.present('sheet')

