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
    # audio record duration as read from the DAT file header
    durationHeader: float = 0
    # actual duration of the audio record as stored in a file
    # typically little longer than what is in the DAT file header
    durationFile: float = 0
    startTime: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    endTime: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    scaleFactor: int = -1


@dataclass
class MetadataFull:
    # Where we get this SetID? database of records?
    # it is in some of the DAT file headers, but not in all of them
    setID: int = -1
    # schedule number seems to be included in many DAT file headers
    schedule: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    numChannels: int = 1
    sampleRate: int = 0
    # audio record duration as read from the DAT file header
    durationHeader: float = 0
    # actual duration of the audio record as stored in a file
    # typically little longer than what is in the DAT file header
    durationFile: float = 0
    startTime: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    endTime: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    # calibration noise level - as provided for calibration
    # -90 seems to be the most common value of calibration noise level
    # 0.0 means not calibrated
    calibNoiseLevel: float = 0.0
    # hydrophone sensitivity - as provided for calibration
    # -196 seems to be the most common value of hydrophone sensitivity
    hydrophoneSensitivity: float = -196
    scaleFactor: int = -1


def deriveOutputFileName(rawFileName: str, ext: str) -> str:
    """
    Derive the output audio filename from raw DAT file 
        - just replace the extension

    :param rawFileName: filename of the raw (DAT) file from which 
                        the output filename shall be derived
    :param ext: output audio filename extension
    :return: filename of the wav file name
    """
    # Generate the new filename with the .wav suffix
    if rawFileName.endswith(".DAT"):
        outputFileName = rawFileName.rsplit('.', 1)[0] + '.' + ext
    else:
        outputFileName = rawFileName + '.' + ext

    return outputFileName


def createOutputFileName(setID: int, startTime: datetime, ext: str) -> str:
    """
    Create output file name from metadata (data set ID, capture start time)

    :param setID: data set ID
    :param startTime: audio record capture start time
    :param ext: output audio filename extension
    :return: filename of the wav file name
    """
    # Format the datetime object to a string as in the original Matlab code
    formattedTimeString = startTime.strftime('%Y%m%d_%H%M%S')
    outputFileName = f"Set{setID}_{formattedTimeString}.{ext}"
    return outputFileName


def writeMono16bit(fileName: str, binData: numpy.ndarray,
                   metadataStruct: MetadataEssential=None,
                   fileFormat='WAV') -> None:
    """
    Write audio signal data into a MS wave file

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
        metadataStruct.durationFile = len(binData)/metadataStruct.sampleRate
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
        with soundfile.SoundFile(fileName, mode='w', samplerate=int(metadataStruct.sampleRate),
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
    """
    Detect whether file corresponding to fileName is WAVE or FLAC file.

    :param fileName: filename of the audio file
    :return: string "WAVE", "FLAC" or "Unknown format"
    """
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
    """
    Extract IMOS metadata as string from tag ICMT (.wav)
    or comment (.flac)

    :param fileName: filename of the audio file
    :return: meta data in text form, shall be a Json string
    """
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
    """
    Extract IMOS metadata as python object json from tag ICMT (.wav)
    or comment (.flac)

    :param fileName: filename of the audio file
    :return: Json metadata object as returned by json.loads()
    """
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
    """
    Extract IMOS metadata as python object json from tag ICMT (.wav)
    or comment (.flac)

    :param fileName: filename of the audio file
    :return: MetadataEssential - Json metadata dataclass (python struct)
    """
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
            durationFile=int(float(metadata_dict['durationFile'])),
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
    """
    Load IMOS audio record (wav or flac) and print
    information from the wav file header.

    :param fileName: filename of the audio file
    :return: soundfile.SoundFile - open sound file, ready
             for further read/manipulation
    """
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
