*************
Installation
*************

Python3 needs to be installed on your target-computer. Download python3 from the official website: `www.python.org <https://www.python.org/downloads/>`_

After installing python3, you are able to run python in a terminal. (``cmd.exe`` on windows)
.. code-block:: bash

  $ python3 --version
  Python 3.6.3


Installing with Python3 (recommended)
======================================================

RTOC is available in the Python package manager PIP::

  pip3 install RTOC


This will download the basic RTOC without the dependencies needed for the GUI, Websockets and Telegram. The default RTOC setup is suitable for running RTOC on embedded devices.

There are also different variations available to install::

  pip3 install RTOC[GUI]         # Includes all packages for GUI
  pip3 install RTOC[Telegram]    # Includes all packages for Telegram
  pip3 install RTOC[ALL]         # Includes all packages

Installing from builds
======================================================

Download the latest release builds for Windows `here <https://github.com/Haschtl/RealTimeOpenControl/releases>`_.

Extract the .zip file into a directory. RTOC is started by double-clicking on "RTOC.exe". Alternatively via command line::

  // local RTOC-instance including GUI
  ./RTOC

Install manually
======================================================

To use the basic RTOC, the following dependencies must be installed::

  pip3 install numpy pycryptodomex requests python-nmap whaaaaat prompt_toolkit psycopg2


If you want to use the GUI you must also install the following packages::

  pip3 install pyqt5 pyqtgraph markdown2 xlsxwriter scipy pandas ezodf pyGithub


If you want full functionality, then you still need the following packages (for telegram bot)::

  pip3 install python-telegram-bot matplotlib


You can use different stylesheets for the GUI if you want. Just install one of these with pip:
'QDarkStyle', 'qtmodern', 'qdarkgraystyle'.


The RTOC repository can then be cloned with::

  git clone git@github.com:Haschtl/RealTimeOpenControl.git


Long-time measurements in postgreSQL database (optional)
=========================================================
If you want to store measurements for a long period of time, I would recommend to use RTOC with a postgreSQL database. Therefore you need to setup postgreSQL on your system and change the postgresql parameters in your :ref:`config.json` file.

**Setup postgreSQL on linux**

1. Open a terminal window
2. Issue the command ``sudo apt install postgresql``
3. Follow the instructions to change the default postgresql-password.
4. Add a new user. You need to switch to the root user to create a new postgres-user

.. code-block:: bash

  $ sudo bash
  $ su - postgres
  $ createuser --interactive --pwprompt
  $ Enter name of role to add: <NEWUSERNAME>
  $ Enter password for new role: <PASSWORD>
  $ Enter it again: <PASSWORD>
  $ Shall the new role be a superuser? (y/n) n
  $ Shall the new role be allowed to create databases? (y/n) y
  $ Shall the new role be allowed to create more new roles? (y/n) n
  $ exit  // to return to root user
  $ exit // to return to your user

5. Create a database

.. code-block:: bash

  $ createdb -O <NEWUSERNAME> <DATABASE_NAME>

6. Enter your postgresql username, port, database and password in your :ref:`config.json` file.


**Setup postgreSQL on windows**

2. Download postgresql one-click installer from `this website <https://www.enterprisedb.com/downloads/postgres-postgresql-downloads#windows>`_
3. Double click on the downloaded file and follow the setup instructions.
4. Add a new user and create a database (google for that)
5. Enter your postgresql username, port, database and password in your :ref:`config.json` file.
