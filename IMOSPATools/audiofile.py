import soundfile
import logging
import numpy
import re
import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

log = logging.getLogger('IMOSPATools')


class IMOSAcousticAudioFileException(Exception):
    pass


@dataclass
class MetadataEssential:
    numChannels: int = 1
    sampleRate: int = -1
    durationHeader: int = 0
    startTime: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    endTime: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    scaleFactor: int = 1


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


def writeMono16bit(fileName: str, sampleRate: float, binData: numpy.ndarray,
                      metadataStruct: MetadataEssential=None, fileFormat='WAV') -> None:
    """
    Write audio signal data into a MS wave file
    !@#$%^& TODO use the struct values rather than extra param sampleRate

    :param fileName: filename of the output audio file
    :param sampleRate: sampling rate
    :param binData: audio data as numpy.ndarray of numpy.int16
    :param metadataStruct: a dataclass structure with metadata. 
                           some go into the mandatory file header,
                           all then as metadata stored in comment tag
                           as json string.
    :return: None
    """
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
        with soundfile.SoundFile(fileName, mode='w', samplerate=int(sampleRate),
                                 channels=1, subtype='PCM_16', format=fileFormat) as sf:
            # __setattr__(self, name, value) is not part of official documented API
            # see https://python-soundfile.readthedocs.io/en/0.11.0/_modules/soundfile.htm
            sf.__setattr__('comment', metadataString)
            sf.write(binData)
    except (IOError, OSError, soundfile.LibsndfileError) as e:
        logMsg = f"Error writing audio file {fileName}"
        log.error(logMsg + f"\nException {e}")
        raise IMOSAcousticAudioFileException(logMsg)

    log.info(f"Written {fileName} with meta data.")


def detectAudioFormat(fileName: str) -> str:
    # Detect whether it is WAVE or FLAC file.

    # Read the first 12 bytes of the file
    with open(fileName, 'rb') as file:
        header = file.read(12)
    # Check for WAVE format
    if header.startswith(b'RIFF') and header[8:12] == b'WAVE':
        return "WAVE"

    # Check for FLAC format
    elif header.startswith(b'fLaC'):
        return "FLAC"

    # If neither WAVE nor FLAC
    else:
        return "Unknown format"


def extractMetadataStr(fileName: str) -> str:
    # Define the regular expression pattern to find the JSON-like structure
    regexp_ICMT = r'ICMT\s*:\s*({.*?})'
    regexp_comment = r'comment\s*:\s*({.*?})'

    audioFormat = detectAudioFormat(fileName)
    log.debug(f"Detected file format {audioFormat}")

    if audioFormat == "WAVE":
        regexpMeta = regexp_ICMT
    elif audioFormat == "FLAC":
        regexpMeta = regexp_comment
    else:
        regexpMeta = ""
        raise IMOSAcousticAudioFileException(f"Unsupported audio format for file: {fileName}, expected WAVE or FLAC.")

    try:
        with soundfile.SoundFile(fileName, mode='r') as sf:
            info = sf.extra_info
    except (IOError, OSError, soundfile.LibsndfileError) as e:
        logMsg = f"Error inspecting audio file {fileName}"
        log.error(logMsg + f"\nException {e}")
        raise IMOSAcousticAudioFileException(logMsg)

    # Search for the pattern in the file content
    match = re.search(regexpMeta, info, re.DOTALL)
    if match:
        metadataString = match.group(1)
        return metadataString
    else:
        logMsg = f"Error: Metadata (as ICMT tag) not found in audio file {fileName}"
        log.error(logMsg)
        raise IMOSAcousticAudioFileException(logMsg)


def extractMetadataJson(fileName: str):
    jsonStr = extractMetadataStr(fileName)
    try:
        # Parse the JSON string
        metadata = json.loads(jsonStr)
        return metadata
    except json.JSONDecodeError as e:
        logMsg = f"Error: Failed to decode JSON from audio file {fileName}"
        log.error(logMsg + f"\nException {e}")
        raise IMOSAcousticAudioFileException(logMsg)


def extractMetadataStruct(fileName: str) -> MetadataEssential:
    metadataJson = extractMetadataJson(fileName)
    try:
        metadataDict = json.loads(jsonStr)
        # Parse datetime strings
        startTime = datetime.strptime(metadata_dict['startTime'], "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
        endTime = datetime.strptime(metadata_dict['endTime'], "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)

        # Create MetadataEssential object
        metadata = MetadataEssential(
            numChannels=int(metadata_dict['numChannels']),
            sampleRate=int(float(metadata_dict['sampleRate'])),
            durationHeader=int(float(metadata_dict['durationHeader'])),
            startTime=start_time,
            endTime=end_time,
            scaleFactor=int(float(metadata_dict['scaleFactor']))
        )
        return metadata
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logMsg = f"Error: Failed to process metadata - {str(e)}"
        log.error(logMsg + f"\nException {e}")
        raise IMOSAcousticAudioFileException(logMsg)


def loadInspect(fileName: str) -> soundfile.SoundFile:
    try:
        with soundfile.SoundFile(fileName, mode='r') as sf:
            signal = sf.read()
            sampleRate = sf.samplerate
            extraInfo = sf.extra_info
            print(extraInfo)
            print("----------------------------------------------------")
            recordDuration = signal.size / sampleRate
            print(f"Audio record duration {recordDuration:.2f}s")
            print(f"Sampling rate {sampleRate}Hz")
            print(f"Maximum abs amplitude of the signal: {numpy.max(numpy.abs(signal))}")
            return sf
    except (IOError, OSError, soundfile.LibsndfileError) as e:
        logMsg = f"Error inspecting audio file {fileName}"
        log.error(logMsg + f"\nException {e}")
        raise IMOSAcousticAudioFileException(logMsg)
