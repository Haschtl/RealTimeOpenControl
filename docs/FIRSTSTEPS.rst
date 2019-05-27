******************
First steps
******************

First run
======================================================
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
