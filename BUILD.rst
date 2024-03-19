========
BEANSp
========

Build and installation from this github repository
--------------------------------------------------

#. Install/upgarde pip, build and local install

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
     
      python3 -m pip -v uninstall imos-pa-tools
      python3 -m pip -v cache purge

   After this, in that environment, beansp just works from every directory, providing the conda environment is activated.
   Imports like:

   .. code-block::

      from imos-pa-tools import ...

   (See `test_sft_beans.py <tests/test_sft_beans.py>`_.)

