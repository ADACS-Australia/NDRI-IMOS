import re
import os
import numpy
import scipy
from datetime import datetime
from typing import Tuple
import _io
import logging
from typing import Final

from IMOSPATools import rawdat

OVERLOAD_LOWER_BOUND: Final[int] = 50
OVERLOAD_UPPER_BOUND: Final[int] = 65000
FULLSCALE_VOLTS: Final[float] = 5.0

class IMOSAcousticCalibException(Exception):
    pass


def countOverload(binData: numpy.ndarray) -> int:
    """
    Count samples with overload
    (too sensitive gain, limited)
    In the original code, a window popped up with warning during
    the interactive method of loading and calibrating sound logger data
    ('Logger was overloaded - signal is clipped on all recorder channels')
    
    :param binData: raw audio data
    :return: count of samples with overload
    """
    count = 0
    for i in binData:
        if i < OVERLOAD_LOWER_BOUND or i > OVERLOAD_UPPER_BOUND:
            count += 1

    return count

def toVolts(binData: numpy.ndarray) -> numpy.ndarray:
    """
    Convert waw data to Volts
    Modified Franks method
    
    :param binData: raw audio data
    :return: audio data in Volts
    """
    # Multiply by this factor to convert A/D counts to volts 0-5
    countsToVolts = FULLSCALE_VOLTS/rawdat.BITS_PER_SAMPLE
    voltsData[:] = (countsToVolts * binData[:]) - np.mean(binData[:] * countsToVolts)

    return voltsData

def loadPrepCalibFile(calibFileName, cnl: float, hs: float)

scipy.signal.welch(x, fs=1.0, window='hann', nperseg=None, noverlap=None, nfft=None, detrend='constant', return_onesided=True, scaling='density', axis=-1, average='mean')

def calibrate(volts: numpy.ndarray, cnl: float, hs: float) -> numpy.ndarray:
    """
    calibrate sound record
    
    :param volts: audio data in Volts
    :param cnl: calibration noise level (dB re V^2/Hz)
    :hydrophone sensitivity (dB re V/uPa) 
    :return: calibrated audio data in Volts
    """
    
    return calibData
