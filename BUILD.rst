=============
IMOSPATools
=============

Build and installation from this github repository
--------------------------------------------------

The IMOS passive audio tools library is wrapped in a python package named IMOSPATools.

#. Install/upgrade pip, build and local install

   .. code-block::
  
      python3 -m pip install --upgrade pip
      python3 -m pip install --upgrade build

   .. code-block::
  
      # test build & local install
      # The "-e" install does not seem to be reliable for re-install on Linux
      #       - keeps pulling some old build from somewhere middlewhere.
      #         python -m pip install -e .*
      # This is more reliable:
      python3 -m build
      python3 -m pip install .

   .. ::
   
   *Note: when working on the code, in case of doubts that recent changes got propagated, uninstall & purge the installed module _before_* ``pip install`` *to ensure the installed version has all the recent modifications.*

   .. code-block::
     
      python3 -m pip -v uninstall IMOSPATools
      python3 -m pip -v cache purge

   There is also a simple `Makefile <Makefile>`_ that is capable of the generic make functionality:

   .. code-block::

      make 
      make install
      make clean

   .. ::

   To use the functions from the package, just import the module and call the functions:
   
   .. code-block::

      from IMOSPATools import ...

   (See `dat2wav.py <scripts/dat2wav.py>`_.)

