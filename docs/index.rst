*************************************
RealTime OpenControl's documentation
*************************************
..
  .. mdinclude:: ../README.md

Welcome to RealTime OpenControl's documentation
================================================
RealTime OpenControl (RTOC) is a free software for recording measurement data of various measuring instruments. It offers the following components

RTLogger backend
++++++++++++++++++++
The core element of RTOC. More information here: :doc:`RTOC.RTLogger`

Expandable with plugins
++++++++++++++++++++++++++++
You can write plugins by your own or use a plugin from the repository. More information here: :doc:`PLUGINS`

Telegram-Bot
+++++++++++++++++++++++++++++
The Telegram-Bot offers access to RTOC from any device with `Telegram <https://www.telegram.com>`_ installed. More information here: :doc:`/TELEGRAM`

Websocket-Server
++++++++++++++++++++
Communication with RTLogger from other processes or devices. Suitable for embedded devices with graphical user interface. More information here: :doc:`/Websocket`

Graphical user interface (RTOC-GUI)
++++++++++++++++++++++++++++++++++++
Used, when running RTOC on computers/laptops to view and edit data. More information here :doc:`/GUI`.

Scripting/Automation
+++++++++++++++++++++++++++++
You can write scripts and run/edit and stop them during runtime. You have full access to all data stored in RTOC and access to all plugins. A event/action system gives a simple solution for very custom automisations. More information here: :doc:`/SCRIPT`

Getting started
================================================
Follow one of the installation-instructions (pip, builds, source): :doc:`INSTALLATION`

See this :doc:`/EXAMPLE` to get an idea of the capabilities of RTOC.

Writing your first plugin
--------------------------------
Have a look at the plugin-documentation: :doc:`PLUGINS`

Data storage
---------------------------
RTOC will create a directory in the home-directory, where all user-data is stored. More information here: :doc:`USERDATA`


FAQ
================================================
- How can I get plugins from the community? :ref:`Plugin repository`
- How do I import new data from CSV, Wave, Excel, ODF, Matlab? :ref:`Import/Export signals/sessions`
- How do I connect a new plugin? :doc:`PLUGINS`
- How do I create a sub-GUI for a device? :ref:`Writing Plugins`
- How do I create my first script? :doc:`SCRIPT`
- What does the trigger mean? :ref:`Trigger-System`
- RTOC library and default functions for scripts: :mod:`.RTLogger.scriptLibrary`
- Can I access the data from any device? :doc:`TELEGRAM` or :doc:`Websocket`
- How do I use the graphical user interface? :doc:`GUI`
- How do I create a telegram bot? :ref:`Telegram-Bot setup`
- How do I control an RTOC server via Websocket in the network? :ref:`Remote-control via Websocket`
- Where can I find examples for plugins? `RTOC repository <https://github.com/Haschtl/RTOC-Plugins>`_


Feel free to buy me some coffee with milk

.. raw:: html

    <form action="https://www.paypal.com/cgi-bin/webscr" method="post" target="_top">
    <input type="hidden" name="cmd" value="_s-xclick" />
    <input type="hidden" name="hosted_button_id" value="Y5894CRYB4L36" />
    <input type="image" src="https://www.paypalobjects.com/en_US/DK/i/btn/btn_donateCC_LG.gif" border="0" name="submit" title="PayPal - The safer, easier way to pay online!" alt="Donate with PayPal button" />
    <img alt="" border="0" src="https://www.paypal.com/en_DE/i/scr/pixel.gif" width="1" height="1" />
    </form>



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Table of contents
=============================
.. toctree::
  :maxdepth: 5

  self
  INSTALLATION
  FIRSTSTEPS

.. toctree::
  :maxdepth: 5
  :caption: Configuration

  PLUGINS
  USERDATA

.. toctree::
  :maxdepth: 5
  :caption: User-Interaction

  TELEGRAM
  SCRIPT
  GUI
  WEBSOCKET

.. toctree::
  :maxdepth: 5
  :caption: Source code

  RTOC.RTLogger
  RTOC
  View source on Github <https://github.com/Haschtl/RealTimeOpenControl/tree/master/RTOC>

.. toctree::
  :maxdepth: 5
  :caption: Usecases

  EXAMPLE

.. toctree::
  :maxdepth: 5
  :caption: Contributing

  CONTRIBUTING
  Donate <https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=V3JGL7BM8WGQY&source=url>
