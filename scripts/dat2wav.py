#!/usr/bin/python3
import argparse

import os
from datetime import datetime
from typing import Tuple
import _io
import logging

from IMOSPATools import rawdat
from IMOSPATools import wav
from IMOSPATools import calibration

log = logging.getLogger('IMOSPATools')

# err codes
# ERR_FooterNotFound = -2

# ------ the code below goes to the tool script ----------------

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode')
    parser.add_argument('--filename', '-f', required=True, help='The name of the raw .DAT file to process.')
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
        log.error(f'File {rawFileName} not found!')
        exit(-1)

    binData, numChannels, sampleRate, durationHeader, \
    startTime, endTime = rawdat.readRawFile(rawFileName)
    
    # calibration code sketch
    # # CalibFName = commandline parameter
    # # cnl, hs - commandline params for now, later loaded from file (csv?)
    # calSpec, calFreq, fSample = calibration.loadPrepCalibFile(CalibFName, cnl, hs)
    # volts = calibration.toVolts(binData)
    # calibratedSignal = calibration.calibrate(volts, cnl, hs, calSpec, calFreq, fSample)
    #
    # TODO: shuffling with the signal before writing it to Wav file 

    if binData is not None:
        # write wav file
        wav.writeMono16bit(log, rawFileName, sampleRate, binData)
