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
    parser.add_argument('--output', '-o', type=str,
                        choices=['wav', 'flac'], default="wav",
                        help='Output audio file format (wav, flac)')
    parser.add_argument('--calibrate', '-c', required=False,
                        help='Calibrate, using calibration file')
    parser.add_argument('--noise', '-n', type=float,
                        required=False,
                        help='Calibration noise level (cnl)')
    parser.add_argument('--sensitivity', '-s', type=float,
                        required=False,
                        help='Hydrophone sensitivity (hs)')
    parser.add_argument('--intermediate', '-i', action='store_true',
                        help='Write intermediate results as single column text file')
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
            log.warning(f"Calibration noise level not provided, using default {args.noise}")
        if args.sensitivity is None:
            args.sensitivity = -196.0
            log.warning(f"Hydrophone sensitivity not provided, using default {args.sensitivity}")

        if args.intermediate:
            # calibration.doWriteIntermediateResults is initialised \
            # to False in the calibration module
            calibration.doWriteIntermediateResults = True

    binData, numChannels, sampleRate, durationHeader, \
        startTime, endTime = rawdat.readRawFile(rawFileName)

    essentialMetadata = audiofile.MetadataEssential(
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
        # calibratedSignal = calibration.calibrate(volts, cnl, hs, calSpec, calFreq, sampleRate)
        calibratedSignal = calibration.calibrateReal(volts, cnl, hs, calSpec, calFreq, sampleRate)
        scaledSignal, scaleFactor = calibration.scale(calibratedSignal)
        essentialMetadata.scaleFactor = scaleFactor

        # debugging...
        log.debug(f"scaled calibrated signal size is: {scaledSignal.size}")
        log.debug(f"scaled calibrated signal type is: {type(scaledSignal)}")
        log.debug(f"scaled calibrated signal sample type is: {scaledSignal.dtype}")
        log.debug(f"scaled calibrated signal sample size is: {scaledSignal.itemsize} bytes")

        if scaledSignal is not None:
            if args.intermediate:
                scaledSignalInt16 = wav.scaleSignalFloatTo16bitPCM(scaledSignal)
                numpy.savetxt('signal_scaled.txt', scaledSignalInt16)

            if args.output == 'wav':
                # write calibrated wav file with 'audiofile' package library
                wavFileName = audiofile.deriveOutputFileName(rawFileName, 'wav')
                audiofile.writeMono16bit(wavFileName, sampleRate,
                                         scaledSignal, essentialMetadata, 'WAV')
            elif args.output == 'flac':
                # write calibrated flac file with 'audiofile' package library
                wavFileName = audiofile.deriveOutputFileName(rawFileName, 'flac')
                audiofile.writeMono16bit(wavFileName, sampleRate,
                                         scaledSignal, essentialMetadata, 'FLAC')
        else:
            logMsg = "Something went wrong, there is no audio signal data to write to wav file."
            log.error(logMsg)
    else:
        if binData is not None:
            # Cannot just save binary data blob to wave,
            # need to convert uint16 to int16
            # Steps: convert to volts, normalise and scale back to signed int16
            volts = calibration.toVolts(binData)
            scaledSignal, scaleFactor = calibration.scale(volts)
            if args.output == 'wav':
                scaledSignalInt16 = wav.scaleSignalFloatTo16bitPCM(scaledSignal)
                # write normalised scaled but still raw uncalibrated data into a wav file
                wavFileName = wav.deriveWavFileName(rawFileName)
                wav.writeMono16bit(wavFileName, sampleRate, scaledSignalInt16)
            elif args.output == 'flac':
                essentialMetadata.scaleFactor = scaleFactor
                # write calibrated flac file with 'audiofile' package library
                wavFileName = audiofile.deriveOutputFileName(rawFileName, 'flac')
                audiofile.writeMono16bit(wavFileName, sampleRate,
                                         scaledSignal, essentialMetadata, 'FLAC')
        else:
            logMsg = "Something went wrong, there is no audio signal data to write to wav file."
            log.error(logMsg)
