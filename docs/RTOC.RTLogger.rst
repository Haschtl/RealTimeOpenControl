********************************
Backend Source-code
********************************

LoggerPlugin.py
====================

This class is imported by any plugin written for RTOC.

It includes all functions to interact with RTOC. Every plugin must inherit this class! Your plugin must look like this

.. code-block:: python

  ::

      from RTOC.LoggerPlugin import LoggerPlugin

      class Plugin(LoggerPlugin):
          def __init__(self, *args, **kwargs):
              LoggerPlugin.__init__(self, *args, **kwargs)
              ...
          ...

If you need to pass arguments to your class initialization, use kwargs. ('stream', 'plot', 'event', 'telegramBot' cannot be used as kwarg-name)

.. automodule:: RTOC.LoggerPlugin
    :members:
    :undoc-members:
    :show-inheritance:
    :noindex:

jsonsocket.py
====================
.. automodule:: RTOC.jsonsocket
    :members:
    :undoc-members:
    :show-inheritance:
    :noindex:


RTOC.RTLogger Submodules
========================

..
  RTOC.RTLogger.Console module
  ----------------------------

  .. comment automodule:: RTOC.RTLogger.Console
  ..    :members:
  ..    :undoc-members:
  ..    :show-inheritance:

RTOC.RTLogger.Daemon module
---------------------------

.. automodule:: RTOC.RTLogger.Daemon
    :members:
    :undoc-members:
    :show-inheritance:

RTOC.RTLogger.DeviceFunctions module
------------------------------------

.. automodule:: RTOC.RTLogger.DeviceFunctions
    :members:
    :undoc-members:
    :show-inheritance:

RTOC.RTLogger.EventActionFunctions module
-----------------------------------------

.. automodule:: RTOC.RTLogger.EventActionFunctions
    :members:
    :undoc-members:
    :show-inheritance:

RTOC.RTLogger.NetworkFunctions module
-------------------------------------

.. automodule:: RTOC.RTLogger.NetworkFunctions
    :members:
    :undoc-members:
    :show-inheritance:

RTOC.RTLogger.RTLogger module
-----------------------------

.. automodule:: RTOC.RTLogger.RTLogger
    :members:
    :undoc-members:
    :show-inheritance:

RTOC.RTLogger.RTOC\_Web module
------------------------------

.. automodule:: RTOC.RTLogger.RTOC_Web
    :members:
    :undoc-members:
    :show-inheritance:

RTOC.RTLogger.RTOC\_Web\_standalone module
------------------------------------------

.. automodule:: RTOC.RTLogger.RTOC_Web_standalone
    :members:
    :undoc-members:
    :show-inheritance:

RTOC.RTLogger.RTRemote module
-----------------------------

.. automodule:: RTOC.RTLogger.RTRemote
    :members:
    :undoc-members:
    :show-inheritance:

RTOC.RTLogger.RT\_data module
-----------------------------

.. automodule:: RTOC.RTLogger.RT_data
    :members:
    :undoc-members:
    :show-inheritance:

RTOC.RTLogger.ScriptFunctions module
------------------------------------

.. automodule:: RTOC.RTLogger.ScriptFunctions
    :members:
    :undoc-members:
    :show-inheritance:

RTOC.RTLogger.importCode module
-------------------------------

.. automodule:: RTOC.RTLogger.importCode
    :members:
    :undoc-members:
    :show-inheritance:

RTOC.RTLogger.loggerlib module
------------------------------

.. automodule:: RTOC.RTLogger.loggerlib
    :members:
    :undoc-members:
    :show-inheritance:

RTOC.RTLogger.scriptLibrary module
----------------------------------

.. automodule:: RTOC.RTLogger.scriptLibrary
    :members:
    :undoc-members:
    :show-inheritance:


RTOC.RTLogger.telegramBot module
--------------------------------

.. automodule:: RTOC.RTLogger.telegramBot
    :members:
    :undoc-members:
    :show-inheritance:
