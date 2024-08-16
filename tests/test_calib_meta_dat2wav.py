import os
import logging
import numpy
import wave

from IMOSPATools import rawdat
from IMOSPATools import wav
from IMOSPATools import calibration
from IMOSPATools import audiofile

log = logging.getLogger('IMOSPATools')
calibration.doWriteIntermediateResults = False


def read_calib_parameters(file_path):
    # helper function to read calibration parameters from a plaintext file
    parameters = {}

    with open(file_path, 'r') as file:
        # Read all lines and split by newline character
        lines = file.read().splitlines()

    for line in lines:
        # Split the line into key and value
        parts = line.split(':')
        if len(parts) == 2:
            key = parts[0].strip()
            # Extract the number, ignoring any units
            value = parts[1].split()[0].strip()
            try:
                # Convert to float
                parameters[key] = float(value)
            except ValueError:
                msg = f"Warning: Could not convert '{value}' to a number for '{key}'"
                print(msg)
                raise AssertionError(msg)

    return parameters


def load_float_array(file_path):
    # helper function to read audio signal intermediate product 
    # in text format, one float number per line
    try:
        # Load the file using numpy's loadtxt function
        # We set dtype to float to ensure all values are treated as floats
        arr = numpy.loadtxt(file_path, dtype=float)
        return arr
    except IOError:
        msg = f"Error: Unable to read file '{file_path}'"
        print(msg)
        raise AssertionError(msg)
    except ValueError:
        msg = f"Error: File '{file_path}' contains invalid data. Ensure all lines contain valid float numbers."
        print(msg)
        raise AssertionError(msg)


def calib_dat2wavflac(rawFileName: str,
                      calibFileName: str,
                      calibParamsFileName: str) -> bool:
    # test calibration of one file using regular (complex) FFT/IFFT

    if not os.path.exists(rawFileName):
        log.error(f'Raw dat file {rawFileName} not found!')
        raise AssertionError(f"FAILED: the following test data file does not exist: {rawFileName}")
    if not os.path.exists(calibFileName):
        log.error(f'Calibration file {calibFileName} not found!')
        raise AssertionError(f"FAILED: the following test data file does not exist: {calibFileName}")
    if not os.path.exists(calibParamsFileName):
        log.error(f'Calibration file {calibParamsFileName} not found!')
        raise AssertionError(f"FAILED: the following test data file does not exist: {calibParamsFileName}")

    try:
        binData, numChannels, sampleRate, durationHeader, \
            startTime, endTime = rawdat.readRawFile(rawFileName)
    except rawdat.IMOSAcousticRAWReadException:
        raise AssertionError(f"FAILED: read raw DAT file {rawFileName}")

    try:
        durationFile = binData.size / sampleRate
        setID = 2

        metadata = audiofile.MetadataFull(
            setID=setID,
            numChannels=numChannels,
            sampleRate=sampleRate,
            durationHeader=durationHeader,
            durationFile=durationFile,
            startTime=startTime,
            endTime=endTime,
        )
    except:
        raise AssertionError(f"FAILED: extract essential metadata from the header of raw DAT file {rawFileName}")

    # debugging...
    log.debug(f"raw .DAT signal size is: {binData.size}")
    log.debug(f"raw .DAT signal type is: {type(binData)}")
    log.debug(f"min bin value in raw .DAT signal size is: {numpy.min(binData)}")
    log.debug(f"max bin value in raw .DAT signal size is: {numpy.max(binData)}")

    numOverloadedSamples = calibration.countOverload(binData)
    if numOverloadedSamples > 0:
        log.warning(f"Logger was overloaded - signal is clipped for {numOverloadedSamples} samples.")

    # read calibration parameters
    try:
        calib_params = read_calib_parameters(calibParamsFileName)
    except:
        raise AssertionError(f"FAILED: read calibration parameters file {calibParamsFileName}")

    param = 'Cal level'
    try:
        cnl = calib_params.get(param)
    except:
        raise AssertionError(f"FAILED: extract calibration parameter \'{param}\' from file {calibParamsFileName}")

    param = 'Hydrophone sensitivity'
    try:
        hs = calib_params.get(param)
    except:
        raise AssertionError(f"FAILED: extract calibration parameter \'{param}\' from file {calibParamsFileName}")

    param = 'Set ID'
    try:
        setID = int(calib_params.get(param))
    except:
        raise AssertionError(f"FAILED: extract calibration parameter \'{param}\' from file {calibParamsFileName}")

    metadata.calibNoiselevel = cnl
    metadata.hydrophoneSensitivity = hs
    metadata.setID = setID

    # read and pre-process calibration audio record
    try:
        calSpec, calFreq, calSampleRate = calibration.loadPrepCalibFile(calibFileName, cnl, hs)
        if sampleRate != calSampleRate:
            msg = "Sample rate is different between the audio record and calibration file."
            logging.error(msg)
            raise AssertionError(msg)
    except:
        raise AssertionError(f"FAILED: read and pre-process calibration audio file {calibFileName}")

    # do the calibration
    try:
        volts = calibration.toVolts(binData)
        calibratedSignal = calibration.calibrate(volts, cnl, hs, calSpec, calFreq, sampleRate)
        scaledSignal, scaleFactor = calibration.scale(calibratedSignal)
        metadata.scaleFactor = scaleFactor
    except:
        raise AssertionError(f"FAILED: calibrate and scale audio file {rawFileName}")

    # debugging...
    log.debug(f"scaled calibrated signal size is: {scaledSignal.size}")
    log.debug(f"scaled calibrated signal type is: {type(scaledSignal)}")
    log.debug(f"scaled calibrated signal sample type is: {scaledSignal.dtype}")
    log.debug(f"scaled calibrated signal sample size is: {scaledSignal.itemsize} bytes")

    if scaledSignal is not None:
        try:
            # write calibrated wav file
            outputFileName = audiofile.createOutputFileName(metadata.setID,
                                                            metadata.startTime,
                                                            'wav')
            outputPath = os.path.dirname(rawFileName) + '/' + outputFileName
            audiofile.writeMono16bit(outputPath, scaledSignal,
                                     metadata)
            # write calibrated flac file
            outputFileName = audiofile.createOutputFileName(metadata.setID,
                                                            metadata.startTime,
                                                            'flac')
            outputPath = os.path.dirname(rawFileName) + '/' + outputFileName
            audiofile.writeMono16bit(outputPath, scaledSignal,
                                     metadata, 'FLAC')
        except:
            raise AssertionError(f"FAILED: write wave file {wavFileName}")
    else:
        logMsg = "Something went wrong, there is no audio signal data to write to a wav file."
        log.error(logMsg)
        raise AssertionError(logMsg)

    return True


def calib_real_dat2wavflac(rawFileName: str,
                           calibFileName: str,
                           calibParamsFileName: str) -> bool:
    # test calibration of one file using real FFT/IFFT

    if not os.path.exists(rawFileName):
        log.error(f'Raw dat file {rawFileName} not found!')
        raise AssertionError(f"FAILED: the following test data file does not exist: {rawFileName}")
    if not os.path.exists(calibFileName):
        log.error(f'Calibration file {calibFileName} not found!')
        raise AssertionError(f"FAILED: the following test data file does not exist: {calibFileName}")
    if not os.path.exists(calibParamsFileName):
        log.error(f'Calibration file {calibParamsFileName} not found!')
        raise AssertionError(f"FAILED: the following test data file does not exist: {calibParamsFileName}")

    try:
        binData, numChannels, sampleRate, durationHeader, \
            startTime, endTime = rawdat.readRawFile(rawFileName)
    except rawdat.IMOSAcousticRAWReadException:
        raise AssertionError(f"FAILED: read raw DAT file {rawFileName}")

    try:
        durationFile = binData.size / sampleRate
        setID = 1

        metadata = audiofile.MetadataFull(
            setID=setID,
            numChannels=numChannels,
            sampleRate=sampleRate,
            durationHeader=durationHeader,
            durationFile=durationFile,
            startTime=startTime,
            endTime=endTime,
        )
    except:
        raise AssertionError(f"FAILED: extract essential metadata from the header of raw DAT file {rawFileName}")

    # debugging...
    log.debug(f"raw .DAT signal size is: {binData.size}")
    log.debug(f"raw .DAT signal type is: {type(binData)}")
    log.debug(f"min bin value in raw .DAT signal size is: {numpy.min(binData)}")
    log.debug(f"max bin value in raw .DAT signal size is: {numpy.max(binData)}")

    numOverloadedSamples = calibration.countOverload(binData)
    if numOverloadedSamples > 0:
        log.warning(f"Logger was overloaded - signal is clipped for {numOverloadedSamples} samples.")

    # read calibration parameters
    try:
        calib_params = read_calib_parameters(calibParamsFileName)
    except:
        raise AssertionError(f"FAILED: read calibration parameters file {calibParamsFileName}")

    param = 'Cal level'
    try:
        cnl = calib_params.get(param)
    except:
        raise AssertionError(f"FAILED: extract calibration parameter \'{param}\' from file {calibParamsFileName}")

    param = 'Hydrophone sensitivity'
    try:
        hs = calib_params.get(param)
    except:
        raise AssertionError(f"FAILED: extract calibration parameter \'{param}\' from file {calibParamsFileName}")

    param = 'Set ID'
    try:
        setID = int(calib_params.get(param))
    except:
        raise AssertionError(f"FAILED: extract calibration parameter \'{param}\' from file {calibParamsFileName}")

    metadata.calibNoiselevel = cnl
    metadata.hydrophoneSensitivity = hs
    metadata.setID = setID

    # read and pre-process calibration audio record
    try:
        calSpec, calFreq, calSampleRate = calibration.loadPrepCalibFile(calibFileName, cnl, hs)
        if sampleRate != calSampleRate:
            msg = "Sample rate is different between the audio record and calibration file."
            logging.error(msg)
            raise AssertionError(msg)
    except:
        raise AssertionError(f"FAILED: read and pre-process calibration audio file {calibFileName}")

    # do the calibration
    try:
        volts = calibration.toVolts(binData)
        calibratedSignal = calibration.calibrateReal(volts, cnl, hs, calSpec, calFreq, sampleRate)
        scaledSignal, scaleFactor = calibration.scale(calibratedSignal)
        metadata.scaleFactor = scaleFactor
    except:
        raise AssertionError(f"FAILED: calibrate and scale audio file {rawFileName}")

    # debugging...
    log.debug(f"scaled calibrated signal size is: {scaledSignal.size}")
    log.debug(f"scaled calibrated signal type is: {type(scaledSignal)}")
    log.debug(f"scaled calibrated signal sample type is: {scaledSignal.dtype}")
    log.debug(f"scaled calibrated signal sample size is: {scaledSignal.itemsize} bytes")

    if scaledSignal is not None:
        try:
            # write calibrated wav file
            outputFileName = audiofile.createOutputFileName(metadata.setID,
                                                            metadata.startTime,
                                                            'wav')
            outputPath = os.path.dirname(rawFileName) + '/' + outputFileName
            audiofile.writeMono16bit(outputPath, scaledSignal,
                                     metadata)
            # write calibrated flac file
            outputFileName = audiofile.createOutputFileName(metadata.setID,
                                                            metadata.startTime,
                                                            'flac')
            outputPath = os.path.dirname(rawFileName) + '/' + outputFileName
            audiofile.writeMono16bit(outputPath, scaledSignal,
                                     metadata, 'FLAC')
        except:
            raise AssertionError(f"FAILED: write wave file {wavFileName}")
    else:
        logMsg = "Something went wrong, there is no audio signal data to write to a wav file."
        log.error(logMsg)
        raise AssertionError(logMsg)

    return True


def compare_wav_files(wav: str, ref: str):
    # Turned out this is not actually realistic to do, for two reasons:
    # 1) the phase delay correction for the high pass Butterworth
    # filter produces slightly different result using Python SciPy
    # compared to Matlab implementation.
    # 2) the Matlab wav write function scales the normalised audio
    # signal (in floats) to signed int16 differently compared to Ptyhon 
    # soundfile package, and in both libs it is done automaticaly,
    # there is no parameter to modify that scaling factor.
    print(f"Compare file {wav} with reference {ref}")
    # Open the first WAV file
    with wave.open(wav, 'rb') as wav_file1:
        params1 = wav_file1.getparams()
        frames1 = wav_file1.readframes(params1.nframes)
        sampleFreq1 = wav_file1.getframerate()
        samples1 = numpy.frombuffer(frames1, dtype=numpy.int16)

    # Open the second WAV file (reference)
    with wave.open(ref, 'rb') as wav_file2:
        params2 = wav_file2.getparams()
        frames2 = wav_file2.readframes(params2.nframes)
        sampleFreq2 = wav_file1.getframerate()
        samples2 = numpy.frombuffer(frames2, dtype=numpy.int16)

    if sampleFreq1 != sampleFreq2:
        logMsg = f"Sampling frequency of compared files is different - tested: {sampleFreq1}Hz reference: {sampleFreq2}Hz."
        log.error(logMsg)
        raise AssertionError(logMsg)

    # Ensure the comparison is only up to the length of the shorter file
    min_length = min(len(samples1), len(samples2))
    samples1 = samples1[:min_length]
    samples2 = samples2[:min_length]

    # Skip the 1st 0.2s as the high pass filter is not settled yet
    samples1 = samples1[int(0.2*sampleFreq1):-int(0.2*sampleFreq1)]
    samples2 = samples2[int(0.2*sampleFreq1):-int(0.2*sampleFreq1)]

    # Compare the samples using numpy.isclose
    # comparison = numpy.isclose(samples1, samples2)
    # Return True if all samples are close, False otherwise
    # return numpy.all(comparison)
    are_close = numpy.allclose(samples1, samples2, rtol=0.2, atol=0.2)

    if not are_close:
        # Find indices where samples are not close
        not_close = ~numpy.isclose(samples1, samples2, rtol=0.2, atol=0.2)
        diff_indices = numpy.where(not_close)[0]

        # Print the first 10 samples that are not close
        print("First 10 samples that are not close (index, wav value, ref value):")
        for i, idx in enumerate(diff_indices[:10]):
            print(f"{idx}: {samples1[idx]} vs {samples2[idx]} ratio {samples2[idx]/samples1[idx]}")

        print("Middle 10 samples that are not close (index, wav value, ref value):")
        for i, idx in enumerate(diff_indices[((diff_indices.size//2)-5):((diff_indices.size//2)+5)]):
            print(f"{idx}: {samples1[idx]} vs {samples2[idx]} ratio {samples2[idx]/samples1[idx]}")

        print("Last 10 samples that are not close (index, wav value, ref value):")
        for i, idx in enumerate(diff_indices[-10:]):
            print(f"{idx}: {samples1[idx]} vs {samples2[idx]} ratio {samples2[idx]/samples1[idx]}")

        logMsg = "Product of calibration (file {str}) is different from reference file."
        log.error(logMsg)
        raise AssertionError(logMsg)

    return are_close


def test_calib_dat2wavflac():
    # test calibration that uses regular (copmplex) FFT/IFFT
    dat1 = 'tests/data/Rottnest_3154/502DB01D.DAT'
    cal1 = 'tests/data/Rottnest_3154/Calib_file/501E9BF5.DAT'
    par1 = 'tests/data/Rottnest_3154/Calib_file/Calib_data.TXT'

    dat2 = 'tests/data/KI_3501/583E9500.DAT'
    cal2 = 'tests/data/KI_3501/Calib_file/5809C515.DAT'
    par2 = 'tests/data/KI_3501/Calib_file/Calib_data.TXT'

    dat3 = 'tests/data/Portland_3092/4F480851.DAT'
    cal3 = 'tests/data/Portland_3092/Calib_file/4FEACA92.DAT'
    par3 = 'tests/data/Portland_3092/Calib_file/Calib_data.TXT'

    calib_dat2wavflac(dat1, cal1, par1)
    calib_dat2wavflac(dat2, cal2, par2)
    calib_dat2wavflac(dat3, cal3, par3)


def test_calib_real_dat2wavflac():
    # test calibration that uses real FFT/IFFT
    dat1 = 'tests/data/Rottnest_3154/502DB01D.DAT'
    cal1 = 'tests/data/Rottnest_3154/Calib_file/501E9BF5.DAT'
    par1 = 'tests/data/Rottnest_3154/Calib_file/Calib_data.TXT'

    dat2 = 'tests/data/KI_3501/583E9500.DAT'
    cal2 = 'tests/data/KI_3501/Calib_file/5809C515.DAT'
    par2 = 'tests/data/KI_3501/Calib_file/Calib_data.TXT'

    dat3 = 'tests/data/Portland_3092/4F480851.DAT'
    cal3 = 'tests/data/Portland_3092/Calib_file/4FEACA92.DAT'
    par3 = 'tests/data/Portland_3092/Calib_file/Calib_data.TXT'

    calib_real_dat2wavflac(dat1, cal1, par1)
    calib_real_dat2wavflac(dat2, cal2, par2)
    calib_real_dat2wavflac(dat3, cal3, par3)


# The following 3 functions are renamed test* -> nest*
# to avoid pytest running them automatically

def nest_calib_dat2wav_reference1():
    wav1 = 'tests/data/Rottnest_3154/502DB01D.wav'
    ref1 = 'tests/data/Rottnest_3154/reference/502DB01D.wav'
    compare_wav_files(wav1, ref1)


def nest_calib_dat2wav_reference2():
    wav2 = 'tests/data/KI_3501/KI_3501'
    ref2 = 'tests/data/KI_3501/reference/KI_3501'
    compare_wav_files(wav2, ref2)


def nest_calib_dat2wav_reference3():
    wav3 = 'tests/data/Portland_3092/4F480851.wav'
    ref3 = 'tests/data/Portland_3092/reference/4F480851.wav'
    compare_wav_files(wav3, ref3)


if __name__ == "__main__":
    # set debugging logging level so we see as much as pos in testing
    logLevel = logging.DEBUG

    logFormat = "[%(asctime)s %(filename)s->%(funcName)s():%(lineno)s] %(levelname)s: %(message)s"
    logging.basicConfig(level=logLevel, format=logFormat,
                        #  seconds resolution is good enough for logging timestamp
                        datefmt='%Y-%m-%d %H:%M:%S')

    test_calib_dat2wavflac()
    test_calib_real_dat2wavflac()
