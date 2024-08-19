import argparse
import os
from datetime import timedelta
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
    descText = "Convertor for raw IMOS passive audio .DAT record to wav or flac with calibration."
    parser = argparse.ArgumentParser(description=descText)
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Enable debug mode')
    parser.add_argument('--input', '-i',
                        help='The name of the input raw audio .DAT file to process.')

    exGroup = parser.add_mutually_exclusive_group()
    exGroup.add_argument('--generate-filename', '-g', action='store_true',
                         help='Generate output filename with setID and time, must provide set ID')
    exGroup.add_argument('--output', '-o',
                        help='The name of the output audio file.')

    parser.add_argument('--format', '-f', type=str,
                        choices=['wav', 'flac'], default="wav",
                        help='Format of the output audio file (wav, flac)')
    parser.add_argument('--calibrate', '-c', required=False,
                        help='Calibrate, using calibration file')
    parser.add_argument('--noise', '-n', type=float,
                        required=False,
                        help='Calibration noise level (cnl)')
    parser.add_argument('--sensitivity', '-s', type=float,
                        required=False,
                        help='Hydrophone sensitivity (hs)')
    parser.add_argument('--setID', '-I', type=int,
                        help='Data set ID')
    parser.add_argument('--intermediate', '-m', action='store_true',
                        help='Write intermediate results as single column text file')

    args = parser.parse_args()

    # Check if --generate-filename was used without --setID
    if args.generate_filename and args.setID is None:
        log.error("Parameter --setID (-I) is required when --generate-filename (-g) is used.")
        parser.error("Parameter --setID (-I) is required when --generate-filename (-g) is used.")

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

    rawFileName = args.input
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
            # calibration.doWriteIntermediateResults is initialised
            # to False in the calibration module
            calibration.doWriteIntermediateResults = True

    if args.setID is not None:
        setID = args.setID
    else:
        setID = 0

    binData, numChannels, sampleRate, durationHeader, \
        startTime, endTime, scheduleTime = rawdat.readRawFile(rawFileName)

    durationFile = binData.size / sampleRate

    log.debug(f'endTime from .DAT file header: {endTime}')
    # cannot just add seconds - timedelta object has to be constructed
    durationTimedelta = timedelta(seconds=durationFile)
    log.debug(f'duration timedelta calculated from actual audio record duration: {durationTimedelta}')
    endTime = startTime + durationTimedelta
    log.debug(f'endTime calculated from actual audio record duration: {endTime}')

    metadata = audiofile.MetadataFull(
        setID=setID,
        schedule=scheduleTime,
        numChannels=numChannels,
        sampleRate=sampleRate,
        durationHeader=durationHeader,
        durationFile=durationFile,
        startTime=startTime,
        endTime=endTime,
        calibNoiseLevel=args.noise,
        hydrophoneSensitivity=args.sensitivity
    )

    # debugging...
    log.debug(f"raw .DAT signal size is: {binData.size}")
    log.debug(f"raw .DAT signal type is: {type(binData)}")
    log.debug(f"min bin value in raw .DAT signal size is: {numpy.min(binData)}")
    log.debug(f"max bin value in raw .DAT signal size is: {numpy.max(binData)}")

    # Sort out the output audio file name
    if args.generate_filename:
        # created/generated filename has priority
        outputFileName = audiofile.createOutputFileName(setID,
                                                        metadata.startTime,
                                                        args.format)
    elif args.output is not None:
        # explicitly specified output filename using commandline parameter
        outputFileName = args.output
    else:
        outputFileName = audiofile.deriveOutputFileName(rawFileName, args.format) 

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
        metadata.scaleFactor = scaleFactor

        # debugging...
        log.debug(f"scaled calibrated signal size is: {scaledSignal.size}")
        log.debug(f"scaled calibrated signal type is: {type(scaledSignal)}")
        log.debug(f"scaled calibrated signal sample type is: {scaledSignal.dtype}")
        log.debug(f"scaled calibrated signal sample size is: {scaledSignal.itemsize} bytes")

        if scaledSignal is not None:
            if args.intermediate:
                scaledSignalInt16 = wav.scaleSignalFloatTo16bitPCM(scaledSignal)
                numpy.savetxt('signal_scaled.txt', scaledSignalInt16)

            if args.format == 'wav':
                # write calibrated wav file with 'audiofile' package library
                audiofile.writeMono16bit(outputFileName, scaledSignal,
                                         metadata, 'WAV')
            elif args.format == 'flac':
                # write calibrated flac file with 'audiofile' package library
                audiofile.writeMono16bit(outputFileName, scaledSignal,
                                         metadata, 'FLAC')
        else:
            logMsg = "Something went wrong, there is no audio signal data to write to wav file."
            log.error(logMsg)
    else:
        # Do not calibrate, just convert the audio record file format 
        if binData is not None:
            # Cannot just save binary data blob to wave,
            # need to convert uint16 to int16
            # Steps: convert to volts, normalise and scale back to signed int16
            volts = calibration.toVolts(binData)
            scaledSignal, scaleFactor = calibration.scale(volts)
            metadata.scaleFactor = scaleFactor
            if args.format == 'wav':
                scaledSignalInt16 = wav.scaleSignalFloatTo16bitPCM(scaledSignal)
                # write normalised scaled but still raw uncalibrated data into a wav file
                # intentionally using the 'wave' package function here, not 'audiofile'
                wav.writeMono16bit(outputFileName, sampleRate, scaledSignalInt16)
            elif args.format == 'flac':
                # write calibrated flac file with 'audiofile' package library
                audiofile.writeMono16bit(outputFileName, scaledSignal,
                                         metadata, 'FLAC')
        else:
            logMsg = "Something went wrong, there is no audio signal data to write to wav file."
            log.error(logMsg)
