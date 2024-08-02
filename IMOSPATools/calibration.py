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

    # Multiply by this factor to convert A/D counts to volts 0.0..5.0V
    countsToVolts = FULLSCALE_VOLTS / (1 << rawdat.BITS_PER_SAMPLE)
    offsetToVolts = numpy.mean(binData[:] * countsToVolts)
    voltsData = (countsToVolts * binData[:]) - offsetToVolts

    if doWriteIntermediateResults:
        numpy.savetxt('signal_voltsData.txt', voltsData, fmt='%.5f')

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

    # debugging...
    log.debug(f"Calibration data size is: {calBinData.size}")

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
    log.debug(f"hammingWindow size is: {hammingWindow.size}")

    # obviously, the parameters are mixed up, and even returned params
    # swapped Python v Matlab
    calFreq, calSpec = scipy.signal.welch(calVoltsData, sampleRate, window=hammingWindow)

    if doWriteIntermediateResults:
        numpy.savetxt('calFreq.txt', calFreq, fmt='%.2f')
        numpy.savetxt('calSpec.txt', calSpec, fmt='%.10f')

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


def extractNotClose(array1, array2, rtol=1e-05, atol=1e-08):
    """
    Compare two arrays and extract values from array1 that are not close to 
    corresponding values in array2.

    Parameters:
    array1 (numpy.ndarray): First input array
    array2 (numpy.ndarray): Second input array
    rtol (float): Relative tolerance (default: 1e-05)
    atol (float): Absolute tolerance (default: 1e-08)

    Returns:
    numpy.ndarray: Array of values from array1 not close to corresponding values in array2
    """
    if array1.shape != array2.shape:
        raise ValueError("Input arrays must have the same shape")

    # Create a boolean mask for values that are not close
    not_close_mask = ~numpy.isclose(array1, array2, rtol=rtol, atol=atol)
    # Use the mask to extract values from array1
    not_close_values = array1[not_close_mask]

    return not_close_values


def testConjugateSymmetry(spectrum: numpy.ndarray) -> bool:
    """
    This function check whether the spectrum has the proper symmetry
    for a real-valued signal. Apply this to your spectrum before
    performing the IFFT
    For a successful IFFT operation, the spectrum should typically
    be conjugate symmetric for real-valued signals.

    All the checks in the test are done; it will not stop checking
    once the 1st failure is detected, to print all the problems
    that were detected.

    Parameters:
    spectrum (numpy.ndarray): spectrum to make symmetric

    Returns:
    bool: True if symmetric, false if not, all within the default tolerance
    """
    retVal = True
    N = len(spectrum)
    # DC component should be real
    # if spectrum[0] != spectrum[0].real:
    # if spectrum[0].imag != 0.0:
    if not numpy.isclose(spectrum[0].imag, 0):
        log.error(f"DC component of spectrum {spectrum[0]} is not real.")
        retVal = False
    if N % 2 != 0:  # Spectrum shall consist of even number of elements
        log.error("Spectrum does not consist of odd number of elements.")
        retVal = False
    else:
        nyquistFreq = spectrum[N//2]
        # Nyquist frequency shall be real
        if not numpy.isclose(nyquistFreq.imag, 0.0, rtol=1e-05, atol=1e-07 ):
            log.error(f"Nyquist frequency {nyquistFreq} is not a real number.")
            retVal = False
    if not numpy.allclose(spectrum[1:N//2], numpy.conj(spectrum[-1:N//2:-1]),
                      rtol=1e-05, atol=1e-08):  # Verify conjugate symmetry
        log.error("Conjugate symmetry test failed.")
        retVal = False

    return retVal


def enforceConjugateSymmetry(spectrum: numpy.ndarray) -> numpy.ndarray:
    """
    For a successful IFFT operation, the spectrum should typically
    be conjugate symmetric for real-valued signals - otherwise
    the result of IFFT might be other than expected, causing an issue.
    This function ensures that the spectrum has the proper symmetry
    for a real-valued signal. Apply this to your spectrum before
    performing the IFFT, and it should help resolve the issue.

    Parameters:
    spectrum (numpy.ndarray): spectrum to make symmetric

    Returns:
    numpy.ndarray: conjugate symmetric spectrum
    """
    N = len(spectrum)
    # DC component must be real
    spectrum[0] = spectrum[0].real
    if N % 2 == 0:
        # Nyquist frequency must be real
        spectrum[N//2] = spectrum[N//2].real
    # Enforce conjugate symmetry
    spectrum[1:N//2] = numpy.conj(spectrum[-1:N//2:-1])  

    return spectrum


def calibrate(volts: numpy.ndarray, cnl: float, hs: float,
              calSpec: numpy.ndarray, calFreq: numpy.ndarray,
              fSample: float) -> numpy.ndarray:
    """
    calibrate sound record using regular FFT
    (functions numpy.fft.fft(), numpy.fft.ifft())

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

    # Make high-pass filter to remove slow varying DC offset
    # 5th order Butterworth filter with a critical frequency 10/sampling rate
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
    fmax = calFreq[len(calFreq) - 1]
    df = fmax * 2 / len(signal)
    # generate a set of frequencies as ndarray
    freqFFT = numpy.arange(0, fmax + df, df)
    # MC note: the interpolation function numpy.interp() has a different
    #          params order compared with matlab function interp1()
    # calSpecInt = numpy.interp(freqFFT, calFreq, calSpec)

    # --- Let's try scipy.interpolate.interp1d instead ---
    # Create the interpolation function
    # (which could be extracted from this library function
    # and done only once per calibration file, not per each data file)
    interp_func = scipy.interpolate.interp1d(calFreq, calSpec,
                                             kind='linear',
                                             fill_value="extrapolate")
    # Interpolate the values (results are the same as with numpy.interp())
    calSpecInt = interp_func(freqFFT)

    # Ignore calibration values below 5 Hz to avoid inadequate correction
    N5Hz = numpy.where(freqFFT <= 5)[0]
    calSpecInt[N5Hz] = calSpecInt[N5Hz[-1]]

    if doWriteIntermediateResults:
        numpy.savetxt('freq_fft.txt', freqFFT, fmt='%.3f')
        numpy.savetxt('calSpecInt.txt', calSpecInt)

    # debugging...
    log.debug(f'cal spec beg {calSpecInt[0:3]}')
    log.debug(f'cal spec end {calSpecInt[-3:][::-1]}')

    spec = numpy.fft.fft(signal)
    if doWriteIntermediateResults:
        numpy.savetxt('spec.txt', spec, fmt='%.10f')

    log.debug(f'sig spectrum DC offset {spec[0]}')
    log.debug(f'sig spectrum Nyquist freq {spec[spec.size//2]}')
    log.debug(f'sig spectrum real beg {spec[1:4].real}')
    log.debug(f'sig spectrum real end {spec[-3:][::-1].real}')
    log.debug(f'sig spectrum imag beg {spec[1:4].imag}')
    log.debug(f'sig spectrum imag end {spec[-3:][::-1].imag}')

    # verify signal spectrum conjugate symmetry
    if testConjugateSymmetry(spec) is not True:
        logMsg = "Signal spectrum is not conjugate symmetric."
        log.error(logMsg)
        raise IMOSAcousticCalibException(logMsg)

    # Inverse FFT
    # Different subscripting for even and odd number of audio signal samples
    # This works, but is clumsy. Simplified.
    #     if numpy.floor(len(signal) / 2) == len(signal) / 2:
    if len(signal) % 2 == 0:
        # odd number of samples
        pwrSpec = numpy.concatenate((calSpecInt[0:-1], calSpecInt[::-1][:-1]))
    else:
        # even number of samples
        pwrSpec = numpy.concatenate((calSpecInt[:], calSpecInt[::-1][:-1]))

    # log.debug(f'pwr spectrum DC offset {pwrSpec[0]}')
    # log.debug(f'pwr spectrum Nyquist freq {pwrSpec[pwrSpec.size//2]}')
    log.debug(f'pwr spectrum real beg {pwrSpec[0:3].real}')
    log.debug(f'pwr spectrum real end {pwrSpec[-3:][::-1].real}')
    log.debug(f'pwr spectrum imag beg {pwrSpec[0:3].imag}')
    log.debug(f'pwr spectrum imag end {pwrSpec[-3:][::-1].imag}')

    specToInverse = spec / numpy.sqrt(pwrSpec)
    log.debug(f"specToInverse.size = {specToInverse.size}")

    # verify calibrated spectrum conjugate symmetry
    if testConjugateSymmetry(specToInverse) is not True:
        specToInverse = enforceConjugateSymmetry(specToInverse)
        logMsg = "Calibrated spectrum to IFFT is not conjugate symmetric, symmetry enforced."
        log.warning(logMsg)
        # raise IMOSAcousticCalibException(logMsg)    

    calibratedSignal = numpy.fft.ifft(specToInverse)

    # ## THIS DIAGNOSTIC CODE MAKES SENSE ONLY WHEN WE DON OT PICK ONLY REAL COMPONENT ABOVE
    maxAbsImaginary = numpy.max(numpy.abs(calibratedSignal.imag))
    logMsg = (f"Maximum absolute value of imaginary component of calibrated signal after IFFT: {maxAbsImaginary}")
    log.info(logMsg)

    # Sanity check of the signal after IFFT - imaginary components of the signal shall be zero-ish
    if not numpy.allclose(calibratedSignal.imag, 0.0, rtol=1e-05, atol=1e-08):
        logMsg = "Calibrated signal after IFFT contains non-zero imaginary component(s)"
        log.error(logMsg)
        log.error(f"imag max = {max(numpy.absolute(calibratedSignal.imag))}")
        raise IMOSAcousticCalibException(logMsg)

    # MC note: we cut off the imaginary component and use only real,
    #          as python math libs leave non-zero imaginary component
    #          artifacts - a consequence of floats implementation
    calibratedSignal = calibratedSignal.real

    # debugging...
    # print(calibratedSignal[:5])
    # print(calibratedSignal[-5:])

    log.debug(f"calibrated signal size is: {calibratedSignal.size}")
    log.debug(f"calibrated signal sample type is: {calibratedSignal.dtype}")
    log.debug(f"calibrated signal sample size is: {calibratedSignal.itemsize} bytes")

    if doWriteIntermediateResults:
        numpy.savetxt('signal_calibrated.txt', calibratedSignal)

    return calibratedSignal


def calibrateReal(volts: numpy.ndarray, cnl: float, hs: float,
                  calSpec: numpy.ndarray, calFreq: numpy.ndarray,
                  fSample: float) -> numpy.ndarray:
    """
    calibrate sound record using real FFT
    (function numpy.fft.rfft(), numpy.fft.irfft())

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

    # Make high-pass filter to remove slow varying DC offset
    # 5th order Butterworth filter with a critical frequency 10/sampling rate
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
    fmax = calFreq[len(calFreq) - 1]
    df = fmax * 2 / len(signal)
    # generate a set of frequencies as ndarray
    freqFFT = numpy.arange(0, fmax + df, df)
    # MC note: the interpolation function numpy.interp() has a different
    #          params order compared with matlab function interp1()
    # calSpecInt = numpy.interp(freqFFT, calFreq, calSpec)

    # --- Let's try scipy.interpolate.interp1d instead ---
    # Create the interpolation function
    # (which could be extracted from this library function
    # and done only once per calibration file, not per each data file)
    interp_func = scipy.interpolate.interp1d(calFreq, calSpec,
                                             kind='linear',
                                             fill_value="extrapolate")
    # Interpolate the values (results are the same as with numpy.interp())
    calSpecInt = interp_func(freqFFT)

    # Ignore calibration values below 5 Hz to avoid inadequate correction
    N5Hz = numpy.where(freqFFT <= 5)[0]
    calSpecInt[N5Hz] = calSpecInt[N5Hz[-1]]

    if doWriteIntermediateResults:
        numpy.savetxt('freq_fft.txt', freqFFT, fmt='%.3f')
        numpy.savetxt('calSpecInt.txt', calSpecInt)

    # debugging...
    log.debug(f'cal spec beg {calSpecInt[0:3]}')
    log.debug(f'cal spec end {calSpecInt[-3:][::-1]}')

    spec = numpy.fft.rfft(signal)
    log.debug(f"spec.size = {spec.size}")
    if doWriteIntermediateResults:
        numpy.savetxt('spec.txt', spec, fmt='%.10f')

    log.debug(f'sig spectrum DC offset {spec[0]}')
    log.debug(f'sig spectrum Nyquist freq {spec[-1]}')

    # Inverse FFT
    # - no fiddling with mirroring of the power spectrum
    #   and making it symmetric needed in case of using
    #   rfft() / irfft()
    pwrSpec = calSpecInt
    log.debug(f"pwrSpec.size = {pwrSpec.size}")
    specToInverse = spec / numpy.sqrt(pwrSpec)
    log.debug(f"specToInverse.size = {specToInverse.size}")
    calibratedSignal = numpy.fft.irfft(specToInverse)

    # debugging...
    # print(calibratedSignal[:5])
    # print(calibratedSignal[-5:])

    log.debug(f"calibrated signal size is: {calibratedSignal.size}")
    log.debug(f"calibrated signal sample type is: {calibratedSignal.dtype}")
    log.debug(f"calibrated signal sample size is: {calibratedSignal.itemsize} bytes")

    if doWriteIntermediateResults:
        numpy.savetxt('signal_calibrated.txt', calibratedSignal)

    return calibratedSignal



def scale(signal: numpy.ndarray) -> (numpy.ndarray, float):
    """
    scaling of output for writing into wav file

    :param signal: audio data/signal in volts
    :param bitsPerSample: bits per sample
    :return: scaled audio signal as numpy.ndarray
    :return: scaleFactor as float
    """

    log.debug(f"Maximum abs amplitude of the calibrated signal before scaling: {numpy.max(numpy.abs(signal))}")

    # scaling as per Sasha's matlab code
    scaleFactor = 10 ** numpy.ceil(numpy.log10(numpy.max(numpy.abs(signal))))
    normalisedSignal = signal / scaleFactor

    log.info(f"Scale factor to reconstruct normalised signal is: {scaleFactor}")
    if doWriteIntermediateResults:
        numpy.savetxt('signal_normalised.txt', normalisedSignal)

    log.debug(f"Maximum abs amplitude of the normalised/scaled signal: {numpy.max(numpy.abs(normalisedSignal))}")

    return normalisedSignal, scaleFactor
