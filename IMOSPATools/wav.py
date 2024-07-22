import wave
import numpy
import logging
from mutagen.wave import WAVE
from mutagen import MutagenError
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import json

from IMOSPATools import rawdat

log = logging.getLogger('IMOSPATools')


class IMOSAcousticWavException(Exception):
    pass


@dataclass
class WavMetadataEssential:
    numChannels: int = 1
    sampleRate: int = -1 
    durationHeader: int = 0
    startTime: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    endTime: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)


def deriveWavFileName(rawFileName: str) -> str:
    """
    Generate the wav filename from raw DAT file

    :param rawFileName: filename of the raw (DAT) file from which the vav filename shall be derived
    :return: filename of the wav file name 
    """
    # Generate the new filename with the .wav suffix
    if rawFileName.endswith(".DAT"):
        wavFileName = rawFileName.rsplit('.', 1)[0] + '.wav'
    else:
        wavFileName = rawFileName + '.wav'

    return wavFileName


def writeMono16bit(wavFileName: str,
                   sampleRate: float,
                   binData: numpy.ndarray):
    """
    Write simple mono wav file, 16bit per sample

    Warning: assuming single channel only,
    as Sasha Gavrilov suggested that there are no data files
    with more than one channel

    :param log: higher level log file
    :param rawFileName: filename of the raw (DAT) file from which the vav filename shall be derived
    :param sampleRate: audio sampling rate
    :param binData: raw audio data
    """
    # Open the WAV file
    try:
        with wave.open(wavFileName, 'wb') as wavFile:
            # Set the parameters of the output file
            wavFile.setnchannels(1)  # mono
            wavFile.setsampwidth(rawdat.BITS_PER_SAMPLE//8)  # in bytes
            wavFile.setframerate(sampleRate)
            # write audio as binary data block
            wavFile.setnframes(binData.size)
            wavFile.writeframes(binData.tobytes())

            log.info(f"Written {wavFileName}")

    except (FileNotFoundError, IOError, OSError, wave.Error) as e:
        logMsg = f"Error writing audio signal into file {wavFileName}"
        log.error(logMsg + f"\nException {e}")
        raise IMOSAcousticWavException(logMsg)

#    if metadataStruct is not None:
#        # Micro$oft wave format does not support custom metadata.
#        # The workaround is: Format metadata into a json string and
#        # write that into wav as a ad sound frame at the end of the file
#        try:
#            metadataDict = asdict(metadataStruct)
#            for key, value in metadataDict.items():
#                # Convert the value to a string
#                metadataDict[key] = str(value)
#            # Serialize the metadata dictionary to a JSON string
#            metadataJsonString = json.dumps(metadataDict)
#
#            # write audio as binary data block
#            metadataJsonByteStream = metadataJsonString.encode('utf-8')
#            # wavFile.setnframes(len(metadataJsonByteStream))
#            wavFile.writeframes(metadataJsonByteStream)
#
#        except (IOError, OSError, wave.Error) as e:
#            logMsg = f"Error writing metadata at the end of audio file {wavFileName}"
#            log.error(logMsg + f"\nException {e}")
#            raise IMOSAcousticWavException(logMsg)

def addIMOSMetadata(wavFileName: str, metadataStruct: WavMetadataEssential):
    """
    Generate the wav filename from raw DAT file

    Micro$oft wave format does not support custom metadata.
    the workaround is: Format metadata into a json string
    and write that into wav as a text comment

    :param rawFileName: filename of the raw (DAT) file from which the vav filename shall be derived
    :return: filename of the wav file name 
    """
    try:
        audio = WAVE(wavFileName)
        # Convert the dataclass instance to a dictionary
        metadataDict = asdict(metadataStruct)

        for key, value in metadataDict.items():
            # Convert the value to a string
            metadataDict[key] = str(value)

        # #Serialize the metadata dictionary to a JSON
        # metadataJson = json.dumps(metadataDict)
        # #Add the JSON string as a single custom tag
        # metadataJsonString = json.dumps(metadataJson)

        # Serialize the metadata dictionary to a JSON string
        metadataJsonString = json.dumps(metadataDict)

        # wav.setcomment(metadata_json.encode('utf-8'))
        audio.add_tags()
        audio.tags['IMOS_metadata'] = metadataJsonString
        audio.save()
    except (FileNotFoundError, IOError, MutagenError) as e:
        logMsg = f"An error occurred while adding metadata to the WAV file {wavFileName}"
        log.error(logMsg + f"\nException {e}")
        raise IMOSAcousticWavException(logMsg)
