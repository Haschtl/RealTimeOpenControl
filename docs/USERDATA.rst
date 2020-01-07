***********
Userdata
***********

Document-Tree
========================================
User data is stored in the home directory of the current user
  - home/USER/.RTOC/ on linux
  - C:\\user\\USER\\ .RTOC\\ on windows

It contains the following files
::
  .RTOC
  ├── backup
  │   ├── localBackup1.json
  │   ├── ...
  ├── devices
  │   ├── Template
  │   ├──   ├── ...
  │   ├── ...
  ├── autorun_devices
  ├── config.json
  ├── globalActions.json
  ├── globalEvents.json
  ├── plotStyles.json
  ├── telegramActions.json
  ├── telegram_clients.json

backup (directory)
========================================
Used only, if backup is active and postgresql is not active. Currently this type of backup is not implemented.

devices (directory)
========================================
Place your plugins inside this folder! Each plugin must be in a folder, which should be named like the main-module of your plugin. For more information on how to make a plugin, click here: :doc:`PLUGINS`

autorun_devices
========================================
Write plugin-names in each line of this file. These plugins will start with RTOC automatically (make sure the plugin-Thread is started in your __init__).

config.json
========================================
This file contains all RTOC configurations. Its separated in different topics\:

global
++++++++++++++

=========================  =============  =========== =========================
Entry                      Default        Type        Information
=========================  =============  =========== =========================
language                   "en"           "en","de"   Selected language
recordLength               500000         int         Local recording limit
name                       "RTOC-Remote"  str         Name displayed in Telegram
documentfolder             "~/.RTOC"      str         ! Do not change !
globalActionsActivated     False          bool        Global actions (in-)active
globalEventsActivated      False          bool        Global events (in-)active
=========================  =============  =========== =========================

postgresql
++++++++++++++++

=========================  =============  =========== =========================
Entry                      Default        Type        Information
=========================  =============  =========== =========================
active                     False          bool        De/activate PostgreSQL database
user                       "postgres"     str         PostgreSQL Username
password                   ""             str         User's password
host                       "127.0.0.1"    str         Host of PostgreSQL-server
port                       5432           int         PostgreSQL port
database                   "postgres"     str         Name of PostgreSQL database
onlyPush                   True           bool        Only push data automatically, if backup active
=========================  =============  =========== =========================

GUI
++++++++++++++++

=========================  ==================  =========== =========================
Entry                      Default             Type        Information
=========================  ==================  =========== =========================
darkmode                   True                bool        De/activate darkmode (inactive)
scriptWidget               True                bool        Show/hide scriptWidget on startup
deviceWidget               True                bool        Show/hide deviceWidget on startup
deviceRAWWidget            True                bool        Show/hide deviceRAWWidget on startup
pluginsWidget              False               bool        Show/hide pluginsWidget on startup
eventWidget                True                bool        Show/hide eventWidget on startup
restoreWidgetPosition      False               bool        Save and restore window and widget positions
newSignalSymbols           True                bool        (inactive)
plotLabelsEnabled          True                bool        Show/hide signal-labels in graph
plotGridEnabled            True                bool        Show/hide grid in graph
showEvents                 True                bool        Show/hide events in graph
grid":                     [True, True, 1.0]   list        Grid configuration: [X-lines, Y-lines, linewidth]
plotLegendEnabled          False               bool        Show/hide legend in graph
blinkingIdentifier         False               bool        Show/hide blue blinking of signal-labels, when they are updated
plotRate                   8                   float       Updaterate of graph in Hz
plotInverted               False               bool        Invert plot (black-white/white-black)
xTimeBase                  True                bool        Plot x-axis values as difference from actual timestamp
timeAxis                   True                bool        Use time-ticks for x-axis
systemTray                 False               bool        Dis/enable close to systemTray
signalInactivityTimeout    2                   float       Time in seconds after Signal-Label turns yellow
autoShowGraph              False               bool        Automatically show new signals
antiAliasing               True                bool        Dis/Enable AntiAliasing
openGL                     True                bool        Dis/Enable OpenGL
useWeave                   True                bool        Dis/Enable Weave
csv_profiles               {}                  dict        Allocation of imported signals is stored here
=========================  ==================  =========== =========================

telegram
++++++++++++++++++++

=========================  =============  ======================================= =========================
Entry                      Default        Type        Information
=========================  =============  ======================================= =========================
active                     False          bool                                    De/activate telegram-bot
token                      ""             str                                     Your telegram bot-token
default_eventlevel         0              0,1 or 2                                Default eventlevel for new users
default_permission         'blocked'      'blocked','read', 'write' or 'admin'    Default user permissions for new users. First user is always admin!
inlineMenu                 False          bool                                    Make the telegram menu inline or in KeyboardMarkup
onlyAdmin                  False          bool                                    If True, only admins will be able to access the bot
=========================  =============  ======================================= =========================

websockets
++++++++++++++++++++

=========================  =============  =========== =========================
Entry                      Default        Type        Information
=========================  =============  =========== =========================
active                     False          bool        De/activate Websocket-server
port                       5050           int         Websocket-port
password                   ''             str         Optional password for Websocket-encryption (AES)
knownHosts                 {}             dict        Recent Websocket-hosts for remote connection are stored here
=========================  =============  =========== =========================

backup
++++++++++++++++++

=========================  ================  =========== =========================
Entry                      Default           Type        Information
=========================  ================  =========== =========================
active                     False             bool        De/activate backup-thread
path                       '~/.RTOC/backup'  str         Backup-directory (does not affect backup, if postgreSQL is active!)
clear                      False             bool        Automatically clear local data after backup
autoIfFull                 True              bool        Automatically backup, if local recordLength is reached
autoOnClose                True              bool        Automatically backup after closing RTOC
loadOnOpen                 True              bool        Automatically load data after starting RTOC (if False, signals are still shown to make sure that IDs are allocated correctly)
intervall                  240               float       Set backup-intervall in seconds
resample                   0                 float         If != 0, signals will be resampled with given samplerate before creating backup
=========================  ================  =========== =========================

globalActions.json
========================================
This file contains all global actions. Read more about the event/action system here: :ref:`Event/Action system`

globalEvents.json
========================================
This file contains all global events. Read more about the event/action system here: :ref:`Event/Action system`

plotStyles.json
========================================
This file contains all signal styles, which are used by the GUI. Delete it, to reset all signal styles.

telegramActions.json
========================================
Use this file to add main-menu-entries in the telegram-bot. More information here: :ref:`Telegram Custom-menu`

telegram_clients.json
========================================
Information about telegram-clients is stored here: ``clientID = {eventlevel = 0, shortcuts = [[],[]], first_name = "NAME", last_name = "NAME", permission = "admin", menu = "menu"}``
