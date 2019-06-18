"""
This template shows, how to implement plugins in RTOC

RTOC version 2.0

A plugin needs to import RTOC.LoggerPlugin to be recognized by RTOC.
"""
try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

import sys
import time
from PyQt5 import uic
from PyQt5 import QtWidgets
import numpy as np

DEVICENAME = "Template"
"""Definition of the devicename outside of plugin-class"""

AUTORUN = True
"""If true, the thread to collect data will run right after initializing this plugin"""
SAMPLERATE = 1
"""The thread,which is supposed to collect data will be executed with 1 Hz"""


class Plugin(LoggerPlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        """Call this to initialize RTOC.LoggerPlugin"""

        self.setDeviceName(DEVICENAME)
        """
        Set a default devicename.
        This will be used for all signals sent by this plugin as default
        """

        self.smallGUI = True
        """This plugin has a GUI, which is small. GUI can be shown in two different ways."""

        self._firstrun = True

        self.setPerpetualTimer(self._updateT, samplerate=SAMPLERATE)
        """You will need to collect data periodically in many applications. You need to start that in a seperate thread.

        RTOC provides a simple way to start a repeated thread with :py:meth:`.LoggerPlugin.setPerpetualTimer`. The first parameter is the function, which collects data and sends it to RTOC. You can define a ``samplerate`` or an ``interval`` to set the samplerate.

        You can still use normal threads to do the same thing, but in this way, the plugin can be stopped properly. If you are using normal threads, make sure, to have a loop limited by '
        ``self.run`` with ``while self.run:``.
        """

        if AUTORUN:
            self.start()
            """
            Start the configured perpetualTimer. You can stop it with ``self.cancel()``. If you want to start data collection, when this plugin is started, you need to call ``self.start()`` in the plugin-initialization.
            """

    def _updateT(self):
        """
        This function is called periodically after calling ``self.start()``.

        This example will generate a sinus and a cosinus curve. And send them to RTOC.


        """
        y1 = np.sin(time.time())
        y2 = np.cos(time.time())

        self.stream([y1, y2], snames=['Sinus', 'Cosinus'], unit=["kg", "m"])
        """
        Use this function to send data to RTOC: :py:meth:`.LoggerPlugin.stream`
        """

        self.plot([-10, 0], [2, 1], sname='Plot', unit='Wow')
        """
        Use this function to send data to RTOC: :py:meth:`.LoggerPlugin.plot`
        """
        if self._firstrun:
            self.event('Test event', sname='Plot', id='testID')
            """
            Use this function to send an event to RTOC: :py:meth:`.LoggerPlugin.event`
            """
            self._firstrun = False

    def loadGUI(self):
        """
        This function is used to initialize the Plugin-GUI, which will be available in :doc:`GUI`.

        This is optional.

        Returns:
            PyQt5.QWidget: A widget containing optional plugin-GUI
        """
        self.widget = QtWidgets.QWidget()
        """
        Create an empty QWidget
        """
        packagedir = self.getDir(__file__)
        """Get filepath of this file"""
        uic.loadUi(packagedir+"/Template/template.ui", self.widget)
        """
        This example will load a QWidget designed with QDesigner
        """
        self.widget.teleMessageButton.clicked.connect(self._teleMessageAction)
        self.widget.telePhotoButton.clicked.connect(self._telePhotoAction)
        self.widget.teleFileButton.clicked.connect(self._teleFileAction)
        """
        Connect GUI-buttons with python-functions
        """
        return self.widget  # This function needs to return a QWidget

    def _teleMessageAction(self):
        text = 'Hello world!'
        self.telegram_send_message(text, onlyAdmin=False)

    def _telePhotoAction(self):
        path = self.getDir(__file__)+'/examplePhoto.png'
        self.telegram_send_photo(path, onlyAdmin=False)

    def _teleFileAction(self):
        path = self.getDir(__file__)+'/examplePhoto.png'
        self.telegram_send_document(path, onlyAdmin=False)



hasGUI = True  # If your plugin has a widget do this

if __name__ == "__main__":
    """
    Sometimes you want to use plugins standalone also. This is very useful for testing.
    """
    if hasGUI:
        app = QtWidgets.QApplication(sys.argv)
        myapp = QtWidgets.QMainWindow()

    widget = Plugin()

    if hasGUI:
        widget.loadGUI()
        myapp.setCentralWidget(widget.widget)

        myapp.show()
        app.exec_()

    widget.run = False

    sys.exit()
