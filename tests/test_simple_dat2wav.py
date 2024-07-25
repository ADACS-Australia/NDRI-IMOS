import os
import logging
import numpy

from IMOSPATools import rawdat
from IMOSPATools import wav
from IMOSPATools import calibration
from IMOSPATools import audiofile

log = logging.getLogger('IMOSPATools')
calibration.doWriteIntermediateResults = False


def test_simple_dat2wav():
    rawFileName = 'tests/data/Rottnest_3154/502DB01D.DAT'
    if not os.path.exists(rawFileName):
        log.error(f'Raw dat file {rawFileName} not found!')
        raise AssertionError(f"FAILED: the following test data file does not exist: {rawFileName}")

    try:
        binData, numChannels, sampleRate, durationHeader, \
            startTime, endTime = rawdat.readRawFile(rawFileName)
    except:
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
            normaliasedSignal = calibration.scaleToBinary(volts,
                                                      rawdat.BITS_PER_SAMPLE)
            scaledSignalInt16 = normaliasedSignal.astype(numpy.int16)

            # write normalised scaled but still raw uncalibrated data into a wav file
            wavFileName = wav.deriveWavFileName(rawFileName)
            wav.writeMono16bit(wavFileName, sampleRate, scaledSignalInt16)
        except:
            raise AssertionError(f"FAILED: normalise and write wave file {wavFileName}")
    else:
        logMsg = "Something went wrong, there is no audio signal data to write to wav file."
        log.error(logMsg)
        raise AssertionError(logMsg)


if __name__ == "__main__":

    # set debugging logging level so we see as much as pos in testing
    logLevel = logging.DEBUG

    logFormat = "[%(asctime)s %(filename)s->%(funcName)s():%(lineno)s] %(levelname)s: %(message)s"
    logging.basicConfig(level=logLevel, format=logFormat,
                        #  seconds resolution is good enough for logging timestamp
                        datefmt='%Y-%m-%d %H:%M:%S')

    test_simple_dat2wav()
