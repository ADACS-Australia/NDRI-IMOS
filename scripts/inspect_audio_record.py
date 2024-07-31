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
                        help='The name of the audio file to inspect.')
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

    fileName = args.filename
    if not os.path.exists(fileName):
        log.error(f'Raw dat file {fileName} not found!')
        exit(-1)

    audiofile.loadInspect(fileName)

    mataJson = audiofile.extractMetadataJson(fileName)
    print(f"Metadata extracted from file {fileName} as JSON:\n{mataJson}")
