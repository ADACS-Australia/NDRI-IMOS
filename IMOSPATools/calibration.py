import numpy
import scipy
import logging
from typing import Final

from IMOSPATools import rawdat
# from IMOSPATools import diagplot

OVERLOAD_LOWER_BOUND: Final[int] = 50
OVERLOAD_UPPER_BOUND: Final[int] = 65000
FULLSCALE_VOLTS: Final[float] = 5.0

log = logging.getLogger('IMOSPATools')
doWriteIntermediateResults = False

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

    if doWriteIntermediateResults:
        numpy.savetxt('signal_binData.txt', binData, fmt='%d')
        # diagplot.dp.add_plot(binData, "Original Signal bin data", 500)
        # diagplot.dp.show()

    # Multiply by this factor to convert A/D counts to volts 0.0..5.0V
    countsToVolts = FULLSCALE_VOLTS / (1 << rawdat.BITS_PER_SAMPLE)
    offsetToVolts = numpy.mean(binData[:] * countsToVolts)
    voltsData = (countsToVolts * binData[:]) - offsetToVolts

    if doWriteIntermediateResults:
        numpy.savetxt('signal_voltsData.txt', voltsData, fmt='%.5f')
        # diagplot.dp.add_plot(voltsData, "Original Signal Volts")

    return voltsData


def loadPrepCalibFile(fileName: str,
                      cnl: float,
                      hs: float) -> (numpy.ndarray, numpy.ndarray, float):
    """
    Load and pre-process calibration file

    :param fileName: file name (can be relative/full path)
    :param cnl: calibration noise level (dB re V^2/Hz)
    :param hs: hydrophone sensitivity (dB re V/uPa)
    :param binData: raw audio data
    :return: calibration spectrum as numpy array
    :return: calibration frequencies as numpy array
    :return: sampling rate
    """
    calBinData, numChannels, sampleRate, durationHeader, \
        startTime, endTime = rawdat.readRawFile(fileName)

    if doWriteIntermediateResults:
        numpy.savetxt('calBinData.txt', calBinData, fmt='%d')
        # diagplot.dp.add_plot(calBinData, "Calibration Signal binary")

    calVoltsData = toVolts(calBinData)

    if doWriteIntermediateResults:
        numpy.savetxt('calVoltsData.txt', calVoltsData, fmt='%.5f')
        # diagplot.dp.add_plot(calBinData, "Calibration Signal Volts")

    # signal.welsh() estimates the power spectral density using welsh method,
    # by dividing the data into segments and averaging periodograms computed
    # on each segment
    # f, Pxx_spec = scipy.signal.welch(x, fs=1.0, window='hann', 
    #       nperseg=None, noverlap=None, nfft=None,
    #       detrend='constant', return_onesided=True,
    #       scaling='density', axis=-1, average='mean')
    # assuming these defaults: noverlap=None, nfft=None, detrend='constant',
    #       return_onesided=True, scaling='density', axis=-1, average='mean'
    # the original Matlab code uses Hamming window of size equal to 1 second
    #       (which equals to frequency in a discrete sampling scale)
    #
    # matlab welch func is: [pxx,f] = pwelch(x,window,noverlap,f,fs)
    # sasha calls it as [Cal_spec,Cal_freq] = pwelch(Cal_sig,Fsamp,0,Fsamp,Fsamp);

    # in scipy, we need to construct hamming window externally, as this is 
    # not included in the welch() library function as in Matlab's pwelch()
    # suing round to convert sampling rate to int as it is float.
    hammingWindow = scipy.signal.windows.hamming(round(sampleRate))

    # debugging...
    log.debug(f"hammingWindow size is: {hammingWindow.size}")

    # obviously, the parameters are mixed up, and even returned params
    # swapped Python v Matlab
    calFreq, calSpec = scipy.signal.welch(calVoltsData, sampleRate, window=hammingWindow)

    if doWriteIntermediateResults:
        numpy.savetxt('calFreq.txt', calFreq, fmt='%.2f')
        numpy.savetxt('calSpec.txt', calSpec, fmt='%.10f')

    # debugging...
    log.debug(f"calSpec size is: {calSpec.size}")
    log.debug(f"calFreq size is: {calFreq.size}")

    # apply 51 th-order one-dimensional median filter
    calSpecFilt = scipy.signal.medfilt(calSpec, 51)
    calSpecNoise = calSpecFilt / (10.0 ** (cnl/10.0)) * (10.0 ** (hs/10.0))
    log.debug(f"calSpec scaled size is: {calSpec.size}")

    if doWriteIntermediateResults:
        numpy.savetxt('calSpecFilt.txt', calSpecFilt)
        numpy.savetxt('calSpecNoise.txt', calSpecNoise)

    return calSpecNoise, calFreq, sampleRate


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

    if doWriteIntermediateResults:
        numpy.savetxt('signal_filtered.txt', signal, fmt='%.5f')
        # diagplot.dp.add_plot(signal, "Filtered Signal Volts")

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
    # generate a set of frequencies as ndarray
    freqFFT = numpy.arange(0, fmax + df, df)
    # MC note: the interpolation function numpy.interp() has a different
    #          params order compared with matlab function interp1()
    calSpecInt = numpy.interp(freqFFT, calFreq, calSpec)

    # Ignore calibration values below 5 Hz to avoid inadequate correction
    N5Hz = numpy.where(freqFFT <= 5)[0]
    calSpecInt[N5Hz] = calSpecInt[N5Hz[-1]]

    if doWriteIntermediateResults:
        numpy.savetxt('spec.txt', spec, fmt='%.10f')
        numpy.savetxt('freq_fft.txt', freqFFT, fmt='%.3f')
        numpy.savetxt('calSpecInt.txt', calSpecInt)

    # debugging...
    print(calSpecInt[82:86])
    print(calSpecInt[-86:-82])

    print(spec[:5])
    print(spec[-5:])

    print(spec[1:5])
    print(spec[-5:-2])

    # MC note: we cut off the imaginary component and use only real,
    #          as python math libs leave non-zero imaginary component
    #          artifacts - a consequnece of floats implementation
    if numpy.floor(len(signal) / 2) == len(signal) / 2:
        # calibratedSignal = numpy.fft.ifft(spec / numpy.sqrt(numpy.concatenate((calSpecInt[1:], calSpecInt[::-1][1:])))).real
        calibratedSignal = numpy.fft.ifft(spec / numpy.sqrt(numpy.concatenate((calSpecInt[1:], calSpecInt[::-1][:-1])))).real
    else:
        # calibratedSignal = numpy.fft.ifft(spec / numpy.sqrt(numpy.concatenate((calSpecInt, calSpecInt[::-1][1:])))).real
        calibratedSignal = numpy.fft.ifft(spec / numpy.sqrt(numpy.concatenate((calSpecInt, calSpecInt[::-1][:-1])))).real

    # debugging...
    print(calibratedSignal[:5])
    print(calibratedSignal[-5:])

    # ## THIS DIAGNOSTIC CODE MAKES SENSE ONLY WHEN WE DON OT PICK ONLY REAL COMPONENT ABOVE
    # maxAbsImaginary = numpy.max(numpy.abs(calibratedSignal.imag))
    # logMsg = (f"Maximum absolute value of imaginary component of calibrated signal after IFFT: {maxAbsImaginary}")
    # log.info(logMsg)

    # Sanity check of the signal after IFFT - imaginary components of the signal shall be zero-ish
    if not numpy.allclose(calibratedSignal.imag, 0.0):
        logMsg = "Calibrated signal after IFFT contains non-zero imaginary component(s)"
        log.error(logMsg)
        raise IMOSAcousticCalibException(logMsg)

    log.debug(f"calibrated signal size is: {calibratedSignal.size}")
    log.debug(f"calibrated signal sample type is: {calibratedSignal.dtype}")
    log.debug(f"calibrated signal sample size is: {calibratedSignal.itemsize} bytes")

    if doWriteIntermediateResults:
        numpy.savetxt('signal_calibrated.txt', calibratedSignal)
        # diagplot.dp.add_plot(calibratedSignal, "Calibrated Signal after IFFT")

    return calibratedSignal


def scaleToBinary(signal: numpy.ndarray, bitsPerSample: int) -> numpy.ndarray:
    """
    scaling of output for writing into wav file

    :param signal: audio data/signal
    :param bitsPerSample: bits per sample
    :return: scaled audio signal
    """
    # scaling as per Sasha's matlab code
    normaliseFactor = 10 ** numpy.ceil(numpy.log10(numpy.max(numpy.abs(signal))))
    normalisedSignal = signal / normaliseFactor

    if doWriteIntermediateResults:
        numpy.savetxt('signal_normalised.txt', normalisedSignal)
        # diagplot.dp.add_plot(calibratedSignal, "Calibrated Signal after IFFT")

    # debugging...
    normalisedMin = numpy.min(normalisedSignal)
    normalisedMax = numpy.max(normalisedSignal)
    log.debug(f"Min sample value in the normalised signal is: {normalisedMin}")
    log.debug(f"Max sample value in the normalised signal is: {normalisedMax}")

    normalizedSignal = (normalisedSignal - normalisedMin) / (normalisedMax - normalisedMin) * 2 - 1
    toInt16Factor = ((1 << (bitsPerSample - 1)) - 1)
    signalBinFloat = normalizedSignal * toInt16Factor
    roundedSignal = numpy.round(signalBinFloat)

    if doWriteIntermediateResults:
        numpy.savetxt('signal_scaled.txt', roundedSignal)
        # diagplot.dp.add_plot(roundedSignal, "Calibrated Scaled Normalised Signal")

    return(roundedSignal)
