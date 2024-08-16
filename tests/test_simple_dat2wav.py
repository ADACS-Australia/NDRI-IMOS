import os
import logging
import numpy

from IMOSPATools import rawdat
from IMOSPATools import wav
from IMOSPATools import calibration
from IMOSPATools import audiofile

log = logging.getLogger('IMOSPATools')
calibration.doWriteIntermediateResults = False


def simple_dat2wav(rawFileName: str) -> bool:
    """
    Test conversion from raw DAT file to MS wave
    - No calibration included.
    - Only simple read, convert to volts, normalise and write as wav.
    - Metadata not included in the wav header
    - using python wav package
    """
    if not os.path.exists(rawFileName):
        log.error(f'Raw dat file {rawFileName} not found!')
        raise AssertionError(f"FAILED: the following test data file does not exist: {rawFileName}")

    try:
        binData, numChannels, sampleRate, durationHeader, \
            startTime, endTime = rawdat.readRawFile(rawFileName)
    except rawdat.IMOSAcousticRAWReadException:
        raise AssertionError(f"FAILED: read raw DAT file {rawFileName}")

    # debugging...
    log.debug(f"raw .DAT signal size is: {binData.size}")
    log.debug(f"raw .DAT signal type is: {type(binData)}")
    log.debug(f"min bin value in raw .DAT signal size is: {numpy.min(binData)}")
    log.debug(f"max bin value in raw .DAT signal size is: {numpy.max(binData)}")

    if binData is not None:
        try:
            # Cannot just save binary data blob to wave,
            # need to convert uint16 to int16
            # Steps: convert to volts, normalise and scale back to signed int16
            volts = calibration.toVolts(binData)
            scaledSignalInt16 = wav.scaleSignalFloatTo16bitPCM(volts)

            # write normalised scaled but still raw uncalibrated data into a wav file
            wavFileName = wav.deriveWavFileName(rawFileName)
            wav.writeMono16bit(wavFileName, sampleRate, scaledSignalInt16)
        except rawdat.IMOSAcousticRAWReadException:
            raise AssertionError(f"FAILED: normalise and write wave file {wavFileName}")
    else:
        logMsg = "Something went wrong, there is no audio signal data to write to a wav file."
        log.error(logMsg)
        raise AssertionError(logMsg)

    return True


def test_simple_dat2wav():
    dat1 = 'tests/data/Rottnest_3154/502DB01D.DAT'
    dat2 = 'tests/data/KI_3501/583E9500.DAT'
    dat3 = 'tests/data/Portland_3092/4F480851.DAT'
    simple_dat2wav(dat1)
    simple_dat2wav(dat2)
    simple_dat2wav(dat3)


if __name__ == "__main__":

    # set debugging logging level so we see as much as pos in testing
    logLevel = logging.DEBUG

    logFormat = "[%(asctime)s %(filename)s->%(funcName)s():%(lineno)s] %(levelname)s: %(message)s"
    logging.basicConfig(level=logLevel, format=logFormat,
                        #  seconds resolution is good enough for logging timestamp
                        datefmt='%Y-%m-%d %H:%M:%S')

    test_simple_dat2wav()
