import wave
from datetime import datetime
from typing import Tuple

# Write simple mono wav file
#   !@#$%^&* Warning: assuming single channel only,
#   eg: C0=1 C1=0 C2=0 C3=0 in the header.
#   as Sasha Gavrilov suggested there are no data files
#   with more than one channel
def write(log, rawFileName, sampleRate, binDataSuccess, binData):
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
