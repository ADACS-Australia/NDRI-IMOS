#!/usr/bin/python3

import re
import os
import numpy as np
import sys
import wave

# Record Header-       E24 set# 3444
# Schedule 1 2016/10/02 00:00:01 - 48836
# Sample Rate 06000 Duration 0000000300
# Filter 0 C0=1 C1=0 LF=008 HF=02800 PG=010 G=001
# Filter 1 C2=0 C3=0 LF=008 HF=05000 PG=001 G=001
#
# Record Marker
# First Data-2016/10/02 00:00:01 - 49926
# Finalised -2016/10/02 00:05:09 - 01096
# Data Validity - data is ok 
# Data to RAM = 0
# Data block size = 0065536

if __name__ == "__main__":

    datFileName = sys.argv[1]
    if not os.path.exists(datFileName):
        print(f'File {datFileName} not found!')
        exit(-1)            
        
    header = []
    footer = []
    # with open('54842511.DAT', 'rb') as file:
    with open(datFileName, 'rb') as file:
        # read the header
        for lineNum in range(1,6):
            line = file.readline()
            print(f'{lineNum} {line}')
            header.append(line.decode("utf-8"))

        pos = file.tell()
        print(f'>>> file position after reading header is {pos}')

        regExp = r"Sample Rate (\d+) Duration (\d+)"
        match = re.match(regExp, header[2])
        if match:
            sampleRate = int(match.group(1))
            durationSeconds = int(match.group(2))            
        else:
            print('Sample Rate or Duration not found!')
        
        numSamplesHeader = sampleRate * durationSeconds
        print(f'numSamplesHeader is {numSamplesHeader}')
        
        # !@#$%^&* TODO: so far assuming single channel only
        # but there could be more (see C0=1 C1=0 C2=0 C3=0 in the header.
        # and the matlab code)
        
        # read the nominal chunk of sound record as numpy array of int16
        binData = np.frombuffer(file.read(numSamplesHeader *
                                          np.dtype(np.int16).itemsize),
                                dtype=np.int16)
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
            exit(-1)
            
        print(f'footer position = {footerPos}')
        
        # rewind the file to the position where the binary data tail begins
        file.seek(binDataTailPos, os.SEEK_SET)
        
        pos = file.tell()
        print(f'>>> file position before read numpy data tail is {pos}')
        
        # read the extra sound record as numpy array of int16
        extraSamplesInBinDataTail = (footerPos - 1) // 2
        binDataTail = np.frombuffer(file.read(extraSamplesInBinDataTail * 
                                              np.dtype(np.int16).itemsize),
                                    dtype=np.int16)
        print(f'Size of extra bin data tail numpy array is {binDataTail.size}')
        
        binData = np.append(binData, binDataTail)
        print(f'Size of complete data is {binData.size}')
        
        # jump one byte ahead, there is an extra newline
        file.seek(binDataTailPos + footerPos, os.SEEK_SET)
        pos = file.tell()
        print(f'>>> file position is {pos}')
        
        # read the footer ("record marker")
        for lineNum in range(1,5):
            line = file.readline()
            print(f'{lineNum} {line}')
            footer.append(line.decode("utf-8"))               

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
