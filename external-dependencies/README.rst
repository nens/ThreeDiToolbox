Dependency handling README
==========================

Qgis comes bundled with several python libraries, but we need a few more. The
extra dependencies (as wheels and eggs) are retrieved or stored into the
``external-dependencies/`` directory and bundled with the plugin.

The main ``threedi_results_analysis/__init__.py`` calls
``dependencies.py`` and installs the dependencies in the subfolder ``deps`` of
the plugin folder. The dependency folder is also added (prepended) to the path.

Python packages included on linux
---------------------------------

Assuming the ``ubuntu-ltr`` "qgis long term release" repository, the following
python packages are included when you apt-install qgis::

  python3-dateutil
  python3-future
  python3-gdal
  python3-httplib2
  python3-jinja2
  python3-markupsafe
  python3-matplotlib
  python3-numpy (via python3-gdal)
  python3-numpy-abi9 (via python3-gdal)
  python3-owslib
  python3-plotly
  python3-psycopg2
  python3-pygments
  python3-pyproj
  python3-requests
  python3-sip
  python3-six
  python3-tz
  python3-yaml

The ones we explicitly need are gdal and numpy.


Python packages included on windows
-----------------------------------

On windows, you can install qgis with osgeo4w, but you can also download a
standalone installer. This installer also uses osgeo4w. 

Extra dependencies we need
--------------------------

There is no ``setup.py`` in qgis plugins, so there's no default place to list
dependencies (and their versions). ``dependencies.py`` has the master list of
extra dependencies.

Most are pip-installable just fine as they're pure python packages. There is
one exception:

- h5py. This is a package that really needs to match various other libraries
  in the system. For windows, it means a custom built package (which we
  include in the plugin).

Our dependency handling
-----------------------

``dependencies.py`` (see :py:mod:`threedi_results_analysis.dependencies`) can be called
directly, which generates a ``constraints.txt`` file for use with pip. The
``Makefile`` handles this for us: it updates the constraints file when the
python file changes.

The ``external-dependencies/`` directory (containing this README) has a
``populate.sh`` script. The ``Makefile`` runs it when needed. It populates the
directory with our dependencies so that we can bundle it with the plugin:

- ``populate.sh`` uses ``pip3 wheel`` to create universal wheel files for the
  four pure python libaries.

- It also downloads and tars the custom build of h5py.

The :py:func:`threedi_results_analysis.dependencies.ensure_everything_installed`
function is called by our main ``threedi_results_analysis/__init__.py``:

- It first checks if the correct versions of our dependencies are
  installed. It doesn't matter where they're installed: system packages,
  qgis-bundled or in the profile directory.

- If something is missing, it calls python3's build-in "pip" to install it
  from the ``external-dependencies/`` directory into the plugin's
  ``deps/`` directory.

As a last step, ``threedi_results_analysis/__init__.py`` calls
:py:func:`threedi_results_analysis.dependencies.check_importability` to make doubly sure
all dependencies are present. Not only the ones from
``external-dependencies/``, but also ``gdal`` and ``numpy`` to make sure
they're properly included with qgis.
