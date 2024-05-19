import re
import os
import numpy
from datetime import datetime, timedelta, timezone
from typing import Tuple
import _io
import logging
from typing import Final
from dataclasses import dataclass, field

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

REGEXP_DATETIME: Final[str] = r'(\d{4}/\d{2}/\d{2}) (\d{2}:\d{2}:\d{2})'
REGEXP_SUBSECONDS: Final[str] = r'(\d{5})$'
REGEXP_SAMPLE_RATE: Final[str] = r"Sample Rate (\d+) Duration (\d+)"
REGEXP_FILTER: Final[str] = r"Filter [0,1] C[0-3]=(\d+) C[0-3]=(\d+)"


@dataclass
class RAWFileFilterLine:
    channelA: bool = 0
    channelB: bool = 0
    lowFreq: int = -1
    highFreq: int = -1
    pGain: int = -1
    gain: int = -1


@dataclass
class RAWFileHeader:
    recordHeader: str = ""
    # not always can be set extracted from the RAW file header.
    # if not known, -1 is used.
    setID: int = -1
    schedule: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    sampleRate: int = -1
    duration: int = -1
    filter0: RAWFileFilterLine = field(default_factory=RAWFileFilterLine)
    filter1: RAWFileFilterLine = field(default_factory=RAWFileFilterLine)


@dataclass
class RAWFileFooter:
    recordHeader: str = ""
    startTime: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    endTime: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    dataValidity: str = "no idea"
    dataToRAM: bool = 0
    dataBlockSize: int = 65536


log = logging.getLogger('IMOSPATools')

class IMOSAcousticRAWReadException(Exception):
    pass


def convertHeaderTime(line: str, timeLabel: str) -> datetime:
    """
    Convert time string found in RAW file header into datetime class

    :param line: line of the header that contains time
    :param limeLabel: label of the time for log prints
    :return: time in datetime class format
    """
    match = re.search(REGEXP_DATETIME, line)
    if match:
        date_str, time_str = match.groups()
        dateTime = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
        log.debug(f"\'{timeLabel}\' timestamp without sub-seconds is: {dateTime}")
    else:
        logMsg = f"\'{timeLabel}\' timestamp not found in Footer of file {file.name}. File corrupted?"
        log.error(logMsg)
        raise IMOSAcousticRAWReadException(logMsg)
        return False
    match = re.search(REGEXP_SUBSECONDS, line)
    if match:
        dateTime += timedelta(seconds=float(match[1])/(float)(1<<16))
        log.info(f"\'{timeLabel}\' timestamp is: {dateTime}")
    else:
        logMsg = f"\'{timeLabel}\' timestamp sub-seconds not found in Footer of file {file.name}. File corrupted?"
        log.error(logMsg)
        raise IMOSAcousticRAWReadException(logMsg)
        return False
    
    return dateTime


def readRawHeaderEssentials(file: _io.BufferedReader) -> Tuple[int, float, float]:
    """
    Read essential parameters from RAW file header
    Assumes file is already open!
    
    :param file: already open file
    :return: number of channels, sampling rate, record duration
    """
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
        raise IMOSAcousticRAWReadException(logMsg)

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
        raise IMOSAcousticRAWReadException(logMsg)

    # regExp = r"Filter 1 C2=(\d) C3=(\d) LF=(\d+) HF=(\d+) PG=(\d+) G=(\d+)"
    match = re.match(regExp, header[4])
    if match:
        isCh2 = int(match.group(1))
        isCh3 = int(match.group(2))
    else:
        logMsg = "Channel 2 and 3 indication not found in header of file " + file.name
        log.error(logMsg)
        raise IMOSAcousticRAWReadException(logMsg)

    numCh = isCh0 + isCh1 + isCh2 + isCh3
    
    if numCh != 1:
        logMsg = f"Unexpected number of channels ({numCh}) in file {file.name}"
        log.error(logMsg)
        raise IMOSAcousticRAWReadException(logMsg)

    return numCh, rate, duration


def readRawBinData(file: _io.BufferedReader, sampleRate: float, durationHeader: float) -> numpy.ndarray:
    """
    Read binary data block (audio recording) from RAW file
    Assumes file is already open!
    
    :param file: already open file
    :return: sampling rate
    :return: record duration as read from the header 
        (in reality little longer, need to scan for footer marker to figure out)
    :return: audio data as numpy array
    """
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
        raise IMOSAcousticRAWReadException(logMsg)
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


def readRawTimesFromFooter(file: _io.BufferedReader, fileOffset: int = 0) -> Tuple[datetime, datetime]:
    """
    Read  from RAW file
    Assumes file is already open!
    
    :param file: already open file
    :return: record start time and end time from the footer, as datetime class
    """
    file.seek(fileOffset, os.SEEK_SET)
    fileDataTail = file.read()
    match = re.search(b"Record Marker", fileDataTail)
    if match:
        footerPos = match.start()
    else:
        logMsg = "Footer (Record Marker) not found in file " + file.name + ". File corrupted?"
        log.error(logMsg)
        raise IMOSAcousticRAWReadException(logMsg)
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

    startTime = convertHeaderTime(footer[1], 'First Data')
    endTime = convertHeaderTime(footer[2], 'Finalised')

    return startTime, endTime


def readRawFile(fileName: str) -> (numpy.ndarray, Tuple[int, float, float, datetime, datetime]):
    """
    Read RAW file
        
    :param fileName: file name (can be relative/full path) 
    
    :return: sampling rate
    :return: audio data as numpy array (None if failed to read)
    :return: number of channels, sampling rate,
    :return: record duration as read from the header
    :return: record start time and end time from the footer, as datetime class        
    """
    binData = None
    
    with open(fileName, 'rb') as file:
        try:
            numChannels, sampleRate, durationHeader = readRawHeaderEssentials(file)
        except IMOSAcousticRAWReadException as E:
            # print(E)
            exit(-1)

        binDataSuccess = False
        # !@#$%^&* Warning: assuming single channel only,
        # eg: C0=1 C1=0 C2=0 C3=0 in the header.
        # as Sasha Gavrilov suggested there are no data files
        # with more than one channel
        try:
            binData = readRawBinData(file, sampleRate, durationHeader)
        except IMOSAcousticRAWReadException as E:
            # print(E)
            exit(-1)
        fileTailOffset = file.tell()

        startTime, endTime = readRawTimesFromFooter(file, fileTailOffset)
        
        # done reading input raw/.DAT file
        file.close()
        
        return binData, numChannels, sampleRate, durationHeader, startTime, endTime
        
