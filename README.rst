======================
IMOS PA Tools
======================

IMOS Passive Audio Tools
-----------------------------------------------------------------

* Free software: GPL-3.0 License
* Documentation: `https://github.com/ADACS-Australia/NDRI-IMOS/blob/master/doc/Documentation.rst <https://github.com/ADACS-Australia/NDRI-IMOS/blob/master/doc/Documentation.rst>`_
* Repo: `https://github.com/ADACS-Australia/NDRI-IMOS <https://github.com/ADACS-Australia/NDRI-IMOS>`_


Features
--------

Python module for IMOS passive audio recordings. Supports following functionality:

* read raw (.DAT) format files
* calibration 
* write in uncompressed Micro$oft wave (.WAV) and compressed flac (.FLAC) audio formats
* the metadata is stored as a Json string in the "comment" ID3 tag
* the library provides functions to extract the metadata

Notes: 

* minimal dependencies (only numpy, scipy, soundfile, wave)
* this python package as library is ready to be published on `PyPI <https://pypi.org/>`_

Credits
-------

Based on matlab code modules of CHORUS software written by Alexander N. Gavrilov.

`Gavrilov A.N. and Parsons M.J.G. (2014), “A MATLAB tool for the Characterisation Of Recorded Underwater Sound (CHORUS)”, Acoustics Australia v.42, No.3, pp. 190-196. <http://www.acoustics.asn.au/journal/Vol42No3-LOWRES.pdf>`_

`URI <http://hdl.handle.net/20.500.11937/38736>`_

Documentation
-------------

`Software documentation <doc/Documentation.rst>`_

Build and installation from this github repository
--------------------------------------------------

The IMOS passive audio tools library is wrapped in a python package named IMOSPATools.

`Build instructions <BUILD.rst>`_

CLI tools included
------------------

Commandline tools 

* dat2wav.py 
    commandline script that is able to read one raw (.DAT) file,
    calibrate it and save the product to a file as Microsoft WAVE
    or loselessly compressed FLAC

* inspect_audio_record.py
    commandline script that read the wav or flac file 
    and prints various information on the data recorrd,
    including IMOS meta data (if included in the file).
