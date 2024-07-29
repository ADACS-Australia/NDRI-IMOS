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
from IMOSPATools import audiofile

log = logging.getLogger('IMOSPATools')
calibration.doWriteIntermediateResults = False


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
            # calibration.doWriteIntermediateResults is initialised \
            # to False in the calibration module
            calibration.doWriteIntermediateResults = True

    binData, numChannels, sampleRate, durationHeader, \
        startTime, endTime = rawdat.readRawFile(rawFileName)

    essentialMetadataFromRaw = wav.WavMetadataEssential(
        numChannels=numChannels,
        sampleRate=sampleRate,
        durationHeader=durationHeader,
        startTime=startTime,
        endTime=endTime
    )

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
        calSpec, calFreq, calSampleRate = calibration.loadPrepCalibFile(calibFileName, cnl, hs)
        if sampleRate != calSampleRate:
            logging.error("Sample rate is different between the audio record and calibration file.")

        volts = calibration.toVolts(binData)
        calibratedSignal = calibration.calibrate(volts, cnl, hs, calSpec, calFreq, sampleRate)
        scaledSignal, scaleFactor = calibration.scale(calibratedSignal)

        # debugging...
        log.debug(f"scaled calibrated signal size is: {scaledSignal.size}")
        log.debug(f"scaled calibrated signal type is: {type(scaledSignal)}")
        log.debug(f"scaled calibrated signal sample type is: {scaledSignal.dtype}")
        log.debug(f"scaled calibrated signal sample size is: {scaledSignal.itemsize} bytes")

        if scaledSignal is not None:
            # write calibrated wav file with 'wave' package library
            wavFileName = wav.deriveWavFileName('_' + rawFileName)
            scaledSignalInt16 = wav.scaleSignalFloatTo16bitPCM(scaledSignal)
            if args.intermediate:
                numpy.savetxt('signal_scaled.txt', scaledSignalInt16)
            wav.writeMono16bit(wavFileName, sampleRate,
                               scaledSignalInt16)
            # write calibrated wav file with 'audiofile' package library
            wavFileName = audiofile.deriveOutputFileName(rawFileName, 'wav')
            audiofile.writeWavMono16bit(wavFileName, sampleRate,
                                        scaledSignal,
                                        essentialMetadataFromRaw)
        else:
            logMsg = "Something went wrong, there is no audio signal data to write to wav file."
            log.error(logMsg)
    else:
        if binData is not None:
            # Cannot just save binary data blob to wave,
            # need to convert uint16 to int16
            # Steps: convert to volts, normalise and scale back to signed int16
            volts = calibration.toVolts(binData)
            scaledSignalInt16 = wav.scaleSignalFloatTo16bitPCM(volts)

            # write normalised scaled but still raw uncalibrated data into a wav file
            wavFileName = wav.deriveWavFileName(rawFileName)
            wav.writeMono16bit(wavFileName, sampleRate, scaledSignalInt16)
        else:
            logMsg = "Something went wrong, there is no audio signal data to write to wav file."
            log.error(logMsg)
