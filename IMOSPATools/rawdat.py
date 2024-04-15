import re
import os
import numpy
from datetime import datetime, timedelta
from typing import Tuple
import _io
import logging
from typing import Final

# --- Example header ---
#   Record Header-       E24 set# 3444
#   Schedule 1 2016/10/02 00:00:01 - 48836
#   Sample Rate 06000 Duration 0000000300
#   Filter 0 C0=1 C1=0 LF=008 HF=02800 PG=010 G=001
#   Filter 1 C2=0 C3=0 LF=008 HF=05000 PG=001 G=001
NUM_LINES_HEADER: Final[int] = 5

# --- Example footer ---
#   Record Marker
#   First Data-2016/10/02 00:00:01 - 49926
#   Finalised -2016/10/02 00:05:09 - 01096
#   Data Validity - data is ok
#   Data to RAM = 0
#   Data block size = 0065536
# Note: some older files have only the first 4 lines of the footer
NUM_LINES_FOOTER: Final[int] = 4

# err codes
# ERR_FooterNotFound = -2

BITS_PER_SAMPLE: Final[int] = 16


log = logging.getLogger('IMOSPATools')

class IMOSAcousticReadException(Exception):
    pass


# Assumes file is already open!
def readRawHeader(file: _io.BufferedReader) -> Tuple[int, float, float]:
    header = []
    for lineNum in range(0, NUM_LINES_HEADER):
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
def readRawBinData(file: _io.BufferedReader, sampleRate: float, durationHeader: float) -> numpy.ndarray:
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
def readRawTimesFromFooter(file: _io.BufferedReader, fileOffset: int = 0) -> Tuple[datetime, datetime]:
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
    for lineNum in range(0, NUM_LINES_FOOTER):
        line = file.readline()
        log.debug(f'{lineNum} {line}')
        footer.append(line.decode("utf-8"))

    regExpDatetime = r'(\d{4}/\d{2}/\d{2}) (\d{2}:\d{2}:\d{2})'
    regExpSubseconds = r'(\d{5})$'

    match = re.search(regExpDatetime, footer[1])
    if match:
        date_str, time_str = match.groups()
        startTime = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
        log.debug(f"\'First Data\' timestamp without sub-seconds is: {startTime}")
    else:
        logMsg = "First Data timestamp not found in Footer of file " + file.name + ". File corrupted?"
        log.error(logMsg)
        raise IMOSAcousticReadException(logMsg)
        return False
    match = re.search(regExpSubseconds, footer[1])
    if match:
        startTime += timedelta(seconds=float(match[1])/(float)(1<<16))
        log.info(f"\'First Data\' timestamp is: {startTime}")
    else:
        logMsg = "First Data timestamp sub-seconds not found in Footer of file " + file.name + ". File corrupted?"
        log.error(logMsg)
        raise IMOSAcousticReadException(logMsg)
        return False
    
    match = re.search(regExpDatetime, footer[2])
    if match:
        date_str, time_str = match.groups()
        endTime = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
        log.debug(f"\'Finalised\' timestamp is: {endTime}")
    else:
        logMsg = "Finalised timestamp not found in Footer of file " + file.name + ". File corrupted?"
        log.error(logMsg)
        raise IMOSAcousticReadException(logMsg)
        return False
    match = re.search(regExpSubseconds, footer[2])
    if match:
        endTime += timedelta(seconds=float(match[1])/(float)(1<<16))
        log.info(f"\'Finalised\' timestamp without sub-seconds is: {endTime}")
    else:
        logMsg = "Finalised timestamp sub-seconds not found in Footer of file " + file.name + ". File corrupted?"
        log.error(logMsg)
        raise IMOSAcousticReadException(logMsg)
        return False
    

    return startTime, endTime
