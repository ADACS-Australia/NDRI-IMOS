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

log = logging.getLogger('IMOSPATools')


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
    voltsData = (countsToVolts * binData[:]) - numpy.mean(binData[:] * countsToVolts)

    return voltsData


def loadPrepCalibFile(fileName: str,
                      cnl: float,
                      hs: float) -> (numpy.ndarray, numpy.ndarray, float):
    """
    Load and pre-process calibration file

    :param fileName: file name (can be relative/full path)
    :param binData: raw audio data
    :return: audio data in Volts
    """
    calBinData, numChannels, sampleRate, durationHeader, \
        startTime, endTime = rawdat.readRawFile(fileName)

    # signal.welsh() estimates the power spectral density using welsh method,
    # by dividing the data into segments and averaging periodograms computed
    # on each segment
    # scipy.signal.welch(x, fs=1.0, window='hann', nperseg=None, noverlap=None,
    #       nfft=None, detrend='constant', return_onesided=True,
    #       scaling='density', axis=-1, average='mean')
    # assuming these defaults: noverlap=None, nfft=None, detrend='constant',
    #       return_onesided=True, scaling='density', axis=-1, average='mean'
    # the original Matlab code uses Hamming window of size equal to 1 second 
    #       (frequency in sampling scale)
    hammingWindow = scipy.signal.windows.hamming(round(sampleRate))
    log.debug(f"hammingWindow size is: {hammingWindow.size}")
    calSpec, calFreq = scipy.signal.welch(calBinData, sampleRate, window=hammingWindow)
    log.debug(f"calSpec size is: {calSpec.size}")
    log.debug(f"calFreq size is: {calFreq.size}")

    # apply an 51 th-order one-dimensional median filter
    calSpec = scipy.signal.medfilt(calSpec, 51)
    calSpec = calSpec / (10.0 ** (cnl/10.0)) * (10.0 ** (hs/10.0))
    log.debug(f"calSpec scaled size is: {calSpec.size}")

    return calSpec, calFreq, sampleRate


def calibrate(volts: numpy.ndarray, cnl: float, hs: float,
              calSpec: numpy.ndarray, calFreq: numpy.ndarray, fSample: float) -> numpy.ndarray:
    """
    calibrate sound record

    :param volts: audio data/signal in Volts
    :param cnl: calibration noise level (dB re V^2/Hz)
    :param hs: hydrophone sensitivity (dB re V/uPa)
    :param calSpec: calibration spectrum
    :param calFreq: calibration frequencies
    :param fSample: sampling frequency of the recorder sensor
    :return: calibrated audio signal
    """
    # Sanity check of the input audio signal (parameter volts) for NaNs
    if numpy.isnan(volts).any():
        logMsg = "Audio signal in volts contains NaN value(s)"
        log.error(logMsg)
        raise IMOSAcousticCalibException(logMsg)

    # make high-pass filter to remove slow varying DC offset
    b, a = scipy.signal.butter(5, 5/fSample*2, btype='high', output='ba')
    # apply the filter on the input signal
    signal = scipy.signal.lfilter(b, a, volts)
    # Sanity check if filtered audio signal sill has no NaNs
    if numpy.isnan(signal).any():
        logMsg = "Audio signal in volts contains NaN value(s)"
        log.error(logMsg)
        raise IMOSAcousticCalibException(logMsg)
    log.debug(f"filtered signal size is: {signal.size}")

    # make correction for calibration data to get signal amplitude in uPa:
    spec = numpy.fft.fft(signal)
    fmax = calFreq[len(calFreq) - 1]
    df = fmax * 2 / len(signal)
    freqFFT = numpy.arange(0, fmax + df, df)
    # MC note: the numpy.interp() function has a different params order from
    #          matlab function interp1()
    calSpecInt = numpy.interp(freqFFT, calSpec, calFreq)

    # Ignore calibration values below 5 Hz to avoid inadequate correction
    N5Hz = numpy.where(freqFFT <= 5)[0]
    calSpecInt[N5Hz] = calSpecInt[N5Hz[-1]]

    if numpy.floor(len(signal) / 2) == len(signal) / 2:
        calibratedSignal = numpy.fft.ifft(spec / numpy.sqrt(numpy.concatenate((calSpecInt[:-1], calSpecInt[::-1][1:])))).real
    else:
        calibratedSignal = numpy.fft.ifft(spec / numpy.sqrt(numpy.concatenate((calSpecInt, calSpecInt[::-1][1:])))).real

    log.debug(f"calibrated signal size is: {calibratedSignal.size}")
    log.debug(f"calibrated signal sample type is: {calibratedSignal.dtype}")
    log.debug(f"calibrated signal sample size is: {calibratedSignal.itemsize} bytes")

    return calibratedSignal


def scaleToBinary(signal: numpy.ndarray, bitsPerSample: int) -> numpy.ndarray:
    """
    scaling of output for writing into wav file

    :param signal: audio data/signal
    :param bitsPerSample: bits per sample
    :return: scaled audio signal
    """
    # scaling as per Sasha's matlab code
    scaleFactor = 10 ** numpy.ceil(numpy.log10(numpy.max(numpy.abs(signal))))
    scaledSignal = signal/scaleFactor
    scaledMin = numpy.min(scaledSignal)
    scaledMax = numpy.max(scaledSignal)
    log.debug(f"Min sample value in the scaled signal is: {scaledMin}")
    log.debug(f"Max sample value in the scaled signal is: {scaledMin}")

    normalizedSignal = (scaledSignal - scaledMin) / (scaledMax - scaledMin) * 2 - 1
    print((1 << (bitsPerSample - 2)) - 1)
    signalBinFloat = normalizedSignal * 32767
    roundedSignal = numpy.round(signalBinFloat)

    return(roundedSignal)
