import argparse
import os
# from datetime import datetime
# from typing import Tuple
# import _io
import logging
import numpy

from IMOSPATools import rawdat
from IMOSPATools import wav
from IMOSPATools import calibration

log = logging.getLogger('IMOSPATools')
calibration.doWriteIntermediateResults = False

# err codes
# ERR_FooterNotFound = -2

# ------ the code below goes to the tool script ----------------

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Enable debug mode')
    parser.add_argument('--filename', '-f', required=True,
                        help='The name of the raw .DAT file to process.')
    parser.add_argument('--calibrate', '-c', required=False,
                        help='Calibrate, using calibration file')
    parser.add_argument('--noise', '-n', required=False, 
                        help='Calibration noise level (cnl)')
    parser.add_argument('--sensitivity', '-s', required=False,
                        help='Hydrophone sensitivity (hs)')
    parser.add_argument('--intermediate', '-i', action='store_true',
                        help='write intermediate results as csv')
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parseArgs()

    # default logging level
    logLevel = logging.INFO

    if args.debug:
        logLevel = logging.DEBUG

    logFormat = "[%(asctime)s %(filename)s->%(funcName)s():%(lineno)s] %(levelname)s: %(message)s"
    logging.basicConfig(level=logLevel, format=logFormat,
                        #  seconds resolution is good enough for logging timestamp
                        datefmt='%Y-%m-%d %H:%M:%S')

    rawFileName = args.filename
    if not os.path.exists(rawFileName):
        log.error(f'Raw dat file {rawFileName} not found!')
        exit(-1)

    if args.calibrate is not None:
        calibFileName = args.calibrate
        if not os.path.exists(calibFileName):
            log.error(f'Calibration file {calibFileName} not found!')
            exit(-1)
        if args.noise is None:
            args.noise = -90.0
        if args.sensitivity is None:
            args.sensitivity = -197.8

        if args.intermediate:
            calibration.doWriteIntermediateResults = True

    binData, numChannels, sampleRate, durationHeader, \
        startTime, endTime = rawdat.readRawFile(rawFileName)
    # debugging...
    log.debug(f"raw .DAT signal size is: {binData.size}")
    log.debug(f"raw .DAT signal type is: {type(binData)}")
    log.debug(f"min bin value in raw .DAT signal size is: {numpy.min(binData)}")
    log.debug(f"max bin value in raw .DAT signal size is: {numpy.max(binData)}")

    numOverloadedSamples = calibration.countOverload(binData)
    if numOverloadedSamples > 0:
        log.warning(f"Logger was overloaded - signal is clipped for {numOverloadedSamples} samples.")

    # calibration
    if args.calibrate is not None:
        # cnl, hs - commandline params for now, later loaded from file (csv?)
        cnl = args.noise
        hs = args.sensitivity
        calSpec, calFreq, fSample = calibration.loadPrepCalibFile(calibFileName, cnl, hs)
        volts = calibration.toVolts(binData)
        calibratedSignal = calibration.calibrate(volts, cnl, hs, calSpec, calFreq, fSample)

        scaledCalibSignal = calibration.scaleToBinary(calibratedSignal, 16)
        scaledCalibSignalInt16 = scaledCalibSignal.astype(numpy.int16)

        if args.intermediate:
            # WTF python you typeless language! 
            # The print defaults to float even for an explicit uint16!
            numpy.savetxt('signal_final_16bit_int.txt', scaledCalibSignalInt16, fmt='%d')
            # diagplot.dp.add_plot(scaledCalibSignal, "Signal final 16bit")
            # diagplot.dp.show()

        # debugging...
        log.debug(f"scaled calibrated signal size is: {scaledCalibSignalInt16.size}")
        log.debug(f"scaled calibrated signal type is: {type(scaledCalibSignalInt16)}")
        log.debug(f"scaled calibrated signal sample type is: {scaledCalibSignalInt16.dtype}")
        log.debug(f"scaled calibrated signal sample size is: {scaledCalibSignalInt16.itemsize} bytes")

        if scaledCalibSignalInt16 is not None:
            # write calibrated wav file
            wav.writeMono16bit(log, rawFileName, sampleRate, scaledCalibSignalInt16)
        else:
            logMsg = "Something went wrong, there is no audio signal data to write to wav file."
            log.error(logMsg)
    else:
        if binData is not None:
            # write raw wav file
            # !@#$%^& TODO: convert uint16 to int16
            wav.writeMono16bit(log, rawFileName, sampleRate, binData)
