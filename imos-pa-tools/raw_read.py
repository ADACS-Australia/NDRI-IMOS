#!/usr/bin/python3
import re
import os
import numpy
from datetime import datetime
from typing import Tuple
import _io
import logging

log = logging.getLogger('imos-pa-tools')

# --- Example header ---
#   Record Header-       E24 set# 3444
#   Schedule 1 2016/10/02 00:00:01 - 48836
#   Sample Rate 06000 Duration 0000000300
#   Filter 0 C0=1 C1=0 LF=008 HF=02800 PG=010 G=001
#   Filter 1 C2=0 C3=0 LF=008 HF=05000 PG=001 G=001
numLinesHeader = 5

# --- Example footer ---
#   Record Marker
#   First Data-2016/10/02 00:00:01 - 49926
#   Finalised -2016/10/02 00:05:09 - 01096
#   Data Validity - data is ok
#   Data to RAM = 0
#   Data block size = 0065536
# Note: some older files have only the first 4 lines of the footer
numLinesFooter = 4

# err codes
# ERR_FooterNotFound = -2


class IMOSAcousticReadException(Exception):
    pass


# Assumes file is already open!
def readDatHeader(file: _io.BufferedReader) -> Tuple[int, float, float]:
    header = []
    for lineNum in range(0, numLinesHeader):
        line = file.readline()
        log.debug(f'{lineNum} {line}')
        header.append(line.decode("utf-8"))

    regExp = r"Sample Rate (\d+) Duration (\d+)"
    match = re.match(regExp, header[2])
    if match:
        rate = float(match.group(1))
        duration = float(match.group(2))
    else:
        logMsg = "\'Sample Rate\' or \'Duration\' not found in header of file " + file.name
        log.error(logMsg)
        raise IMOSAcousticReadException(logMsg)

    # regExp = r"Filter 0 C0=(\d+) C1=(\d+) LF=(\d+) HF=(\d+) PG=(\d+) G=(\d+)"
    # optimised - decode only what we need
    regExp = r"Filter [0,1] C[0-3]=(\d+) C[0-3]=(\d+)"
    
    match = re.match(regExp, header[3])
    if match:
        isCh0 = int(match.group(1))
        isCh1 = int(match.group(2))
    else:
        logMsg = "Channel 0 and 1 indication not found in header of file " + file.name
        log.error(logMsg)
        raise IMOSAcousticReadException(logMsg)

    # regExp = r"Filter 1 C2=(\d) C3=(\d) LF=(\d+) HF=(\d+) PG=(\d+) G=(\d+)"
    match = re.match(regExp, header[4])
    if match:
        isCh2 = int(match.group(1))
        isCh3 = int(match.group(2))
    else:
        logMsg = "Channel 2 and 3 indication not found in header of file " + file.name
        log.error(logMsg)
        raise IMOSAcousticReadException(logMsg)

    numCh = isCh0 + isCh1 + isCh2 + isCh3
    
    if numCh != 1:
        logMsg = f"Unexpected numver of channels ({numCh}) in file {file.name}"
        log.error(logMsg)
        raise IMOSAcousticReadException(logMsg)

    return numCh, rate, duration


# Assumes file is already open!
def readDatBinData(file: _io.BufferedReader, sampleRate: float, durationHeader: float) -> numpy.ndarray:
    numSamplesHeader = int(sampleRate * durationHeader)
    log.debug(f'numSamplesHeader is {numSamplesHeader}')

    # read the nominal chunk of sound record as numpy array of int16
    binData = numpy.frombuffer(file.read(numSamplesHeader * numpy.dtype(numpy.int16).itemsize), dtype=numpy.int16)
    log.debug(f'Size of read bin data as per header numpy array is {binData.size}')

    # store the position where the binary data tail begins
    binDataTailPos = file.tell()
    log.debug(f'File position after bin data as per header is {binDataTailPos}')

    fileDataTail = file.read()
    match = re.search(b"Record Marker", fileDataTail)
    if match:
        footerPos = match.start()
    else:
        logMsg = "Footer (Record Marker) not found in file " + file.name + ". File corrupted?"
        log.error(logMsg)
        raise IMOSAcousticReadException(logMsg)
        return False
    
    # rewind the file to the position where the binary data tail begins
    file.seek(binDataTailPos, os.SEEK_SET)

    pos = file.tell()
    log.debug(f'file position before read bin data tail is {pos}')

    # read the extra sound record as numpy array of int16
    extraSamplesInBinDataTail = (footerPos - 1) // 2
    binDataTail = numpy.frombuffer(file.read(extraSamplesInBinDataTail * numpy.dtype(numpy.int16).itemsize), dtype=numpy.int16)
    log.debug(f'Size of extra bin data tail numpy array is {binDataTail.size}')

    binData = numpy.append(binData, binDataTail)
    log.info(f'Size of complete data is {binData.size} samples {binData.size * numpy.dtype(numpy.int16).itemsize} bytes')

    return binData


# Assumes file is already open!
def readTimesFromFooter(file: _io.BufferedReader, fileOffset: int = 0) -> Tuple[datetime, datetime]:
    file.seek(fileOffset, os.SEEK_SET)
    fileDataTail = file.read()
    match = re.search(b"Record Marker", fileDataTail)
    if match:
        footerPos = match.start()
    else:
        logMsg = "Footer (Record Marker) not found in file " + file.name + ". File corrupted?"
        log.error(logMsg)
        raise IMOSAcousticReadException(logMsg)
        return False

    footerOffset = fileOffset + footerPos
    log.debug(f'footer position = {footerOffset}')
    # fast forward to the footer offset
    file.seek(footerOffset, os.SEEK_SET)

    footer = []
    # read the footer ("record marker")
    for lineNum in range(0, numLinesFooter):
        line = file.readline()
        log.debug(f'{lineNum} {line}')
        footer.append(line.decode("utf-8"))

    regExp = r'(\d{4}/\d{2}/\d{2}) (\d{2}:\d{2}:\d{2})'

    match = re.search(regExp, footer[1])
    if match:
        date_str, time_str = match.groups()
        startTime = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
        log.info(f"\'First Data\' timestamp is: {startTime}")
    else:
        logMsg = "First Data timestamp not found in Footer of file " + file.name + ". File corrupted?"
        log.error(logMsg)
        raise IMOSAcousticReadException(logMsg)
        return False

    match = re.search(regExp, footer[2])
    if match:
        date_str, time_str = match.groups()
        endTime = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
        log.info(f"\'Finalised\' timestamp is: {endTime}")
    else:
        logMsg = "Finalised timestamp not found in Footer of file " + file.name + ". File corrupted?"
        log.error(logMsg)
        raise IMOSAcousticReadException(logMsg)
        return False

    return startTime, endTime
