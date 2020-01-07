******************
First steps
******************

First run
======================================================
After installing RTOC, you can run it with::

  // local RTOC-instance including GUI
  python3 -m RTOC

  // local RTOC-instance without GUI
  // I would recommend starting RTOC as a service and not to use this.
  python3 -m RTOC.RTLogger -s start/stop

  // local RTOC-Configuration from Console
  python3 -m RTOC.RTLogger -c

  // remote RTOC-instance with GUI
  python3 -m RTOC -r <ADRESS>

  // explicit local RTOC GUI (even if database is enabled)
  python3 -m RTOC -l
