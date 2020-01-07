*****************************
Websocket Communication
*****************************

**Websocket Port: 5050, SSL: 443 **


The content is formatted as a JSON file (Python: dict) with the following keys (all optional). For more information: :py:mod:`.RTLogger.NetworkFunctions`

==================================================================   ============================================================
dict-key                                                             Description
==================================================================   ============================================================
 ``authorize = "hashed_password"                                       You must always send this command in the beginning (If not password-protected: authorize=True)
 ``plot = False``                                                      ``True``: x and y data are plotted as one signal. ``False``: x and y data are signals in pairs. See :py:meth:`.LoggerPlugin.plot` for more information.

 ``x = [0,1,2,3,4,5]``                                                 X data to be sent. If ``x`` is not set and ``plot = False``, ``time.time()`` is set as x-value. If ``plot = True``, the indices of the ``y`` data are used. See :py:meth:`.LoggerPlugin.plot` for more information.
 ``y = [1,2,3,4,5,6]``                                                 Y-data to be sent. See :py:meth:`.LoggerPlugin.plot` for more information.
 ``sname = ["signalname"]``                                            List of signal names with ``plot = False``, only one element with ``plot = True``. See :py:meth:`.LoggerPlugin.plot` for more information.
 ``dname = "devicename"``                                              Device name to be transmitted. See :py:meth:`.LoggerPlugin.plot` for more information.
 ``unit = "unit"``                                                     signal unit. See :py:meth:`.LoggerPlugin.plot` for more information.

 ``event = {text = "", dname='', sname='', x=clock, priority=0}``      Create an event. See :py:meth:`.LoggerPlugin.event` for more information.

 ``getLatest= True``                                                   If ``getLatest=True``, RTOC returns a Dict of the most current measured values. The signal names are the keys. See :py:meth:`.NetworkFunctions.getLatest` for more information.
 ``getSignalList = True``                                              If ``getSignalList=True``, RTOC returns a list of signal names. See :py:meth:`.NetworkFunctions.getSignalList` for more information.
 ``getEventList = True``                                               If ``getEventList=True``, RTOC returns a list of all events. See :py:meth:`.NetworkFunctions.getEventList` for more information.
 ``getPluginList = True``                                              If ``getPluginList =True``, RTOC returns a Dict of the plugins containing the plugin functions, parameters and the status of the plugin. See :py:meth:`.NetworkFunctions.getPluginList` for more information.
 ``getEvent = ['Device.Signal',...]``                                  Server request for the events of a signal. See :py:meth:`.NetworkFunctions.getEvent` for more information.
 ``getSignal = ['Device.Signal',...]``                                 Server request for signal data. See :py:meth:`.NetworkFunctions.getSignal` for more information.
 ``getSession = True``  

  ``remove = ['signal', 'DEVICE.SIGNAL']``  

 ``subscribe = ['signal', 'DEVICE.SIGNAL']``  
 ``unsubscribe = ['signal', 'DEVICE.SIGNAL']``  
 ``subscribeAll = True``  
 ``unsubscribeAll = True``  

 ``plugin = {...}``                                                    Access to plugins with Dict. See :py:meth:`.NetworkFunctions.handleTcpPlugins` for more information.
 ``logger = {...}``                                                    RTOC default functions. See :py:meth:`./RTLogger/RTWebsocketServer` for more information.
 ``userAction = {...}``
 ``automation = {...}``
==================================================================   ============================================================

As response RTOC delivers a dict with the following keys\:

===================  ================================================================
dict-key             Description
===================  ================================================================
`error = False`      If True, an error has occurred in the transmission
`sent = False`       Is True if data (x,y) has been transmitted to the server.
`signalList = []`    Contains list of devices, at getSignalList-Request
`pluginList= {}`     Dict with plugins, with getPluginList-Request
`signals = {}`       Dict with signals, with getSignal-Request
`events = {}`        Dict with events, at getEvent-Request
`latest = {}`        Dict with latest measured values, at getLatest-Request
`userAction = {}`
`automation = {}`
`logger = {}`
`plugin = {}`
`remove = {}`
`getSession = {}`
===================  ================================================================

Python example (With :py:mod:`./RTLogger/RTWebsocketClient`)
------------------------------------------------------

This example uses the module :py:mod:`./RTLogger/RTWebsocketClient`::

  import RTWebsocketClient

  data = {'x':[0,1,2,3],'y':[1,2,3,4],'dname':'Test','sname':['T1','T2','T3','T4']}
  sock = RTWebsocketClient.RTWebsocketClient()
  sock.on_message = lambda msg: print(msg)
  sock.connect('127.0.0.1', 5050)
  sock.send(data)
  input('Press enter to quit')
  sock.close()


Have a look into the RTWebsocketClient-File to see, which websocket-callbacks are available.