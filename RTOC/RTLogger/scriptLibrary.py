"""
This is a collection of functions, which can be used in scripts and global events/actions

To use any of these functions, call them with 'RTOC.<function>(...)' in scripts, events or actions.
"""

import scipy as sp
from scipy import signal as scipysignal
import numpy as np


import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)


def lsfit(self, x, y, func="linear", x0=None, n=None):
    """
    Use non-linear least squares to fit a function, func, to data.

    This functions calls :func:`scipy.optimize.curve_fit`.

    There are two predefined functions. Set func to 'linear' to perform a linear lsqfit.
    Set func to 'quad' to perform a quadratic lsqfit.

    Args:
        x (list): List of x-values
        y (list): List of y-values
        func (function): Least-square function or 'linear' or 'quad'
        x0 (:func:`np.array`): List of initial parameters for fitting
        n (int): Length of returned data. If None, default is config['global']['recordLength']

    Returns:
        x (list): x-values (a linspace)
        y (list): Fitted y-values
        params (list): Identified parameters
    """
    if n is None:
        n = self.config['global']['recordLength']
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
    x = np.linspace(min(x), max(x), n)
    y = []
    for value in x:
        y.append(function(value, *params))
    return x, y, params


def resample(self, x, y, n=None):
    """
    One-dimensional linear interpolation.

    This functions calls :func:`numpy.interp`.

    Args:
        x (list): List of x-values
        y (list): List of y-values
        n (int): Length of returned data. If None, default is config['global']['recordLength']

    Returns:
        x (list): x-values (a linspace)
        y (list): Interpolated y-values
    """
    if n is None:
        n = self.config['global']['recordLength']
    if len(x) == len(y):
        x2 = np.linspace(x[0], x[-1], n)
        y = np.interp(x2, x, y)
        return np.array(x2), np.array(y)


def resampleFourier(self, x, y, n=None):
    """
    Resample x to n samples using Fourier method along the given axis.

    This functions calls :func:`scipy.signal.resample`.

    Args:
        x (list): List of x-values
        y (list): List of y-values
        n (int): Length of returned data. If None, default is config['global']['recordLength']

    Returns:
        x (list): x-values (a linspace)
        y (list): Resampled y-values
    """
    if n is None:
        n = self.config['global']['recordLength']
    if len(x) == len(y):
        x = np.linspace(x[0], x[-1], n)
        y, x2 = scipysignal.resample(y, n, x)
        # y = np.interp(x,signalX,signalY)
        return np.array(x), np.array(y)


def combine(self, signalsU, n=None):
    """
    Combines multiple signals to have the same x-values (uses :meth:`.resample`).

    Args:
        signalsU (list): List of signals: [[x,y],[x,y],...]
        n (int): Length of returned data. If None, default is config['global']['recordLength']

    Returns:
        x (list): x-values (a linspace)
        y (list[lists]): List of new y-values for each signal
    """
    if n is None:
        n = self.config['global']['recordLength']
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
    newX = np.linspace(minx, maxx, n)
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


def runningMean(x, y, n=5):
    """
    Returns moving average of signal

    Args:
        x (list): List of x-values
        y (list): List of y-values
        n (int): Number of values for moving average

    Returns:
        x (list): x-values (a linspace)
        y (list): meaned y-values
    """
    y2 = np.zeros((len(y),))
    for ctr in range(len(y)):
        y2[ctr] = np.sum(y[ctr:(ctr+n)])
    y2 = y2[:-n]
    n_2 = int(n/2)
    m = n-n_2
    x = x[m:-n_2]
    return x, y2/n


def mean(x, y, n=None):
    """
    Returns mean-value of signal

    Args:
        x (list): List of x-values
        y (list): List of y-values
        n (int): Number of latest values beeing meaned. If None, default is len(x)

    Returns:
        x (list): x-values (a linspace)
        y (list): meaned y-values
    """
    if n is None:
        n = len(x)
    if len(x) > n:
        m = y[-n:-1]
        n = sum(m)/len(m)
    else:
        n = sum(y)/len(y)
    return n


def PID(x, y, desvalue, kp=1, ki=0, kd=0, initI=None):
    """
    PID-controller.

    Args:
        x (list): List of x-values
        y (list): List of y-values
        desvalue (float): Desired value
        kp (float): proportional control parameter
        ki (float): integrative control parameter
        kd (float): derived control parameter
        initI(float): Use this, if 'ki!=0'. You need to pass the initI value from last call of :meth:`.PID`.

    Returns:
        float: control vlaue

        float (optional): The last integrated value from integrative controller
    """
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
    """
    Returns derivative of latest signal-values

    Args:
        x (list): List of x-values
        y (list): List of y-values

    Returns:
        dy/dx (float): Derivative of latest signal-values
    """
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
    """
    Returns derivative of whole signal

    Args:
        x (list): List of x-values
        y (list): List of y-values

    Returns:
        dy/dx (list): Derivative of whole signal
    """
    if len(y) >= 2 and len(x) == len(y):
        dx = np.diff(x)
        dy = np.diff(y)
        return x[:-1], np.divide(dy, dx)
    else:
        return [0], [0]


def norm(x, y, max=1, min=0, oldMin=None, oldMax=None):
    """
    Normalizes signal to be inbetween 'min' and 'max'.

    Args:
        x (list): List of x-values
        y (list): List of y-values
        max (float): The maximum value of output-signal
        min (float): The minimum value of output-signal
        oldMin (float): The minimum value of original-signal. If None, this will be min(y)
        oldMax (float): The maximum value of original-signal. If None, this will be max(y)

    Returns:
        dy/dx (list): Derivative of whole signal
    """
    if oldMin is None:
        oldMin = min(y)
    if oldMax is None:
        oldMax = max(y)
    y = (y-oldMin)/oldMax
    y = y*max+min
    return x, y
