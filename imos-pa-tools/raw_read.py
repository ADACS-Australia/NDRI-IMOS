#!/usr/bin/python3

import re
import os
import numpy
import sys
import wave
from datetime import datetime
from typing import Tuple
import _io

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
#ERR_FooterNotFound = -2


class IMOSAcousticReadException(Exception):
    pass

    
# Assumes file is already open!
def readDatHeader(file: _io.BufferedReader) -> Tuple[int, float, float]:
    header = []
    for lineNum in range(0, numLinesHeader):
        line = file.readline()
        print(f'{lineNum} {line}')
        header.append(line.decode("utf-8"))
        
    regExp = r"Sample Rate (\d+) Duration (\d+)"
    match = re.match(regExp, header[2])
    if match:
        rate = float(match.group(1))
        duration = float(match.group(2))            
    else:
        print('Sample Rate or Duration not found!')
        raise IMOSAcousticReadException("Sample Rate or Duration not found in header of file " + file.name)

    regExp = r"Filter 0 C0=(\d) C1=(\d) LF=(\d+) HF=(\d+) PG=(\d+) G=(\d+)"
    match = re.match(regExp, header[4])
    if match:
        isCh0 = int(match.group(1))
        isCh1 = int(match.group(2))            
    else:
        print('Channel 0 and 1 presence not found!')
        raise IMOSAcousticReadException("Channel 0 and 1 indication not found in header of file " + file.name)
    
    regExp = r"Filter 1 C0=(\d) C1=(\d) LF=(\d+) HF=(\d+) PG=(\d+) G=(\d+)"
    match = re.match(regExp, header[5])
    if match:
        isCh2 = int(match.group(1))
        isCh3 = int(match.group(2))            
    else:
        print('Channel 2 and 3 indication not found!')
        raise IMOSAcousticReadException("Channel 2 and 3 indication not found in header of file " + file.name)

    numCh = isCh0 + isCh1 + isCh2 + isCh3
    
    return numCh, rate, duration


# Assumes file is already open!
def readDatBinData(file: _io.BufferedReader, sampleRate: float, durationHeader: float) -> numpy.ndarray:
    numSamplesHeader = sampleRate * durationHeader
    print(f'numSamplesHeader is {numSamplesHeader}')
        
    # read the nominal chunk of sound record as numpy array of int16
    binData = numpyfrombuffer(file.read(numSamplesHeader *
                                      numpy.dtype(numpy.int16).itemsize),
                            dtype=numpy.int16)
    print(f'Size of read bin data numpy array is {binData.size}')
        
    # store the position where the binary data tail begins
    binDataTailPos = file.tell()
    print(f'>>> file position after bin data as per header is {binDataTailPos}')
                
    fileDataTail = file.read()
    match = re.search(b"Record Marker", fileDataTail)
    if match:
        footerPos = match.start()
    else:
        print('Footer (Record Marker) not found!')
        raise IMOSAcousticReadException("Footer (Record Marker) not found in file " + file.name + ". File corrupted?")
        # exit(ERR_FooterNotFound)
        return False
            
    print(f'footer position = {footerPos}')
        
    # rewind the file to the position where the binary data tail begins
    file.seek(binDataTailPos, os.SEEK_SET)
      
    pos = file.tell()
    print(f'>>> file position before read bin data tail is {pos}')
        
    # read the extra sound record as numpy array of int16
    extraSamplesInBinDataTail = (footerPos - 1) // 2
    binDataTail = numpy.frombuffer(file.read(extraSamplesInBinDataTail * 
                                          numpy.dtype(numpy.int16).itemsize),
                                dtype=numpy.int16)
    print(f'Size of extra bin data tail numpy array is {binDataTail.size}')
        
    binData = numpy.append(binData, binDataTail)
    print(f'Size of complete data is {binData.size}')
    
    return binData


# Assumes file is already open!
def readTimesFromFooter(file: _io.BufferedReader, fileOffset: int) -> Tuple[datetime, datetime]:
    file.seek(fileOffset, os.SEEK_SET)
    fileDataTail = file.read()
    match = re.search(b"Record Marker", fileDataTail)
    if match:
        footerPos = match.start()
    else:
        print('Footer (Record Marker) not found!')
        raise IMOSAcousticReadException("Footer (Record Marker) not found in file " + file.name + ". File corrupted?")
        return False

    # read the footer ("record marker")
    for lineNum in range(0, numLinesFooter):
        line = file.readline()
        print(f'{lineNum} {line}')
        footer.append(line.decode("utf-8"))
    
    regExp = r'(\d{4}/\d{2}/\d{2}) (\d{2}:\d{2}:\d{2})'
    
    match = re.search(regExp, footer[1])
    if match:
        date_str, time_str = match.groups()    
        startTime = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
        print(f"The decoded datetime is: {startTime}")
    else:
        print("First Data timestamp not found in Footer.")
        raise IMOSAcousticReadException("First Data timestamp not found in Footer of file " + file.name + ". File corrupted?")
        return False

    match = re.search(regExp, footer[2])
    if match:
        date_str, time_str = match.groups()    
        endTime = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
        print(f"The decoded datetime is: {startTime}")
    else:
        print("First Data timestamp not found in Footer.")
        raise IMOSAcousticReadException("Finalised timestamp not found in Footer of file " + file.name + ". File corrupted?")
        return False

    return startTime, endTime


if __name__ == "__main__":

    datFileName = sys.argv[1]
    if not os.path.exists(datFileName):
        print(f'File {datFileName} not found!')
        exit(-1)            
        
    # with open('54842511.DAT', 'rb') as file:
    with open(datFileName, 'rb') as file:
        numChannels, sampleRate, durationHeader = readDatHeader(file)

        #-----------------------------------------------------------
        
        numSamplesHeader = sampleRate * durationHeader
        print(f'numSamplesHeader is {numSamplesHeader}')
        
        #-----------------------------------------------------------
        
        # !@#$%^&* Warning: assuming single channel only,
        # eg: C0=1 C1=0 C2=0 C3=0 in the header.
        # as Sasha Gavrilov suggested there are no data files 
        # with more than one channel              
        
        binData = readDatBinData(file, sampleRate, durationHeader)
        fileTailOffset = file.tell()
                
        #-------------------------------------------------------------------
        
        startTime, endTime = readTimesFromFooter(file, fileTailOffset)
        
        file.close()
        
        # write wav file
        
        # Generate the new filename with the .wav suffix
        if datFileName.endswith(".DAT"):
            wavFileName = datFileName.rsplit('.', 1)[0] + '.wav'
        else:
            wavFileName = datFileName + '.wav'

        # Open the WAV file
        with wave.open(wavFileName, 'w') as wavFile:
            # Set the parameters of the output file
            wavFile.setnchannels(1) # mono
            wavFile.setsampwidth(2) # in bytes, 16bit samples
            wavFile.setframerate(sampleRate)
            wavFile.setnframes(binData.size)
            wavFile.writeframes(binData.tobytes())
