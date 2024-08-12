======================
IMOS PA Tools
======================

IMOS Passive Audio Tools Documentation
-----------------------------------------------------------------

This software contains of a Python library package IMOAPATools and a set of CLI tools that serve also as a demo code how to use the library.

It is recommended to install the package with pip in a virtual environment (eg miniconda), or in a container.

Repository structure
--------------------
  
   .. code-block::
  
      NDRI-IMOS
      ├── doc          ... documentation
      ├── IMOSPATools  ... the python library code
      ├── jupyter      ... Jupyter notebooks to compare results with reference
      ├── scripts      ... CLI tools
      ├── src
      │   ├── matlab   ... the reference matlab implementation of calibration
      │   └── utils
      │       └── imos_read  ... simple C code to read .DAT file
      └── tests        ... test procedures
         └── data      ... test data
               ├── KI_3501
               │   ├── Calib_file
               │   └── reference
               ├── Portland_3092
               │   ├── Calib_file
               │   └── reference
               └── Rottnest_3154
                   ├── Calib_file
                   └── reference
         
   .. ::

Static design
-------------

The static design diagram shows the breakdown of the library into code modules.

.. image:: IMOSPATools_static_design.svg
   :alt: Static library design

Dynamic design
--------------

The calibration dataflow diagram shows processing steps and intermediate 
data products through the procedure of calibration.

.. image:: calibration_dataflow.svg
   :alt: Calibration dataflow diagram

CLI tools included
------------------

Commandline tools 

* dat2wav.py ... commandline script that is able to read one raw (.DAT) file,
                 calibrate it and save the product as Microsoft wave or flac file

* inspect_audio_record.py ... commandline script that read the vane or flac file 
                              and prints various information on the data recordd,
                              including IMOS meta data (if included in the file).
   

