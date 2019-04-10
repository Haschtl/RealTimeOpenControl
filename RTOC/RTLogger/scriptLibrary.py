import scipy as sp
from scipy import signal as scipysignal
import numpy as np


def lsfit(self, x, y, func="linear", *args, **kwargs):
    x0 = kwargs.get('x0', None)
    num = kwargs.get('n', None)
    for idx, arg in enumerate(args):
        if idx == 0:
            x0 = arg
        if idx == 1:
            num = arg

    if num is None:
        num = self.maxLength
    # Initial guess.
    if type(func) == str:  # automatic mode
        if func == "linear":
            x0 = np.array([0, 0])

            def function(x, a, b):
                return a + b*x
        elif func == "quad":
            x0 = np.array([0, 0, 0])

            def function(x, a, b, c):
                return a + b*x + c*x*x
    else:
        function = func

    params, matrix = sp.optimize.curve_fit(function, x, y, x0)
    x = np.linspace(min(x), max(x), num)
    y = []
    for value in x:
        y.append(function(value, *params))
    return x, y, params


def resample(self, x, y, *args, **kwargs):
    num = kwargs.get('n', None)
    for idx, arg in enumerate(args):
        if idx == 0:
            num = arg

    if num is None:
        num = self.maxLength
    if len(x) == len(y):
        x2 = np.linspace(x[0], x[-1], num)
        y = np.interp(x2, x, y)
        return np.array(x2), np.array(y)


def resampleFourier(self, x, y, *args, **kwargs):
    num = kwargs.get('n', None)
    for idx, arg in enumerate(args):
        if idx == 0:
            num = arg

    if num is None:
        num = self.maxLength
    if len(x) == len(y):
        x = np.linspace(x[0], x[-1], num)
        y, x2 = scipysignal.resample(y, num, x)
        # y = np.interp(x,signalX,signalY)
        return np.array(x), np.array(y)


def combine(self, signalsU, *args, **kwargs):
    for arg in args:
        pass  # optionale parameter ohne
    num = kwargs.get('n', None)
    # FALSCH, da signals jetzt = [x,y, x,y, x,y]
    if num is None:
        num = self.maxLength
    signals = []
    for idx, sig in enumerate(signalsU):
        if idx % 2 != 0:
            signals.append([signalsU[idx-1], signalsU[idx]])
    minx = []
    maxx = []
    for signal in signals:
        minx.append(min(list(signal[0])))
        maxx.append(max(list(signal[0])))
    minx = max(minx)
    maxx = min(maxx)
    newX = np.linspace(minx, maxx, num)
    retSignals = []
    for signal in signals:
        retSignal = []
        oldX = []
        oldY = []
        for idx, x in enumerate(signal[0]):
            if x > minx and x < maxx:
                oldX.append(x)
                oldY.append(signal[1][idx])
        retSignal = np.interp(newX, oldX, oldY)
        retSignals.append(retSignal)
    return newX, retSignals


def runningMean(x, y, *args, **kwargs):
    N = kwargs.get('n', 5)
    for idx, arg in enumerate(args):
        if idx == 0:
            N = arg

    y2 = np.zeros((len(y),))
    for ctr in range(len(y)):
        y2[ctr] = np.sum(y[ctr:(ctr+N)])
    y2 = y2[:-N]
    n = int(N/2)
    m = N-n
    x = x[m:-n]
    return x, y2/N


def mean(x, y, *args, **kwargs):
    N = kwargs.get('n', None)
    for idx, arg in enumerate(args):
        if idx == 0:
            N = arg

    if len(x) > N:
        m = y[-N:-1]
        n = sum(m)/len(m)
    else:
        n = sum(y)/len(y)
    return n


def PID(x, y, desvalue, *args, **kwargs):
    kp = kwargs.get('kp', 1)
    ki = kwargs.get('ki', 0)
    kd = kwargs.get('kd', 0)
    initI = kwargs.get('initI', None)
    for idx, arg in enumerate(args):
        if idx == 0:
            kp = arg
        if idx == 1:
            ki = arg
        if idx == 2:
            kd = arg
        if idx == 3:
            initI = arg

    value = y[-1]
    error = value-desvalue
    regelung = kp*error+d(x, y)*kd
    if initI is not None:
        newI = initI + error
        regelung += ki*newI
        return regelung, newI
    else:
        return regelung


def d(x, y):
    if len(y) >= 2:
        dy = y[-2]-y[-1]
        dx = x[-2]-x[-1]
        if dx == 0:
            if dy > 0:
                return float('inf')
            elif dy < 0:
                return float('-inf')
            else:
                return 0
        else:
            return dy/dx
    else:
        return 0


def diff(x, y):
    if len(y) >= 2 and len(x) == len(y):
        dx = np.diff(x)
        dy = np.diff(y)
        return x[:-1], np.divide(dy, dx)
    else:
        return [0], [0]


def norm(x, y, *args, **kwargs):
    normGain = kwargs.get('max', 1)
    normOffset = kwargs.get('min', 0)
    min = kwargs.get('oldMin', None)
    max = kwargs.get('oldMax', None)
    for idx, arg in enumerate(args):
        if idx == 0:
            normGain = arg
        if idx == 1:
            normOffset = arg
        if idx == 2:
            min = arg
        if idx == 3:
            max = arg

    if min is None:
        min = min(y)
    if max is None:
        max = max(y)
    y = (y-min)/max
    y = y*normGain+normOffset
    return x, y
