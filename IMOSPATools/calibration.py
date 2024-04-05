import re
import os
import numpy
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

def calibrate(volts: numpy.ndarray) -> numpy.ndarray:
    
    return calibData
