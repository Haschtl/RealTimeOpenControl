import numpy as np
import pkgutil
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

"""
    This file contains some general functions of RTLogger
"""

    
def npJSONWorkAround(o):
    if isinstance(o, np.int64):
        return int(o)
    else:
        return o


def iter_namespace(ns_pkg):
    # Specifying the second argument (prefix) to iter_modules makes the
    # returned name an absolute name instead of a relative one. This allows
    # import_module to work without having to do additional modification to
    # the name.
    # return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")
    return pkgutil.walk_packages(path=ns_pkg.__path__, prefix=ns_pkg.__name__ + ".", onerror=lambda x: None)


def list_submodules(package_name):
    list_name = []
    for loader, module_name, is_pkg in pkgutil.walk_packages(package_name.__path__, package_name.__name__+'.'):
        list_name.append(module_name)
        module_name = __import__(module_name, fromlist='dummylist')
        if is_pkg:
            list_submodules(list_name, module_name)
    return list_name


def calcDuration(self, x, maxlen):
    dt = x[-1]-x[0]
    l = len(x)
    # maxlen = self.logger.maxLength
    return dt/l*maxlen
