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

try:
    from statsmodels.tsa.ar_model import AR
    from sklearn.metrics import mean_squared_error
except (ImportError, SystemError):
    AR = None
    logging.info('statsmodels and sklearn is not installed. Cannot use "rtoc.estimate".')

def lsfit(self, x, y, func="linear", x0=None, n=None):
    """
    Use non-linear least squares to fit a function, func, to data.

    This functions calls :py:meth:`.scipy.optimize.curve_fit`.

    There are two predefined functions. Set func to 'linear' to perform a linear lsqfit.
    Set func to 'quad' to perform a quadratic lsqfit.

    Args:
        x (list): List of x-values
        y (list): List of y-values
        func (function): Least-square function or 'linear' or 'quad'
        x0 (:py:meth:`.np.array`): List of initial parameters for fitting
        n (int): Length of returned data. If None, default is config['global']['recordLength']

    Returns:
        x (list): x-values (a linspace)
        y (list): Fitted y-values
        params (list): Identified parameters
    """
    if n is None and self is not None:
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

    This functions calls :py:meth:`.numpy.interp`.

    Args:
        x (list): List of x-values
        y (list): List of y-values
        n (int): Length of returned data. If None, default is config['global']['recordLength']

    Returns:
        x (list): x-values (a linspace)
        y (list): Interpolated y-values
    """
    if n is None and self is not None:
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

def predict(coef, history):
    """
    Make a prediction give regression coefficients and lag obs
    """
    yhat = coef[0]
    for i in range(1, len(coef)):
        yhat += coef[i] * history[-i]
    return yhat

def estimate(x,y, n):
    """
    Estimate n values in future for a signal using ARMA. You need to install the following python packages with pip3: ``pip3 install statsmodels scikit-learn scikit-metrics patsy``

    Args:
        x (list): List of x-values
        y (list): List of y-values
        n (int): Number of values to be estimated

    Returns:
        x (list): List of estimated x-values
        y (list): List of estimated y-values
    """
    if AR is None:
        return

    x, y = resample(None, x, y, n=len(x))
    samplerate = 1/(x[1]-x[0])

    #train = np.diff(y)
    train = np.array(y)
    test = np.linspace(x[-1]+1/samplerate, x[-1]+(1/samplerate)*n, n)
    # size = int(len(data) * 0.66)
    # train, test = data[0:size], data[size:]
    # train autoregression
    model = AR(train)
    model_fit = model.fit(maxlag=6, disp=False)
    window = model_fit.k_ar
    coef = model_fit.params
    # walk forward over time steps in test
    history = [train[i] for i in range(len(train))]
    predictions = list()
    for t in range(len(test)):
        yhat = predict(coef, history)
        predictions.append(yhat)
        history.append(yhat)
    error = mean_squared_error(test, predictions)
    print('Test MSE: %.3f' % error)

    return test, predictions

def correlate(x1,y1,x2,y2, mode='valid'):
    """
    Crosscorrelate two signals using numpy.correlate

    Args:
        x1 (list): List of x-values of signal 1
        y1 (list): List of y-values of signal 1
        x1 (list): List of x-values of signal 2
        y1 (list): List of y-values of signal 2
        mode: {'valid', 'same', 'full') Refer to the convolve docstring. Note that the default is ‘valid’, unlike convolve, which uses ‘full’.

    Returns:
        x (list): List of x-values
        y (list): List of correlated y-values
    """
    maxL = max([len(y1), len(y2)])
    x,ys = combine(None, [[x1,y1],[x2,y2]], n=maxL)
    y = np.correlate(ys[0], ys[1], mode)

    return x, y

def forwardEuler(x,y, f, U_0, samplerate, T):
    dt = 1/samplerate
    N_t = int(round(float(T)/dt))
    u = np.zeros(N_t+1)
    t = np.linspace(0, N_t*dt, len(u))
    u[0] = U_0
    for n in range(N_t):
        u[n+1] = u[n] + dt*f(u[n], t[n])
    return t,u

def CCN():
    """
    https://machinelearningmastery.com/how-to-get-started-with-deep-learning-for-time-series-forecasting-7-day-mini-course/

    https://machinelearningmastery.com/time-series-prediction-lstm-recurrent-neural-networks-python-keras/


    Estimate n values in future for a signal using Convolutional Neural Network model. You need to install the following python packages with pip3: ``pip3 install tensorflow keras``

    Args:
        x (list): List of x-values
        y (list): List of y-values
        n (int): Number of values to be estimated

    Returns:
        x (list): List of estimated x-values
        y (list): List of estimated y-values
    """
    from keras.models import Sequential
    from keras.layers import Dense
    from keras.layers import Flatten
    from keras.layers.convolutional import Conv1D
    from keras.layers.convolutional import MaxPooling1D
    # define dataset
    X = np.array([[10, 20, 30], [20, 30, 40], [30, 40, 50], [40, 50, 60]])
    y = np.array([40, 50, 60, 70])
    # reshape from [samples, timesteps] into [samples, timesteps, features]
    X = X.reshape((X.shape[0], X.shape[1], 1))
    # define model
    model = Sequential()
    model.add(Conv1D(filters=64, kernel_size=2, activation='relu', input_shape=(3, 1)))
    model.add(MaxPooling1D(pool_size=2))
    model.add(Flatten())
    model.add(Dense(50, activation='relu'))
    model.add(Dense(1))
    model.compile(optimizer='adam', loss='mse')
    # fit model
    model.fit(X, y, epochs=1000, verbose=0)
    # demonstrate prediction
    x_input = np.array([50, 60, 70])
    x_input = x_input.reshape((1, 3, 1))
    yhat = model.predict(x_input, verbose=0)
    print(yhat)



def PT2_estimation(x,y, n, k=100, t1=101, t2=100, t0=25):
    """
    Estimate n values in future for a signal with PT2-behavior.

    Args:
        x (list): List of x-values
        y (list): List of y-values
        n (int): Number of values to be estimated
        k (float): Initial parameter for PT2
        t1 (float): Initial parameter for PT2
        t2 (float): Initial parameter for PT2
        t0 (float): Initial parameter for PT2

    Returns:
        x (list): List of estimated x-values
        y (list): List of estimated y-values
    """
    def _pt2(x, k, t1, t2, t0):
        """
        Verzögerungs-Übertragungsglied zweiter Ordnung. Z.b.: zur Temperaturanalyse
        """
        y = k*(1-(1/(t1-t2))*(t1*np.exp(-x/t1)-t2*np.exp(-x/t2)))+t0
        return y

    x, y, params = lsfit(None, x, y, func=_pt2, x0=[k, t1, t2, t0], n=None)
    # perform fitting

    # generate additional x-data
    # calculate y-data
