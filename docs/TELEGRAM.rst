****************************
Telegram Communication
****************************

Telegram-Bot setup
=============================

Create a new Telegram-Bot
-----------------------------
- Telegram must be installed on Smartphone/PC,...
- Open the following website: `https://telegram.me/BotFather <https://telegram.me/BotFather>`_
- Click on 'SEND MESSAGE' (Telegram should open and create a new contact 'BotFather')
- Create a new bot with the command '/newbot
- Enter a name for the bot
- Enter a username for the bot
- You will receive a token which has to be entered in RTOC (looks like this: 123456789:AABBAABB66AA11_uGG22GH44AA55_3)

Configure RTOC for Telegram
-----------------------------
You can eather configure it in the settings of the RTOC GUI or edit the :ref:`config.json` file by yourself. Enter your Bot-Token there and activate it  (``active=True``).

User permissions
-----------------------------
By default any new client connected to this bot will have no permissions. You can change the default behavior in :ref:`config.json`.

The first client connected to the bot will automatically be admin. The admin has the permission to change the permissions of all users.

- **blocked**: No permissions at all
- **custom**: Can only call user-specifig shortcuts, cannot receive event-notifications
- **read**: Can receive event-notifications and plot signals
- **write**: Can create global Events/Actions, send Events/Signals, access devices
- **admin**: Full permissions. Can delete signals, access settings menu

.. image:: ../screenshots/telegramBot.png

Custom permission
+++++++++++++++++++++++
The custom permission has a special role. A user with 'custom' permission will not receive notifications for events and will only see shortcuts, created for this user. Thereby you can provide a very simple bot to users, which will only be able to call selected functions or modify parameters. For example a bot with only two buttons to control the heating in the livingroom: 'Set Temperature' and 'Enable/Disable'


Mainmenu
==================

- <CUSTOM_ACTIONS> [**read**,**write**,**admin**]
- <USER SHORTCUTS> [**custom**,**write**,**admin**]
- Latest values [**read**,**write**,**admin**]
- Signals [**read**,**write**,**admin**]
- Devices [**write**,**admin**]
- Send event/signal [**write**,**admin**]
- Automation [**write**,**admin**]
- Settings [**read**,**admin**, **write**]
  - Set Event Notification  [**read**,**write**,**admin**]
  - General [**admin**, **write**]
  - Telegram-Bot [**admin**]
  - Backup [**admin**]

Latest values
-----------------------------

Displays the most current measured value of each signal.

Signals
-----------------------------

Contains a list of all signals. Clicking on a signal will select this signal. You can also select the time-period with ``Select period``. ``Generate plot`` will send you a plot with your selected signals in the selected period of time.

``Show/Hide events`` will show/hide events in the plot. Events are displayed as vertical lines with the event-text

``Delete signals`` [**admin**] will delete all selected data (signals and time-period).

``Delete events`` [**admin**] will delete all selected events (time-period).

Devices
-----------------------------

Contains a list of all devices/plugins found on the RTOc server (see submenu: Device).
  Device
  - Start/stop device
  - Functions: List of all device functions. Execute by click
  - Parameters: List of all device parameters: Edit by click
  - Change samplerate
  - *Info: You can create main-menu-shortcuts for functions and parameters*

Send event/signal
-----------------------------

Create a new event with Telegram. You can send measurements, which your doing manually, too.

Automation
-----------------------------

Editor for :ref:`Event/Action system`.

Settings
-----------------------------

Set Event Notification
++++++++++++++++++++++++

Telegram-Notifications can be received from the RTOC-server if events occur. The notification level can be set here. (Averages, Warnings, Errors)

General
++++++++++++++++++++++

- Change recording length: Change the local recording length of the server.
- Change global samplerate: Change the samplerate of all plugins using ``self.samplerate`` or ``self.setPerpetualTimer(func,samplerate)``.
- TCP-Server: On/Off: En/disable TCP-server
- Restart server: Restart host computer

TelegramBot
++++++++++++++++++++++

- Telegram bot appeareance: You can switch between the inlinekeyboard-button style and chat style
- OnlyAdmin - mode: If enabled, only admins have access to the bot.
- Previews: Admins can preview the different permissions to check them.
- Telegram clients: List of connected clients. Admins can change user-permissions.

Backup-Settings
++++++++++++++++++++++

- Configure all backup options.
- Delete signals: Deletes all signals and events.
- Resample database

Telegram Custom-menu
===========================
The file :ref:`telegramActions.json` contains dicts with actions, that will be shown in the main menu and can be executed by any user. If the action-name (key) starts with '_' only admins will be able to see this button.

Here is an example to send a screenshot

.. code-block:: python

  {
	 "Screenshot": """

      import pyscreenshot as ImageGrab
      dir = self.config['global']['documentfolder']
      im = ImageGrab.grab()\nim.save(dir+'/telegram_overview.png')
      return 'picture', dir+'/telegram_overview.png'
      """

  }

A telegram action must return either a text, a picture or any other file.

``return 'text', 'My example text'`` to return a text message.

``return 'picture', <dir/to/picture.jpg>`` to return a picture.

``return 'document', <dir/to/file>`` to return any other file.

User Shortcuts
===========================
Any Telegram client can define his own shortcuts to plugin-functions and parameters. These shortcuts will be displayed in the main menu.

To define a new shortcut, you can either modify the shortcuts manually in the :ref:`telegram_clients.json` file.

Clients with 'write' or 'admin' permission can create shortcuts right in the Telegram bot. You can press the 'Create shortcut' button in every plugin-parameter or function submenu.

**Important: ** Every telegram function (telegram_send_message,...) inside a plugin-function will send the message, file or image only to the client, who called the shortcut.
