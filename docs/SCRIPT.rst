*****************************
Controlling and automation
*****************************

Overview
===================================================
Own scripts can be used during the runtime:

- modify the measurement data
- Adjusting plugin parameters and calling functions
- Create new signals
- manual and automatic controlling, ...

In general, you write a Python script like any other, you can import libraries, etc. However, you should pay attention to performance.

RTOC provides an own library for scripts: :mod:`.RTLogger.scriptLibrary`

There are three places, where custom scripting is possible.

- :ref:`Run scripts in GUI`
- Telegram-menu-entries: :doc:`TELEGRAM`
- :ref:`Event/Action system`

Available functions and libraries
======================================

Python libraries
----------------------

There are several python libraries automatically imported in scripts

.. code-block:: python

  import math
  import numpy as np
  import sys
  import scipy as sp
  from .RTLogger import scriptLibrary as rtoc

Functions to interact with RTOC
--------------------------------------------
.. automethod:: RTOC.LoggerPlugin.LoggerPlugin.stream
  :noindex:
.. automethod:: RTOC.LoggerPlugin.LoggerPlugin.plot
  :noindex:
.. automethod:: RTOC.RTLogger.RTLogger.RTLogger.exportData
  :noindex:
.. automethod:: RTOC.RTLogger.RT_data.RT_data.clear
  :noindex:

Access to plugin parameters and signals in scripts
------------------------------------------------------------------
All signals can be references in scripts in these ways

.. code-block:: python

  [x],[y] = Device.Signalname
  [x] = Device.Signalname.x
  [y] = Device.Signalname.y
  c = Device.Signalname.latest

plugin parameters and functions can be accessed in this way

.. code-block:: python

  Device.FUNCTION(...)
  Device.PARAMETER = ...

Access to telegram functions
------------------------------------------------------------------
You can send messages, pictures, files and graphs with the following functions. (e.g. ``telegram.send_message_to_all('Hi')``):

.. automethod:: RTOC.RTLogger.telegramBot.telegramBot.send_message_to_all
  :noindex:
.. automethod:: RTOC.RTLogger.telegramBot.telegramBot.send_photo
  :noindex:
.. automethod:: RTOC.RTLogger.telegramBot.telegramBot.send_document
  :noindex:
.. automethod:: RTOC.RTLogger.telegramBot.telegramBot.send_plot
  :noindex:


Special stuff
----------------------
The actual timestamp is available in the global variable ``clock``.
You can use the default ``print()`` function for text-output in console, GUI and telegram.

You can define variables **global**. This ensures, this variable will remain until the next call of this script. Example

.. code-block:: python

  global VARNAME = 0

If-else conditions aren't always suitable for real-time operations. You cannot trigger rising/falling for example. Therefore you can use a trigger to call the code inside a condition only once

.. code-block:: python

  trig CONDITION:
    print('Hello')

This example will only print 'Hello', if CONDITION changes from ``False`` to ``True``.

RTOC library
----------------------

.. automodule:: RTOC.RTLogger.scriptLibrary
    :members:
    :undoc-members:
    :show-inheritance:
    :noindex:

Event/Action system
============================
The Event/Action System allows Python code to be executed when events occur. These pieces of code have the same possibilities as scripts.

Global actions
----------------
Global actions are stored in the file :ref:`globalActions.json`.

Example

.. code-block:: python

  {
    "action2": {
      "listenID": ["testID"],
      "parameters": "",
      "script": "Generator.gen_level = 1",
      "active": False

    }

  }

This JSON-file contains dicts - each describing one action.

===============   =================== =========================================================
Parameter         Datatype            Definition
===============   =================== =========================================================
``listenID``      ``list``            The event-IDs of events, which will trigger this action
``parameters``    ``str``             Unused
``script``        ``str``             The script, which will be executed
``active``        ``bool``            If True, this action will be active
===============   =================== =========================================================

Global events
---------------------
Global events are stored in the file :ref:`globalEvents.json` unlike events created in plugins.

Example

.. code-block:: python

  {
    "myevent": {
      "cond": "Generator.Square.latest >= 2",
      "text": "It is big",
      "return": " ",
      "priority": 0,
      "id": "testID",
      'trigger': 'rising',
      'sname': '',
      'dname': '',
      'active': True

    }

  }

This JSON-file contains dicts - each describing one event.

===============   =================== =========================================================
Parameter         Datatype            Definition
===============   =================== =========================================================
``cond``          ``str``             The condition triggering the event.
``trigger``        ``str``            Change trigger-mode. ``rising``, ``falling``, ``both``,``true``, ``false``. If ``rising``, the event will be triggered if cond changes from ``False`` to ``True``. If ``falling``, the other way around. ``both`` for rising and falling. ``true`` for always, if condition is true. ``false`` for always, if condition is false.
``active``        ``bool``            If True, this event will be active.
``id``            ``str``             The event-ID used to trigger actions.
``return``        ``str``             Unused
``text``          ``str``             See :py:meth:`.LoggerPlugin.event`
``dname``         ``str``             ...
``sname``         ``str``
``priority``      ``0,1 or 2``
===============   =================== =========================================================

**Global actions and events can also be configured during runtime in the telegram-bot.**
