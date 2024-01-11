ThreeDiToolbox
==============

A **deprecated** QGIS plugin with tools for working with models and netCDF results from
3Di hydraulic/hydrologic modelling software.

3Di Toolbox has been replaced by the 3Di Schematisation Editor (for viewing and editing schematisations) and 3Di Result Analysis (for analysing simulation results). Please install these two plugins through the Plugin Manager.

The current version of 3Di Toolbox is a **sunset** version: running this version removes toolbox dependencies and is only (temporarily) able to show schematisations from 3Di spatialites. You may still need to load layers from the 3Di spatialite to fix errors reported by the schematisation checker. This is a temporary situation, while the 3Di team is preparing the phasing out of the spatialite and transitioning to geopackage entirely.

Installation
----------------

You need to install Qgis 3.28 (the "long term release"). 

Add the Lizard QGIS repository: via the QGIS menu bar go to "Plugins > Manage
And Install Plugins... > Settings". Add
``https://plugins.lizard.net/plugins.xml`` and reload. Install the plugin by
selecting ThreeDiToolbox.

Local development
-----------------

Local development happens with docker to make sure we're working in a nicely
isolated environment. So first build the docker::

  $ docker-compose build

If your user ID isn't ``1000``, you can run it like this::

  $ docker-compose build --build-arg uid=`id -u` --build-arg gid=`id -g`

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
