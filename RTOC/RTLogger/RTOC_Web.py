# -*- coding: utf-8 -*-
"""
This is executed with `python3 -m RTOC.RTLogger -w`, if postgresql is not active

This code is not documented. Read the Webserver documentation for more information: :doc:`WEBSERVER`

"""
import dash
import dash_html_components as html
import dash_core_components as dcc
import dash_table
import plotly

from dash.dependencies import Input, Output, State
import time
import datetime
import logging as log
from gevent.pywsgi import WSGIServer
from flask import Flask
# import datetime
# from threading import Thread
# import json
# import pandas as pd
# import numpy as np
# import plotly.plotly as py
# import plotly.graph_objs as go
# import flask
# import os
log.basicConfig(level=log.WARNING)
logging = log.getLogger(__name__)
# pip3 install dash dash-core-components==0.39.0rc4
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

server = Flask(__name__)
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, sharing=True,
                server=server, url_base_pathname='/', csrf_protect=False)
app.config['suppress_callback_exceptions'] = True
#server = app.server

eventTableTitle = ['Zeitpunkt', 'Typ', 'Gerät', 'Signal', 'Inhalt', 'ID', 'Rückgabewert']
from .RTLogger import RTLogger

# @server.route('/favicon.ico')
# def favicon():
#     print(server.root_path)
#     return flask.send_from_directory(server.root_path,
#                                      'favicon.ico')


app.layout = html.Div([
    dcc.Tabs(id="tabs", children=[
        dcc.Tab(label='Signale', children=[
            html.Div([
                dcc.Checklist(
                    id='activeCheck',
                    options=[
                        {'label': 'Plot aktiv', 'value': 'PLOT'},
                    ],
                    values=['PLOT']
                ),
                dcc.Dropdown(
                    id='signal_dropdown',
                    options=[],
                    searchable=True,
                    clearable=True,
                    placeholder="Wähle Signale aus, um sie darzustellen.",
                    multi=True,
                    # value=""
                ),
                dcc.Graph(id='live-update-graph'),  # , style={'height': '100vh'},),
                dcc.Interval(
                    id='interval-component',
                    interval=1*1000,  # in milliseconds
                    n_intervals=0
                )
            ],
                id='signals_div')
        ]),
        dcc.Tab(label='Mitteilungen', children=[
                dash_table.DataTable(
                    id='datatable-interactivity',
                    columns=[{"name": i, "id": i} for i in eventTableTitle],
                    editable=False,
                    filtering=True,
                    sorting=True,
                    # sorting_type="multi",
                    # row_selectable="multi",
                    # row_deletable=False,
                    # selected_rows=[],
                    pagination_mode="fe",
                    pagination_settings={
                        "displayed_pages": 1,
                        "current_page": 0,
                        "page_size": 35,
                    },
                    navigation="page",
                ),
                dcc.Interval(
                    id='interval-component2',
                    interval=1*1000,  # in milliseconds
                    n_intervals=0
                ),
                html.Div(id='datatable-interactivity-container',
                         style={'height': '100vh'},)
                ]),
    ]),
])

signals = [
    [[1, 2, 3, 4, 5], [4, 3, 2, 6, 7], 'E.Temperatur', '°C'],
    [[1, 2, 3, 4, 5], [4, 3, 2, 6, 7], 'E.Feuchtigkeit', '%'],
    [[1, 2, 3, 4, 5], [4, 3, 2, 6, 7], 'E.Temperatur3', '°C'],
    [[1, 2, 3, 4, 5], [4, 3, 2, 6, 7], 'E.CO2', 'ppm'],
    [[1, 2, 3, 4, 5], [4, 3, 2, 6, 7], 'E.Temperatur2', '°C'],
]
events = [['heute', 'Warnung', 'E', 'Temperatur', 'Temperatur zu hoch', '34666', '3']]

lastSignals = []


run = False
samplerate = 1


logger = RTLogger(True)
if logger is None:
    logging.warning('No logger connected to RTOC_Web')
    app.title = 'RTOC-Web'
else:
    app.title = logger.config['global']['name']


def start(debug=False):
    global run
    #global logger
    run = True
    try:
        print('Starting webserver')
        # app.run_server(debug=debug)
        #from yourapplication import app
        try:
            port = logger.config['global']['webserver_port']
        except:
            port = 8050
        http_server = WSGIServer(('0.0.0.0', port), app.server)
        http_server.serve_forever()
    except KeyboardInterrupt:
        run = False
        logger.stop()
        logging.info('Server killed by user.')
    except Exception:
        logging.error('Webserver crashed!')


def stop():
    global run
    if run:
        run = False
    else:
        logging.warning('HTML-Server was not started. Could not stop')


def updateT():
    global events
    global signals
    diff = 0
    while run:
        if diff < 1/samplerate:
            time.sleep(1/samplerate-diff)
        start_time = time.time()
        new_signals = []
        for sigID in logger.database.signals().keys():
            signal = logger.database.signals()[sigID]
            name = logger.database.getSignalName(sigID)
            unit = logger.database.signals()[sigID][4]
            if len(signal(id)[0]) > 0:
                x = list(signal[0])
                y = list(signal[1])
                signame = '.'.join(name)
                new_signals.append([x, y, signame, unit])
        signals = new_signals
        diff = (time.time() - start_time)

# Multiple components can update everytime interval gets fired.


@app.callback(
    dash.dependencies.Output('signal_dropdown', 'options'),
    [dash.dependencies.Input('interval-component', 'n_intervals')]
)
def update_date_dropdown(n_intervals):
    global logger
    new_signals = []
    for sigID in logger.database.signals().keys():
        signal = logger.database.signals()[sigID]
        name = logger.database.getSignalName(sigID)
        unit = logger.database.signals()[sigID][4]
        if len(signal[2]) > 0:
            x = list(signal[2])
            y = list(signal[3])
            signame = '.'.join(name)
            new_signals.append([x, y, signame, unit])
    signals = new_signals
    return [{'label': i[2], 'value': i[2]} for i in signals]


last_now = time.time()


@app.callback(Output('live-update-graph', 'figure'),
              [Input('interval-component', 'n_intervals')],  # Input('activeCheck', 'values')],
              state=[State('live-update-graph', 'figure'), State('activeCheck', 'values'),
                     State('live-update-graph', 'relayoutData'),  State('signal_dropdown', 'value')]
              )
def update_graph_live(n_intervals, lastPlot, active, relayout_data, selection):
    global lastSignals
    global logger
    global last_now
    if active == ['PLOT']:
        now = time.time()
        last_now = now
    else:
        now = last_now
    new_signals = []
    for sigID in logger.database.signals().keys():
        signal = logger.database.signals()[sigID]
        name = logger.database.getSignalName(sigID)
        unit = logger.database.signals()[sigID][4]
        if len(signal[0]) > 0:
            x = [i-now for i in list(signal[2])]
            y = list(signal[3])
            signame = '.'.join(name)
            new_signals.append([x, y, signame, unit])
    signals = new_signals
    sorted = {}
    units = []
    if selection is None:
        selection = []
    if active == ['PLOT']:
        sig = signals
        lastSignals = signals
    else:
        sig = lastSignals
    for signal in sig:
        if signal[2] in selection:
            if signal[3] not in sorted.keys():
                sorted[signal[3]] = []
            sorted[signal[3]].append(signal[0:3])
    # Create the graph with subplots
    if len(sorted) == 0:
        greater1 = 1
    else:
        greater1 = len(sorted)
    # subplot_titles=tuple(sorted.keys()))
    fig = plotly.tools.make_subplots(rows=greater1, cols=1, vertical_spacing=0.2,)
    fig['layout']['margin'] = {
        'l': 30, 'r': 10, 'b': 30, 't': 10
    }
    fig['layout']['legend'] = {'x': 0, 'y': 1, 'xanchor': 'left'}
    # print(sorted)

    for idx, unit in enumerate(sorted.keys()):
        for signal in sorted[unit]:
            fig.append_trace({
                'x': signal[0],
                'y': signal[1],
                'name': signal[2]+' ['+unit+']',
                'mode': 'lines+markers',
                'type': 'scatter'
            }, idx+1, 1)
        fig['layout']['yaxis'+str(idx+1)].update(title='['+unit+']', showgrid=True)
        fig['layout']['xaxis'+str(idx+1)].update(title='Vergangene Zeit [s]', showgrid=True)
        if relayout_data:
            if 'xaxis'+str(idx+1)+'.range[0]' in relayout_data:
                fig['layout']['xaxis'+str(idx+1)]['range'] = [
                    relayout_data['xaxis'+str(idx+1)+'.range[0]'],
                    relayout_data['xaxis'+str(idx+1)+'.range[1]']
                ]
            if 'yaxis'+str(idx+1)+'.range[0]' in relayout_data:
                fig['layout']['yaxis'+str(idx+1)]['range'] = [
                    relayout_data['yaxis'+str(idx+1)+'.range[0]'],
                    relayout_data['yaxis'+str(idx+1)+'.range[1]']
                ]
        if idx == 0:
            fig['layout']['yaxis'].update(title='['+unit+']', showgrid=True)
            fig['layout']['xaxis'].update(title='Vergangene Zeit [s]', showgrid=True)
            if relayout_data:
                if 'xaxis.range[0]' in relayout_data:
                    fig['layout']['xaxis']['range'] = [
                        relayout_data['xaxis.range[0]'],
                        relayout_data['xaxis.range[1]']
                    ]
                if 'yaxis.range[0]' in relayout_data:
                    fig['layout']['yaxis']['range'] = [
                        relayout_data['yaxis.range[0]'],
                        relayout_data['yaxis.range[1]']
                    ]
    return fig


# @app.callback(Output('datatable-interactivity-container', 'children'))
# def display_output():
#     return html.Div([
#         html.Div(id='datatable-output'),
#         dash_table.DataTable(
#             id='datatable',
#             columns=[{'Column 1': i} for i in range(5)]
#         )
#     ])

@app.callback(
    Output('datatable-interactivity', 'data'),
    [Input('interval-component2', 'n_intervals')],)
def update_output(n_intervals):
    data = []
    for evID in logger.database.events().keys():
        event = logger.database.events()[evID] # [devID, sigID, eventid, text, x, value, priority]
        name = logger.database.getEventName(evID)

        event_dict = {}
        # event_dict[eventTableTitle[0]]=time.strftime("%d.%m %H:%M:%S", time.gmtime(int(events[0][idx])))
        event_dict[eventTableTitle[0]] = datetime.datetime.fromtimestamp(
            event[4]).strftime('%Y-%m-%d %H:%M:%S:%f')
        if event[6] == 0:
            text = "Information"
        elif event[6] == 1:
            text = "Warnung"
        else:
            text = "Fehler"
        event_dict[eventTableTitle[1]] = text # ['Zeitpunkt', 'Typ', 'Gerät', 'Signal', 'Inhalt', 'ID', 'Rückgabewert']
        event_dict[eventTableTitle[2]] = name[0]
        event_dict[eventTableTitle[3]] = name[1]
        event_dict[eventTableTitle[4]] = event[3]
        event_dict[eventTableTitle[6]] = event[2]
        event_dict[eventTableTitle[5]] = event[5]
        data.append(event_dict)


# start(debug=True)
# if __name__ == '__main__':
#     try:
#         start(debug=True)
#     except KeyboardInterrupt:
#         stop()
