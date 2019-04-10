# bokeh serve --show test.py
from bokeh.plotting import figure, curdoc
from bokeh.driving import linear

from bokeh.models import ColumnDataSource
from bokeh.models.widgets import TextInput, PasswordInput
from bokeh.layouts import column, layout
from bokeh.models.widgets import Toggle
from bokeh.models import WheelZoomTool
from bokeh.palettes import Category20 as palette

import os
import time

from .LoggerPlugin import LoggerPlugin

try:
    from PyQt5.QtCore import QCoreApplication
    translate = QCoreApplication.translate
except ImportError:
    def translate(id, text):
        return text

HOST = "127.0.0.1"

# select a palette
colors = palette[20]

TOOLTIPS = [
    (translate('Web', "Signal"), "@name"),
    (translate('Web', "Index"), "$index"),
    (translate('Web', "Messwert"), "@y @unit"),
    (translate('Web', "Zeitpunkt"), "-@x ms"),
]

signals = []
signalNames = []
now = time.time()


@linear()
def update(step):
    global signalNames
    global now
    ans = rtoc_web._sendTCP(getSignalList=True, getSignal='all')
    if ans != False and ans != None:
        if ans['signalList'] != signalNames:
            for i, name in enumerate(ans['signalList']):
                if name not in signalNames:
                    print('Adding signal')
                    sig = ans['signals']['.'.join(name)]
                    x = [(s-now)*1000 for s in sig[0]]
                    rtoc_web.addSignal(x=x, y=sig[1], sname=name[1],
                                       dname=name[0], unit='', color=colors[i % len(colors)])
            signalNames = ans['signalList']
        if not rtoc_web.pauseButton.active:
            for s in signals:
                if s.data['name'][-1].split('.') in signalNames:
                    sig = ans['signals'][s.data['name'][-1]]
                    now = time.time()
                    newdata = {}
                    newdata['x'] = [(s-now)*1000 for s in sig[0]]
                    newdata['y'] = sig[1]
                    newdata['name'] = [s.data['name'][-1] for i in sig[0]]
                    newdata['unit'] = [s.data['unit'][-1] for i in sig[1]]
                    s.data = newdata
                    s.trigger('data', s.data, s.data)
    elif ans is False:
        rtoc_web.connectButton.button_type = "danger"
        rtoc_web.connectButton.label = translate('Web', "Verbindung fehlgeschlagen")
        curdoc().remove_periodic_callback(rtoc_web.updater)
        rtoc_web.updater = None
    else:
        rtoc_web.connectButton.button_type = "danger"
        rtoc_web.connectButton.label = translate('Web', "Passwort falsch")
        curdoc().remove_periodic_callback(rtoc_web.updater)
        rtoc_web.updater = None


class RTOC_Web(LoggerPlugin):
    def __init__(self, host=None):

        super(RTOC_Web, self).__init__(None, None, None)
        self.updater = None
        self.p = self.createPlot()
        self.createGUI()

        self.setLegend()
        self.runHTMLServer()
        self.hostname = host
        if self.hostname is not None:
            self.hostInput.value = self.hostname
            self.connectButton.active = True
            # self.connect()

    def runHTMLServer(self):
        curdoc().add_root(column(self.p, sizing_mode='stretch_both'))  # 'stretch_both'))
        curdoc().add_root(column(self.bottom_gui))
        curdoc().title = "RTOC-Web"
        curdoc().theme = 'dark_minimal'

    def createGUI(self):
        self.hostInput = TextInput(value=HOST, placeholder=HOST, sizing_mode='scale_width')
        self.connectButton = Toggle(label=translate('Web', "Verbinden"),
                                    sizing_mode='scale_width', name=' ')
        self.connectButton.on_click(self.connect)
        self.pauseButton = Toggle(label=translate('Web', "Pause"), sizing_mode='scale_width')
        self.pauseButton.on_click(self.pausePlot)
        self.passwordInput = PasswordInput(value='', placeholder=translate(
            'Web', '(TCP-Server Passwort)'), sizing_mode='scale_width')

        # self.top_gui = layout([[self.pauseButton]], sizing_mode='scale_width')
        self.bottom_gui = layout(
            [[self.pauseButton, self.connectButton, self.hostInput, self.passwordInput]], sizing_mode='fixed')

    def createPlot(self):
        p = figure(sizing_mode='stretch_both',
                   # plot_width=1000,
                   # plot_height=600,
                   title='RTOC-Web',
                   toolbar_location="above",
                   toolbar_sticky=False,
                   tooltips=TOOLTIPS,
                   x_axis_type="datetime",
                   # background_fill_color=DARK_GRAY,
                   # background_fill_alpha=1,
                   # border_fill_color=DARK_GRAY,
                   # outline_line_color=BROWN_GRAY,
                   tools="pan,wheel_zoom,zoom_in,zoom_out,save,crosshair,hover,box_zoom,reset")
        # tools="box_edit, box_select, box_zoom, click, crosshair, help, hover, lasso_select, pan, point_draw, poly_draw, poly_edit, poly_select, previewsave, redo, reset, save, tap, undo, wheel_zoom, xbox_select, xbox_zoom, xpan, xwheel_pan, xwheel_zoom, xzoom_in, xzoom_out, ybox_select, ybox_zoom, ypan, ywheel_pan, ywheel_zoom, yzoom_in, yzoom_out, zoom_in, zoom_out")

        # p.x_range.follow="end"
        #p.x_range.follow_interval = 2000
        # p.x_range.range_padding=0
        p.toolbar.active_scroll = p.select_one(WheelZoomTool)
        p.xaxis.axis_label = translate('Web', "Vergangene Zeit [s]")
        #p.yaxis.axis_label = "Messwert"
        return p

    def pausePlot(self, *args):
        if self.pauseButton.active:
            print('pausing')
            self.pauseButton.button_type = "danger"
        else:
            print('not pausing')
            self.pauseButton.button_type = "default"

    def setLegend(self):
        self.p.legend.location = "top_left"
        self.p.legend.click_policy = "mute"  # "hide"

    def connect(self, *args):
        if self.connectButton.active:
            pw = self.passwordInput.value
            if pw == '':
                pw = None
            ok = self.checkConnection(self.hostInput.value, self.passwordInput.value)
            if ok is True:
                self.connectButton.button_type = "success"
                self.updater = curdoc().add_periodic_callback(update, 500)
                self.connectButton.label = translate('Web', "Verbindung trennen")
            elif ok is False:
                self.connectButton.button_type = "danger"
                self.connectButton.label = translate('Web', "Verbindung fehlgeschlagen")
                #self.connectButton.active = True
            else:
                self.connectButton.button_type = "danger"
                self.connectButton.label = translate('Web', "Passwort falsch")
                #self.connectButton.active = True
        else:
            if self.updater:
                curdoc().remove_periodic_callback(self.updater)
                self.updater = None
            self.connectButton.button_type = "default"
            self.connectButton.label = translate('Web', "Verbinden")

    def addSignal(self, x=[0], y=[0], sname='NoName', dname='NoDevice', unit='', color='firebrick'):
        self.createNewLinePlot(self.createLoggerDataSource(x, y, sname, dname, unit), color)
        self.setLegend()

    def createLoggerDataSource(self, x, y, sname='NoName', dname='NoDevice', unit=''):
        source = ColumnDataSource(data={
            'name': [dname+"."+sname for i in x],
            'unit': [unit for i in x],
            'x': x,
            'y': y,
        })
        return source

    def createNewLinePlot(self, source, color='firebrick'):
        global signals
        r1 = self.p.line(x='x', y='y',
                         color=color,
                         line_width=2,
                         alpha=0.8,
                         muted_color=color,
                         muted_alpha=0.2,
                         legend=source.data['name'][0]+" ["+source.data['unit'][0]+"]",
                         source=source)
        signals.append(r1.data_source)

    def checkConnection(self, hostname, password):
        self.createTCPClient(hostname, password)
        # try:
        print("Trying to connect to "+hostname)
        ok = self.sendTCP()
        if ok != False and ok != None:
            ok = True
        # except:
        #     ok = False
        return ok


userpath = os.path.expanduser('~/.RTOC')
if not os.path.exists(userpath):
    os.mkdir(userpath)

if os.path.exists(userpath+"/rtoc_webhost.txt"):
    with open(userpath+"/rtoc_webhost.txt", 'r') as fh:
        host = fh.read()
else:
    host = HOST

rtoc_web = RTOC_Web(host)
