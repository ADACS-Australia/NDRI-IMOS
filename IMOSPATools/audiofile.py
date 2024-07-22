import soundfile
import logging
import numpy
import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

log = logging.getLogger('IMOSPATools')


class IMOSAcousticAudioWriteException(Exception):
    pass


@dataclass
class MetadataEssential:
    numChannels: int = 1
    sampleRate: int = -1 
    durationHeader: int = 0
    startTime: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    endTime: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)


def deriveOutputFileName(rawFileName: str, ext: str) -> str:
    """
    Generate the wav filename from raw DAT file

    :param rawFileName: filename of the raw (DAT) file from which the vav filename shall be derived
    :return: filename of the wav file name 
    """
    # Generate the new filename with the .wav suffix
    if rawFileName.endswith(".DAT"):
        outputFileName = rawFileName.rsplit('.', 1)[0] + '.' + ext
    else:
        outputFileName = rawFileName + '.' + ext

    return outputFileName


def writeWavMono16bit(fileName: str, sampleRate: float, binData: numpy.ndarray,
                      metadataStruct: MetadataEssential=None):
    # Write WAV file with optional metadata as comment
    # Ensure binData is int16
    if binData.dtype != numpy.int16:
        raise ValueError("binData must be of type numpy.int16")

    if metadataStruct is not None:
        # Micro$oft wave format does not support custom metadata.
        # The workaround is: Format metadata into a json string and
        # write that into wav as a ad sound frame at the end of the file
        metadataDict = asdict(metadataStruct)
        for key, value in metadataDict.items():
            # Convert the value to a string
            metadataDict[key] = str(value)

        # #Serialize the metadata dictionary to a JSON
        # metadataJson = json.dumps(metadataDict)
        # #Add the JSON string as a single custom tag
        # metadataJsonString = json.dumps(metadataJson)

        # Serialize the metadata dictionary to a JSON string
        metadataString = json.dumps(metadataDict)
    else:
        metadataString = "IMOS audio"

    try:
        with soundfile.SoundFile(fileName, mode='w+', samplerate=int(sampleRate),
                                 channels=1, subtype='PCM_16', format='WAV') as sf:
            # __setattr__(self, name, value) is not part of official documented API
            # see https://python-soundfile.readthedocs.io/en/0.11.0/_modules/soundfile.htm
            sf.__setattr__('comment', metadataString)
            sf.write(binData)
    except (IOError, OSError, soundfile.LibsndfileError) as e:
        logMsg = f"Error writing audio file {fileName}"
        log.error(logMsg + f"\nException {e}")
        raise IMOSAcousticAudioWriteException(logMsg)

    log.info(f"Written {fileName} with meta data.")


# # Verify the metadata
# data, samplerate = sf.read(output_filename)
# metadata = sf.info(output_filename).metadata
# print("Metadata comment:", metadata.get('comment'))
