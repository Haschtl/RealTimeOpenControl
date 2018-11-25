import numpy as np
import pkgutil


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
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")


def calcDuration(self, x, maxlen):
    dt = x[-1]-x[0]
    l = len(x)
    # maxlen = self.logger.maxLength
    return dt/l*maxlen
