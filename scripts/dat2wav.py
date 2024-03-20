#!/usr/bin/python3
import argparse

import sys
import wave
from datetime import datetime
from typing import Tuple
import _io
import logging

from IMOSPATools import rawdat

log = logging.getLogger('IMOSPATools')

# err codes
# ERR_FooterNotFound = -2

# ------ the code below goes to the tool script ----------------

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode')
    parser.add_argument('--filename', '-f', help='The name of the raw .DAT file to process.')
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

    datFileName = args.filename
    if not os.path.exists(datFileName):
        log.error(f'File {datFileName} not found!')
        exit(-1)

    with open(datFileName, 'rb') as file:
        try:
            numChannels, sampleRate, durationHeader = readDatHeader(file)
        except IMOSAcousticReadException as E:
            # print(E)
            exit(-1)

        binDataSuccess = False
        # !@#$%^&* Warning: assuming single channel only,
        # eg: C0=1 C1=0 C2=0 C3=0 in the header.
        # as Sasha Gavrilov suggested there are no data files
        # with more than one channel
        try:
            binData = readDatBinData(file, sampleRate, durationHeader)
            binDataSuccess = True
        except IMOSAcousticReadException as E:
            # print(E)
            exit(-1)
        fileTailOffset = file.tell()

        startTime, endTime = readTimesFromFooter(file, fileTailOffset)
        # done reading input raw/.DAT file
        file.close()

        # write wav file
        if binDataSuccess:
            # Generate the new filename with the .wav suffix
            if datFileName.endswith(".DAT"):
                wavFileName = datFileName.rsplit('.', 1)[0] + '.wav'
            else:
                wavFileName = datFileName + '.wav'

            # Open the WAV file
            with wave.open(wavFileName, 'w') as wavFile:
                # Set the parameters of the output file
                wavFile.setnchannels(1)  # mono
                wavFile.setsampwidth(2)  # in bytes, 16bit samples
                wavFile.setframerate(sampleRate)
                wavFile.setnframes(binData.size)
                wavFile.writeframes(binData.tobytes())
    
            log.info(f"Written {wavFileName}")
