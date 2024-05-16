import wave
import numpy
import logging

def writeMono16bit(log: logging.Logger, rawFileName: str, sampleRate: float, binData: numpy.ndarray):
    """
    Write simple mono wav file, 16bit per sample

    !@#$%^&* Warning: assuming single channel only,
    as Sasha Gavrilov suggested that there are no data files
    with more than one channel

    :param log: higher level log file
    :param rawFileName: filename of the raw (DAT) file from which the vav filename shall be derived
    :param sampleRate: audio sampling rate
    :param binData: raw audio data
    """
    
    # Generate the new filename with the .wav suffix
    if rawFileName.endswith(".DAT"):
        wavFileName = rawFileName.rsplit('.', 1)[0] + '.wav'
    else:
        wavFileName = rawFileName + '.wav'

    # Open the WAV file
    try:
        with wave.open(wavFileName, 'w') as wavFile:
            # Set the parameters of the output file
            wavFile.setnchannels(1)  # mono
            wavFile.setsampwidth(2)  # in bytes, 16bit samples
            wavFile.setframerate(sampleRate)
            # write audio as binary data block
            wavFile.setnframes(binData.size)
            wavFile.writeframes(binData.tobytes())
        
            log.info(f"Written {wavFileName}")

    except wave.Error as e:
        log.error(f"Error writing WAV file {wavFileName}: {e}")
    except IOError as e:
        log.error(f"Error opening WAV file {wavFileName}: {e}")
    except Exception as e:
        log.error(f"Unexpected error {wavFileName}: {e}")
