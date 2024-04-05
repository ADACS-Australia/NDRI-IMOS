import re
import os
import numpy
from datetime import datetime
from typing import Tuple
import _io
import logging
from typing import Final

OVERLOAD_LOWER_BOUND: Final[integer] = 50
OVERLOAD_UPPER_BOUND: Final[integer] = 65000


class IMOSAcousticCalibException(Exception):
    pass


def calculateOverload(binData: numpy.ndarray) -> int:
    overloadCount = 0
    for i in binData:
        if i < OVERLOAD_LOWER_BOUND or i > OVERLOAD_UPPER_BOUND:
            overloadCount += 1

    return overloadCount


def toVolts(binData: numpy.ndarray) -> numpy.ndarray:
    
    return voltsData


def calibrate(volts: numpy.ndarray) -> numpy.ndarray:
    
    
    return calibData
