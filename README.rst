3Di Results Analysis
====================

A QGIS plugin for analyzing 3Di results and visualize computational grids in the 3Di Modeller Interface.

.. _`3Di`: https://3diwatermanagement.com/

The tools that this plugin provides allow you to:

- Make (maximum) water depth or water level rasters from raw 3Di simulation results.
- Visualize results on the map canvas for a specific timestep
- Plot timeseries of discharge, water level or any other variable in a graph
- Make side view plots of water levels and water level gradients at any time during the simulation
- Calculate the water balance for any given area in the model domain
- Calculate aggregated results such as maximum water level per node or total discharge per flowline
- Calculate the total discharge crossing a user-defined line
- Find the upstream or downstream area for any node or group of nodes


Installation
------------

Prerequisites
^^^^^^^^^^^^^

**Windows**

Install Qgis 3.28.5+ (the "long term release") from qgis.org. 


**Ubuntu**

Install QGIS and the required python3-h5py dependency::

  $ sudo apt install qgis python-h5py


Getting the plugin
^^^^^^^^^^^^^^^^^^

- In QGIS, goto "Plugins > Manage And Install Plugins... > Settings"
- Add ``https://plugins.lizard.net/plugins.xml`` and reload
- Install the plugin by selecting ``3Di Results Analysis``


Installation notes
^^^^^^^^^^^^^^^^^^

If you have the ``PIP_REQUIRE_VIRTUALENV=1`` setting you may have to
(temporally) remove that in order to install the plugin, but be assured that
all the required dependencies are bundled with the plugin and automatically
installed into the ``deps`` directory of the plugin in your QGIS profile.


Local development
-----------------

On Linux, local development happens with docker to make sure we're working in a nicely
isolated environment. So first build the docker::

  $ docker-compose build

The docker-qgis's settings are persisted in a "named docker volume",
``qgis-docker``. To wipe it clean, run ``docker-compose down -v``.

To run the full tests including coverage report and flake8::

  $ docker-compose run -e QT_QPA_PLATFORM=offscreen qgis-desktop make test

You can also just run pytest. You won't get the coverage report. You *can*
however then use one of the pytest options, like ``-x``, which aborts the test
at the first failure::

  $ docker-compose run --rm qgis-desktop pytest -x

To get a "coverage" report for the docstrings or to run flake8::

  $ docker-compose run --rm qgis-desktop make docstrings

To run black (standard pep8-compatible code formatting), isort (import
sorting) and flake8 (reporting missing imports and so), run::

  $ docker-compose run --rm qgis-desktop make beautiful

To run the QGIS application itself in the docker::

  $ xhost +local:docker  # you may need this to run the gui
  $ docker-compose run --rm qgis-desktop qgis


Release
-------

Make sure you have ``zest.releaser`` with ``qgispluginreleaser`` installed. The
``qgispluginreleaser`` ensures the metadata.txt, which is used by the qgis plugin
manager is also updated to the new version. To make a new release enter the following
commands and follow their steps::

    $ cd /path/to/the/plugin
    $ fullrelease

This creates a new release and tag on github. Additionally, a zip file
``threedi_results_analysis.<version>.zip`` is created. Github actions is configured to also
create this zip and upload it to https://plugins.lizard.net/ when a new tag is
created, using the ``upload-artifact.sh`` script.

You can also manually create a zip file of the current checked out code with the
following command::

    $ docker-compose run --rm qgis-desktop make zip

