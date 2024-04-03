#!/usr/bin/python3
import argparse

import os
from datetime import datetime
from typing import Tuple
import _io
import logging

from IMOSPATools import rawdat
from IMOSPATools import wav

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

    with open(rawFileName, 'rb') as file:
        try:
            numChannels, sampleRate, durationHeader = rawdat.readRawHeader(file)
        except rawdat.IMOSAcousticReadException as E:
            # print(E)
            exit(-1)

        binDataSuccess = False
        # !@#$%^&* Warning: assuming single channel only,
        # eg: C0=1 C1=0 C2=0 C3=0 in the header.
        # as Sasha Gavrilov suggested there are no data files
        # with more than one channel
        try:
            binData = rawdat.readRawBinData(file, sampleRate, durationHeader)
            binDataSuccess = True
        except rawdat.IMOSAcousticReadException as E:
            # print(E)
            exit(-1)
        fileTailOffset = file.tell()

        startTime, endTime = rawdat.readRawTimesFromFooter(file, fileTailOffset)
        
        # done reading input raw/.DAT file
        file.close()

        if binDataSuccess:
            # write wav file
            wav.write(log, rawFileName, sampleRate, binDataSuccess, binData)
