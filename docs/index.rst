Welcome to RealTime OpenControl's documentation!
================================================
RealTime OpenControl (RTOC) is a free software for recording measurement data of various measuring instruments. It offers the following components

- RTLogger backend, which connects all parts (but the GUI) together. More information here: :ref:`Code documentation`
- Writing own plugins for all types of devices. More information here: :doc:`PLUGINS`
- TelegramBot to access RTLogger from any device with `Telegram <https://www.telegram.com>`_. More information here: :doc:`/TELEGRAM`

- TCP-server to access RTLogger from other processes or devices. More information here: :doc:`/TCP`

- Webserver to view data from RTLogger or postgreSQL database. More information here: :doc:`/WEBSERVER`
- RTOC-GUI to access and RTLogger. More information here :ref:`GUI documentation`.
- Scripting/Automation with scripts and event/action systtem. More information here: :doc:`/SCRIPT`

Getting started
================================================

Installation
--------------

Installing with Python3 (recommended)
++++++++++++++++++++++++++++++++++++++++++++++++++

RTOC is available in the Python package manager PIP::

  pip3 install RTOC


This will download the basic RTOC without the dependencies needed for the GUI, Telegram and the Webserver. The default RTOC setup is suitable for running RTOC on embedded devices.

There are also different variations available to install::

  pip3 install RTOC[Webserver]   # Includes all packages for webserver
  pip3 install RTOC[GUI]         # Includes all packages for GUI
  pip3 install RTOC[Telegram]    # Includes all packages for Telegram
  pip3 install RTOC[ALL]         # Includes all packages

Installing from builds
++++++++++++++++++++++++++++++++++++++++++++++++++

Download the latest release builds for Windows (soon also Linux) `here <https://github.com/Haschtl/RealTimeOpenControl/releases>`_.

Extract the .zip file into a directory. RTOC is started by double-clicking on "RTOC.exe". Alternatively via command line::

  // local RTOC-instance including GUI
  ./RTOC

Install manually
++++++++++++++++++++++++++++++++++++++++++++++++++

To use the basic RTOC, the following dependencies must be installed::

  pip3 install numpy pycryptodomex requests python-nmap whaaaaat prompt_toolkit psycopg2


If you want to use the GUI you must also install the following packages::

  pip3 install pyqt5 pyqtgraph markdown2 xlsxwriter scipy pandas ezodf pyGithub


If you want full functionality, then you still need the following packages (for telegram bot and webserver)::

  pip3 install python-telegram-bot matplotlib dash gevent dash_daq dash_table plotly flask


You can use different stylesheets for the GUI if you want. Just install one of these with pip:
'QDarkStyle', 'qtmodern', 'qdarkgraystyle'.


The RTOC repository can then be cloned with::

  git clone git@github.com:Haschtl/RealTimeOpenControl.git


Tips for embedded applications or long-time measurements
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
If you want to store measurements for a long period of time, I would recommend to use RTOC with a postgreSQL database. Therefore you need to setup postgreSQL on your system and change the postgresql parameters in your :ref:`config.json` file.

**Setup postgreSQL on linux**

1. Open a terminal window
2. Issue the command ``sudo apt install postgresql``
3. Follow the instructions to change the default postgresql-password.
4. Add a new user and create a database (google for that)
5. Enter your postgresql username, port, database and password in your :ref:`config.json` file.


**Setup postgreSQL on windows**

2. Download postgresql one-click installer from `this website <https://www.enterprisedb.com/downloads/postgres-postgresql-downloads#windows>`_
3. Double click on the downloaded file and follow the setup instructions.
4. Add a new user and create a database (google for that)
5. Enter your postgresql username, port, database and password in your :ref:`config.json` file.

First run
++++++++++++++++++++++++++++++++++++++++++++++++++
After installing RTOC, you can run it with::

  // local RTOC-instance including GUI
  python3 -m RTOC

  // local RTOC-instance without GUI (only TCP-Server, [HTTP-Server, Telegram-Bot])
  // I would recommend starting RTOC as a service and not to use this.
  python3 -m RTOC.RTLogger -s start/stop

  // local RTOC-Configuration from Console
  python3 -m RTOC.RTLogger -c

  // local RTOC-Webserver at port 8050
  python3 -m RTOC.RTLogger -w

  // remote RTOC-instance with GUI
  python3 -m RTOC -r <ADRESS>

  // explicit local RTOC GUI (even if database is enabled) 
  python3 -m RTOC -l

Writing your first plugin
---------------------------------------
Have a look at the plugin-documentation: :doc:`PLUGINS`


GUI documentation
================================================
You can use the GUI to control your plugins, manipulate your measurements, try scripts, import data and configure your settings.
You can also view and control RTOC-servers remotely. Unfortunately this is limited to short recordings due to the TCP-protocol, which cannot handle long datasizes. This will maybe be fixed in future releases.

For more information about the GUI, read the GUI documentation: :doc:`/GUI`

The GUI-Code is mostly undocumented, but you can take a look inside here: :doc:`RTOC`


Userdata
================================================
User data is stored in the home directory of the current user
  - home/USER/.RTOC/ on linux
  - C:\user\USER\.RTOC\ on windows

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

backup (directory)
------------------
Used only, if backup is active and postgresql is not active. Currently this type of backup is not implemented.

devices (directory)
-------------------
Place your plugins inside this folder! Each plugin must be in a folder, which should be named like the main-module of your plugin. For more information on how to make a plugin, click here: :doc:`PLUGINS`

autorun_devices
---------------
Write plugin-names in each line of this file. These plugins will start with RTOC automatically (make sure the plugin-Thread is started in your __init__).

config.json
-----------
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
webserver_port             8050           int         Port of webserver (disabled)
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

=========================  =============  =========== =========================
Entry                      Default        Type        Information
=========================  =============  =========== =========================
active                     False          bool        De/activate telegram-bot
token                      ""             str         Your telegram bot-token
eventlevel                 0              0,1 or 2    Default eventlevel for new users
chat_ids                   {}             dict        Information about telegram-clients is stored here
inlineMenu                 False          bool        Make the telegram menu inline or in KeyboardMarkup
=========================  =============  =========== =========================

tcp
++++++++++++++++++++

=========================  =============  =========== =========================
Entry                      Default        Type        Information
=========================  =============  =========== =========================
active                     False          bool        De/activate TCP-server
port                       5050           int         TCP-port
password                   ''             str         Optional password for TCP-encryption (AES)
knownHosts                 {}             dict        Recent TCP-hosts for remote connection are stored here
remoteRefreshRate          1              float       Refresh-rate for remote session
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
=========================  ================  =========== =========================

globalActions.json
------------------
This file contains all global actions. Read more about the event/action system here: :ref:`Event/Action system`

globalEvents.json
-----------------
This file contains all global events. Read more about the event/action system here: :ref:`Event/Action system`

plotStyles.json
---------------
This file contains all signal styles, which are used by the GUI. Delete it, to reset all signal styles.

telegramActions.json
--------------------
Use this file to add main-menu-entries in the telegram-bot. More information here: :ref:`Telegram Custom-menu`



Code documentation
================================================
.. toctree::
   :maxdepth: 5

   RTOC.RTLogger


FAQ
================================================
- How can I get plugins from the community? :ref:`Plugin repository`
- How do I import new data from CSV, Wave, Excel, ODF, Matlab? :ref:`Import/Export signals/sessions`
- How do I connect a new plugin? :doc:`PLUGINS`
- How do I create a sub-GUI for a device? :ref:`Writing Plugins`
- How do I create my first script? :doc:`SCRIPT`
- What does the trigger mean? :ref:`Trigger-System`
- RTOC library and default functions for scripts: :mod:`RTOC.RTLogger.scriptLibrary`
- Can I access the data from any device? :doc:`TELEGRAM` or :doc:`TCP`
- How do I use the graphical user interface? :doc:`GUI`
- How do I create a telegram bot? :ref:`Telegram-Bot setup`
- How do I control an RTOC server via TCP in the network? :ref:`Remote-control via TCP`
- Where can I find examples for plugins? `RTOC repository <https://github.com/Haschtl/RTOC-Plugins>`_


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Full Content table
=============================
.. toctree::
   :maxdepth: 5

   RTOC
   RTOC.RTLogger
   PLUGINS
   GUI
   SCRIPT
   TCP
   TELEGRAM
   WEBSERVER
