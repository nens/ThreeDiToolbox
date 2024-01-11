ThreeDiToolBox changelog
========================


2.5.6 (unreleased)
------------------

- Sunset version: removes toolbox dependencies and only able to show schematisations. (#887)


2.5.5 (2023-09-21)
------------------

- Bump threedigrid to 2.0.*
- Bump threedi-modelchecker to 2.4.*
- Bump threedigrid-builder to 1.12.*


2.5.4 (2023-07-20)
------------------

- Bump threedidepth to 0.6.1
- Add algorithm for maximum waterdepth to processing toolbox.
- Make the plugin work with all QGis versions by making installed
  h5py version depend on QGis version.

2.5.3 (2023-06-16)
------------------

- Bump threedi-modelchecker to 2.2.*
- Bump threedi-schema to 0.217.*
- Bump hydxlib to 1.5.1
- Bump threedigrid-builder to at least 1.11.4


2.5.2 (2023-04-26)
------------------

- Bump threedi-schema to at least 0.216.2
- Bump SQLAlchemy to 2.0.6
- Bump threedidepth to 0.5
- Bump hydxlib to 1.5.*


2.5.1 (2023-04-11)
------------------

- Temporary pinned threedi-schema on bugfix version to deal with dropped sqlalchemy 1.3 support.
- Fixed import issue with setuptools/importlib


2.5 (2023-02-06)
----------------

- Added usage of threedi_schema package
- Replaced pygeos dependency with a Shapely
- Fixed raster checks
- Fixed database interface in sufhyd importer
- Removed Command Tool and converted commands to processing algorithms (#715)
- Bumped several dependencies (Alembic)
- Add processing algorithm Import Hydx (#730)
- Do not set default inputs for "Computational grid from schematisation" processing algorithm (#723)
- Computational grid from h5 file: use file as input instead of containing folder (#722)

2.4.1 (2022-12-08)
------------------

- Do not expect pipe_quality field in sufhyd import. (#728)

- Check schema version before sufhyd import. (#726)

- threedi-modelchecker dependency fix. (#729)


2.4 (2022-11-28)
----------------
- Removed separate raster checker tool

- Updating to the minimal schema version 208

- Fetch wheels for threedigrid-builder and pygeos on linux.

- Updating to the minimal schema version 209


2.3 (2022-08-15)
----------------

- Added results analysis algorithms


2.2 (2022-06-29)
----------------

- Improved dependency management
- Added some missing dependendies on Windows
- Added plugin icon
- Dependencies are now stored in plugins' deps folder.
- Watershed tool.


2.1 (2022-06-14)
----------------

- Removed the create_views routine, this is now done by the modelchecker (migration tool).

- Upgrade sqlites from 3 to 4.3 when possible (migration tool). Warn users that this is necessary if
  their file has version 3.

- Removed the 'pipe_quality' column from v2_pipe.


2.0 (2022-03-30)
----------------

- First go at updating dependencies for python 3.9 and the new 3.22 LTR on
  windows.

- Updated the dockerfile to work with the new 3.22 dependencies on linux.
  Also switched to the official qgis development base dockerfile.


1.34 (2022-03-22)
-----------------

- Pinned geoalchemy2 to ``0.10.2`` instead of ``>0.10`` due to a
  migration bug:
  https://github.com/geoalchemy/geoalchemy2/issues/372. The one
  bundled with the previous version was ``0.11.1``.


1.33 (2022-03-17)
-----------------

- Add processing algorithm to check rasters


1.32 (2022-02-15)
-----------------

- Changes to the modelinterface builder: *only* threedi_models_and_simulations
  plugin is bundled, *not anymore* the threedi_qgis_api_client.


1.31 (2022-02-15)
-----------------

- Changes to the modelinterface builder: the threedi_models_and_simulations
  plugin is now also bundled.


1.30 (2022-02-15)
-----------------

- Fixed constructing the cells layer from new gridadmins (which contains NaN
  instead of -9999. for 1D nodes).

- DWF Calculator now takes the 'percentage' attribute of the impervious_surface_map into account + cleaner code

- DWF Calculator also works for v2_surface and use_0d_inflow from global settings determines its behaviour

- Updated threedi_modelchecker to 0.25.2.

- Schematisation checker compatible with threedi-modelchecker 0.25.2

- Include info and warning level messages in schematisation checker results csv

- Fix encoding error when reading gridadmin.h5

- Add processing algorithm to migrate sqlite to newest schema

- Add processing algorithm to check schematisation

- Update styling of result nodes and flowlines, mainly to also show flowlines with content_type = 'v2_added_c'


1.20 (2021-09-02)
-----------------

- Update threedidepth algorithm with new functionalities: multiple timesteps
  and export as netcdf file.

- Added netCDF4 binary for windows. Also added cftime (netcdf4 dependency).

- Added new animation slider.

- Updated dependencies are un-imported (technically: removed from ``sys.modules``)
  to prevent old versions from sticking around. In 1.18, you could get an error
  from the ``alembic`` dependency that complained about a too old sqlalchemy.

- Moved automatic tests from travis-ci to github actions.

- Fixed issue with broken sideview tool for qgis 3.16.6 and higher

- For *internal test purposes only*, fresh zips (for manual
  installation) are made of all pull requests and of master. See
  https://docs.3di.live/threeditoolbox-dev/ .

- Enhancements for the water depth/level calculation processing tool.

1.19 (2021-05-21)
-----------------

- Update to modeler interface: qgis 3.16.7 and threedi-api-qgis-client 2.4.1. (No changes
  to ThreeDiToolBox itself!)


1.18 (2021-04-22)
-----------------

- Adjusted dependencies for new threedi-modelchecker release.

- Installing bundled dependencies should no longer fetch newer releases
  from pypi, but stick to what we bundle in our external-dependencies
  directory.


1.17 (2021-04-01)
-----------------

- Restricting pyqtgraph to <0.12 to prevent ``from PyQt5 import sip`` import
  errors.

- Fixed error in notifying of necessary qgis restart.


1.16.1 (2021-03-04)
-------------------

- Bump metadata.txt version


1.16 (2021-03-04)
-----------------

- Enable the 3Di processing provider with threedidepth processing script.

- Bump version of pyqtgraph, QGIS_VERSION and THREEDI_API_QGIS_CLIENT_VERSION

- Fix import sufhydx coordinates swapped on newer gdal versions.


1.15 (2021-02-16)
-----------------

- Bump threedi-api-qgis-client to 2.2.0

- Bump QGIS version of the modeller interface to QGIS 3.10.14

- Add multiple stylings for the schematisation.

- Bump lizard-connector to version 0.7.3

- Add support for h5py with hdf5 1.10.5

- Added a extra processing provider for 3Di

- Added integration with threedidepth as a processing plugin

- Updated the threedi-modelchecker version to 0.11: https://github.com/nens/threedi-modelchecker/blob/master/CHANGES.rst#011-2021-01-26  # noqa

- Make RotateLabelAxisItem compatible with pyqtgraph 0.11


1.14.1 (2020-07-06)
-------------------

- Bug fix: graphview trying to get pump variables on models where there are not
  pumps.

- Bug fix in the sufhyd-importer-tool: using the wrong material.


1.14 (2020-05-25)
-----------------

- Added threedi-api-qgis-client to the modeller-interface. You can specify the version
  via the `THREEDI_API_QGIS_CLIENT_VERION` variable in the Makefile.

- Bumped threedi_modelchecker to 0.10.1.

- Bug fix pummplines: where the pumplines would use twice the same coordinates and thus
  be an invisible line.

- Bump threedigrid to 1.0.20.6.

- Bug fix vertical infiltation lines and pumplines not showing correctly.

- Set qgis installer version to final-3_10_4.

- Bug fix pumplines coords not using the projected coordinates.

- Graph-tool: only allow users to add graphs via the results-group, i.e. from the
  layers 'nodes', 'flowlines' and 'pumplines'.

- Graph-tool fix bug where pumpline-id was used to look up flowline variables and
  flowline-id for pumpline variables.

- Small fix in predict_calc_points command.

- Update v2_pumpstation action_type from 'set_capacity' to 'set_pump_capacity'.


1.13 (2019-12-02)
-----------------

- Added installer build script for ``3Di Modeller interface`` to makefile.

- Added Click as external dependency, which is currently required for the
  threedi-modelchecker.

- Improve raster_checker's 'extreme raster values' check: not rely on meta data,
  but check actual data. Also include number of warnings in pop-up when finished.

- Added custom h5py binaries for windows in external dependencies. Build for
  windows with python3.7. This h5py is able to read in results from the new
  threedi-api and the old (v2) results.

- Added a pip uninstall command before trying to install an external
  dependency to make sure our external packages get cleaned up.

- Bumped threedigrid to 1.0.16

- Automatically add a spatialite connection to the qgis-browser when a user
  loads a 3Di model via the result-selection-tool.

- Updated layer_styles of the schematisation. Attributes forms for all
  schematisation layers are configured. These layers are now grouped and
  ordered, and many widget types are configured.

- Added missing columns to the manhole_view layer.

- Added 'v2_cross_section_location_view' and 'v2_simple_infiltration' layers
  to the schematisation group.

- Administrative change: releases to https://plugins.lizard.net are now made
  by the automatic test server.


1.12.2 (2019-09-12)
-------------------

- Pinned h5py version to 2.9.


1.12.1 (2019-07-12)
-------------------

- Bumped threedi-modelchecker to 0.5 (no longer raise MigrationTooHighError).


1.12 (2019-07-08)
-----------------

- Fixed dependency installation on windows 7.

- Added developer documentation.

- Modelchecker user interface improvements.

- Running pip with ``--upgrade`` so that old packages actually get updated.

- Fixed bug where widget of control_structures wouldn't show up due to
  garbage collection.

- Bumped threedi-modelchecker to 0.3.

- Fix tool_commands/control_structures missing 's' for 'set_discharge_coefficient'.


1.11.1 (2019-06-17)
-------------------

- Made automated tests on travis-ci.org run much faster (from 8 down to 3
  minutes).

- Added better logging. In qgis, our messages are now visible in the console
  log. Also, a logfile is written (``threedi-qgis-log.txt``), which can be
  used to investigate problems. There's also a new button to open the logfile
  so that you can email it.

- Integrated threedi-modelchecker in the plugin as a tool_command.

- Improved dependency management of the plugin.

- Refactored structure of the plugin of the plugin: the tools are more clearly
  separated.

- Refactoring of many variables/classes/functions/methods to be more clear and
  consistent in the whole plugin.


1.10 (2019-03-28)
-----------------

- Cleaned up old docker-files (now only QGIS3.4.5) and pinned GeoAlchemy2 and
  updated docker readme.rst

- Fixed waterbalance tool rubberbands for 1d2d flow

- Grouped the 4 animation layers

- Fixed views model schematisation and statistics tool

- Fix guess_indicator postgres fields username and password


1.9 (2019-03-04)
----------------

- Fixed sideview bug point no geometry


1.8 (2019-02-28)
----------------

- Updated external h5py library (build h5py lib against hdf5 1.10.4-1 (instead
  of hdf5 1.8.11-2)


1.7 (2019-02-28)
----------------

- Updated ThreediToolbox to Qgis3 (python3 and qt5).

- Display pumplines without connection_node_end just for 5 meters

- QGIS3 can only handle netcdf-groundwater results (created after March 2018)

- Added a new tool: raster checker (added to commands.tools.step1)

- Waterbalance tool now correctly checks whether rain has been aplied to
  simulation

- Get rid of NetCDF4 lib

- Add v2_culvert to layer_tree_manager

- Added surface sources and sinks (q_sss) to the datasource for the graph-tool
  and animation-tool.

- Added surface sources and sinks to the waterbalance.

- Bumped threedigrid to 1.0.10.

- ResultSelectionWidget now correctly downloads the selected result.

- Removed matplotlib dependency used by the waterbalance barchart. The
  waterbalance barchart now uses pyqtgraph.

- Fixed bug reading in numpy.bytes as utf-8 strings.

- Fixed bug in netcdf_groundwater not reading in correctly the aggregate
  variable.

- Changed UI of several popup-windows to make them better displayable.


1.6 (2018-11-28)
----------------

- Enable ThreeDiToolbox besides NETCDF4 also for NETCDF3_CLASSIC (old results)


1.5 (2018-11-26)
----------------

- Add v2_culvert_view to layer_tree_manager


1.4 (2018-11-26)
----------------

- Enable intercepted_volume through aggregation NetCDF

- Upgrade threedigrid from 0.2.6 to 1.0.7 (current latest version)

- Add '(de)activate all layers' buttons in Waterbalancetool

- Remove old fashioned statistics (pop-up "do you want to calculate stats?")

- Improve NetCDF result selection (disabled selection aggregation NetCDF)

- Disable stacking of volume difference lines in the WaterBalance tool

- Gracefully handle HTTPError thrown by ResultsWorker thread.

- Added QSortFilterProxyModel to the result_selection to enable sorting and
  filtering of downloaded results.

- WaterbalanceTool account for flow directions (1d2d, 1d, 2d and groundwater)

- Enable leakage and simple infiltration through aggregation NetCDF

- WaterBalanceTool translate terms Dutch to English

- WaterBalanceTool get rid of "error" term

- WaterBalanceTool get rid of non-natural options

- WaterBalanceTool now only works with aggregation NetCDF and only with
  certain set of aggregation flow variables and aggregation methods

- not able to start StatisticsTool and WaterBalanceTool before select
  sqlite and NetCDf

- Include water balance tool (DeltaresTdiToolbox) in plugin.

- Add fix for ``None`` values in WeirStats calculation (caused by np.nan
  casting to None)

- Disable auto SI prefix on the vertical axis.

- Update schematisation layer style (add a lot of non_geom tables)

- Updated styling of waterbalance chart.


1.3 (2018-06-19)
----------------

- Use progress bar during loading ThreeDiStatistics (+ dutch to english names)

- Display 2d_vertical_infiltration in graph (not in animation)

- Include ThreeDiStatistics tool in plugin.

- Fix unmasked arrays in ``get_timeseries`` methods.

- Rename NetcdfDataSourceGroundwater to NetcdfGroundwaterDataSource.

- Add some data source tests.

- Add ``mock`` dep.

- Add new Lizard result types for downloading groundwater results.


1.2 (2018-05-24)
----------------

- Fix the aggregate find function for realz.


1.1 (2018-05-24)
----------------

- Update new aggregate result name.


1.0 (2018-05-24)
----------------

- pumplines exporter now also ignores first element

- Fix some nasty bugs in ``temp_get_value_by_timestep_nr_impl``: some
  variables (like ``qp``) only have a 1D or 2D component, and the previous
  implementation only returned that component. However, this will cause
  indexing errors, so the behavior is changed such that the method now
  always returns a masked array that is 2D+1D long if no index is passed
  as argument. Furthermore, ``np.zeros`` is changed to ``np.ma.zeros`` in
  the if block when an index is passed, which I think also might have caused
  bugs.

- let netcdf_groundwater get_timeseries return NaN istead of -9999

- improve feedback to user in case of graph tool with v2_pumpstation_view

- Close result selection window when the Escape key is pressed.

- Fix leakage name.

- Implement ``get_timeseries`` for pumplines using the newest threedigrid.

- Fix SetFID error caused by int32.

- try to show more often the object_name in graph widget (instead of 'N/A')

- use gridadmin has_pumpstations in functions get_or_create_pumpline_layer and
  available_subgrid_map_vars

- Progressbar exporting to gridadmin.sqlite starts now at 0%

- Add support for aggregate netcdf in NetcdfDataSourceGroundwater.

- add leakage to subgrid_map variables

- Add support for aggregate netcdf in NetcdfDataSourceGroundwater.

- add leakage to subgrid_map variables

- Update available vars methods using threedigrid for
  NetcdfDataSourceGroundwater.

- Implement ``available_aggregation_vars`` using threedigrid.

- Bump threedigrid to 0.2.2.

- Enable threedigrid get_timeseries for result and schematization layers

- Disable the "Calculate statistics?" prompt if there are already csv files
  available.

- Add caching of netcdf data in ``get_values_by_timestemp_nr``.

- Enable PEP8 check in build process; fix remaining PEP8 errors.

- Move icons to ``icons`` folder.

- Wrap layer generation code in transactions to improve performance (it was
  very slow on Windows, this improves it considerably so it's possible that
  it autocommited on every statement, see: http://gdal.org/drv_sqlite.html)

- Update groundwater flowlines overlapping order.

- Title of sideview dockwidget does not overlap with button anymore

- Remask masked arrays in ``get_values_by_timestemp_nr`` for
  NetcdfDataSourceGroundwater.

- Change the geometry column name of ``gridadmin.sqlite`` from ``GEOM`` to
  ``the_geom`` so that it behaves similarly to the old
  ``subgrid_map.sqlite1``. This required the use of the ``Spatialite``
  connector (subclasses QGIS db_plugin) because GDAL versions lower than 2.0
  do not support renaming of geometry columns.

- Make ``disable_sqlite_synchronous`` re-entrant (i.e.: it works expectedly
  when multiple functions that are decorated with it call each other)

- Add netcdf version (netcdf or netcdf-groundwater) detection to make
  plugin more robust

- Pinned threedigrid to working version (0.1.3)

- Animation tool: split nodes and lines into node_results, line_results,
  node_results_groundwater, line_results_groundwater (all with own styling)

- Add module base.netcdf_groundwater (relocated from base.DummyDataSourse)

- Fix find_h5_file

- Add (temporary) ad-hoc implementations of get_timeseries and
  get_values_by_timestemp_nr.

- Fix QGIS plugin updater problem on Windows with files being unable to be
  deleted because they're held open by QGIS.

- Fix cache clearer for groundwater.

- Fix incorrect 'q_lat' name.

- Set root logger level to make logging to QGIS work.

- Reproject gridadmin.sqlite to wgs84 (EPSG:4326): this fixes the side view
  tool that expects the generated layers to be in that projection.

- Add groundwater categories to styling.

- Combine nodes, flowlines and pumplines in one ``gridadmin.sqlite`` file.

- Add pumplines exporter.

- Add layer generation for ``netcdf-groundwater`` results.

- Add ``BaseDataSource`` abstract interface.

- Add h5py 2.7.0 to ``external`` libs for Windows. The files were acquired
  by installing h5py using OSGeo4W on Windows 7, and copying the installed
  files to the ``external`` folder.
- Add detection method to determine whether .h5 or id_mappping.json is present
  (this determines if the netcdf is old (no groundwater) or new (groundwater)


0.15 (2018-02-07)
-----------------

- Update lizard-connector, which contains a fix for mitigating problems with
  the ``future`` library that is used by QGIS.


0.14 (2017-11-14)
-----------------

- Fix bugs in the control structures.


0.13 (2017-10-23)
-----------------

- Update lizard-connector to 0.5 to fix the limit of 1000 results.

- Add tool "control structures".

- Remove unused code.


0.12 (2017-08-09)
-----------------

- Default maximum for QSpinBox is 99, so setValue is limited to 99. That's
  why the spinbox_search_distance maximum and spinbox_levee_distance are
  set to 5000.

- Add v2_orifice to the flowlines styling.

- Add ``v2_numerical_settings`` to the layer tree manager.

- Fix csv_join import in statistic scripts.

- Fix invalid characters in directory name in the scenario downloader.

- Fix bug in method that sets column sizes due to overwritten attribute.

- Fix bug with logout not stopping the thread and keep pulling in results.

- Add Lizard scenario result download functionality to the
  ``ThreeDiResultSelection`` tool. Some remarks about this feature:

  - To connect with the Lizard API, ``lizard-connector`` is used. Downloading
    the data happens in a worker thread because there can be many resuls.
    After logging in the user will be presented with the newest results
    immediately (this is synchronous). Progressively older results will be
    downloaded by the thread and dynamically added to the table view.

  - Chunked downloading (using append mode) is used because of the large
    files, which we do not want to keep in memory.

- Add tool "create breach locations".

- Automatically remove old entries from both the connected point and the
  calculation points table when the tool ``predict_calc_points`` is being
  re-run.

- Add a second connected point to the template for calculation points of type
  "double connected".

- [toolbox] rename 'toolbox_tools' to 'Tools', use english for toolbox
  sub-directories, remove 'Instellingen' tab, remove 'auto update logboek'
  checkbox.

- Fix ``guess_indicators.py`` tool.

- Fix clearing cache in Windows.

- Update documentation for stats module.


0.11.1 (2017-07-04)
-------------------

- Fix release that didn't include depencencies.

- Introduce hack in Makefile to fix missing depencencies.


0.11 (2017-07-03)
-----------------

- Remove checked in source code for SQLAlchemy, SpatialAlchemy
  (a.k.a. GeoAlchemy2), and PyQtGraph. These packages will now
  be installed with pip using a requirements.txt.

- Add class diagram documentation for ``ThreediDatabase``.


0.10 (2017-06-20)
-----------------

- Fix E501 (line too long) violations manually because AutoPEP8 can't fix
  those.

- Add pycodestyle checking to Travis.

- AutoPEP8 everything.

- Include model result files in repo + add more tests.

- Remove deprecated/unused code.

- Add QGIS as dependency to Travis; make nosetests work on Travis for all
  tests.

- Add a new tool (``CacheClearer``) to clear the model cache.

- Add an About tool class so that the about ``QAction`` can be added in the
  same way as the other tools.

- Add ``setup.cfg`` with coverage options (needs ``coverage``); exclude the
  external and importer source files from tests.


0.9.3 (2017-04-10)
------------------

- Changed array shape for lines array in Netcdf. This was done due to a bug in
  the calculationcore netcdf library.

- Add option to make graphs  ``absolute`` to the graph tool.

- Bugfix predict calcualtion points: For endpoints always enumerate the
  ``last_seq_id`` by one.

- Added QML styling for 2d schematisation.


0.9.2 (2017-02-14)
------------------

- Adopted the column names for the ``predict_calc_points`` command to the
  newest 3Di migrations.


0.9.1 (2016-12-12)
------------------

- Fix Travis build.

- Bugfix import sufhyd.

- Fix assertion in netCDF datasource and update QML styling.


0.9 (2016-11-28)
----------------

- Update cumulative aggregation methods.

- The user_ref field now has the following format:
  ``<content>.code#<content>.id#<table_name>#calc_pnt_nr``

- Uniform usage of ``spatialite`` instead of ``sqlite`` as ``db_type``
  variable string throughout the ThreediToolBox.

- Auto populate the ``levee_id`` column of the ``v2_connected_pnt`` table
  when a new point is being added or the location of an existing point is
  being changed.

- Auto populate the ``connected_pnt`` table from the computed calculation
  points that have a calculation type greater than 1.

- Sufhyd import:
  - logfile has same name and location as sufhyd, whith '.log' extended
  - added extra logging about used file, date adn number of objects
  - the multiple connection number (num_mvb) is added to connection codes
  - automatically add boundary when structures are not connected to end node
  - moved automatically added boundaries 1 meter

- Set required qgis version to 2.14

- Sideview:
  - bugfix: support of profiles without height (used for weirs)
  - correct relative heights for profiles which does not start at 0 height

- Bugfix: impervious surface, changed 'half_open' to 'open_paved'

- Bugfix: graph legend hover shows correct location when using 'result' layers

- support 'dry' cell values (without showing -9999 in graph)

- improved 1d modellayer styling

- Bug fix: Explicitly check for ``None`` on the return value of the
  ``calc_type_dict`` because a return value of 0 is also falsy.
  Also make sure the ``dist_calc_points`` attribute is always
  available for objects with a geometry

- Executing a select statement on an empty table using sqalchemy causes
  problems becasue it does not allow to cosume the active cursor.
  The cursor explictly has to be closed, or references to it dropped.
  Otherwise the cursor and thus the connection will be alive, and
  the database will be locked.

- Using the sqalchemy engine instead of the ``QtSql.QSqlQuery`` object
  to retrieve data from postgres or spatialite databases to make sure
  the geos extension is available (this doesn't always seem to be
  the case for windows installtions).

- Bugfix: Removed ``os.path.join`` to generate the ``db_name`` variable because
  this produced a '/' instead of a '\' for windows OS.


- Auto populate the ``connected_pnt`` table from the computed calculation
  points that have a calculation type greater than 1.

- Added the tool ``predict_calc_points``. It computes the threedicore
  calcualtion points and their calculation type.

0.8.2 (2016-09-22)
------------------

- Bugfix: layers not present in the ``styled_layers`` dict were added without
  stats, but should be added with stats.

- Sufhyd import: Fix for outlet constraints.

- Sufhyd import: Set autoincrement to max id number to prevent id errors
  (when id's are manually set)
- Slight improvement to the previous bugfix. The exact problem was with the
  pump layers which were not cloned. Now we clone them explicitly, so the
  previous bugfix isn't necessary anymore.

- Bugfix for segmentation fault when deleting the root layer group. The
  possible reason for the segfault is adding the same layer from the
  TimeseriesDatasourceModel to the QGIS map registry multiple times. The fix
  is to clone the layers so we don't get the same layers added multiple times.

- Updated the styler so that it doesn't apply styles to layers without the
  right statistic fields. If the layer doesn't have the right statistics, just
  show the layer without any styling.
- Bugfix relative path exception.


0.8.1 (2016-09-13)
------------------

- Fixes sufhyd import.


0.8 (2016-09-13)
----------------

- Added pump statistics.

- Connected python logging handler to qgis logging

- Import of sufhyd files with logging

- Made reading netCDF properties more robust.

- Reuse previously generated csv stats files.

- Added auto statistic generation via layer tree manager.

- Refactored statistic generation (put logic in separate modules).

- Refactored timeseries methods of NetcdfDataSource, more consistent
  ``get_values_of`` methods.

- Made ``get_timeseries`` only accept one netCDF variable name.

- Add Layer Manager, which loads the model and result layers.

- Add map animator for showing results on the map (first version, work in progress).

- Made the parameter config variable for the Graph and Map animator tools. Add
  parameters so almost all results from netCDF and result netCDF can be displayed.

- Optimizations in getting the time array from netCDF.

- Refactored NetcdfDataSource and included support for getting all variables
  from both regular and aggregation netCDF including getting the timeseries.

- Removed support for spatialite datasource with results.

- Changed id behavior for netcdf datasources and requesting tools. Now the
  netcdf_id or spatialite id is used (so no magic with -1, etc.)

- Added ``water op straat`` statistic to manhole statistics; refactored NcStats
  a bit.

- Updated some method names.

- Updated NetcdfDataSource so that it keeps some netCDF attributes in memory.

- Stores selected model and results in Qgs project file (\*.qgs).

- Cache generated model layers in spatialite.

- Add point markers to selected sideview points.

- Show marker of current location when hovering over graph.


0.7.1 (2016-07-25)
------------------

- Support of interflow results in graphs

- Bug fix: after closing sideview and reopening, errors were generated

- Bug fix: support of square profiles by sideview

- Bug fix: support of pure 2d models

- Bug fix: support sideview with pipes and openwater in one sideview

- Bug fix: calculation of  length of openwater channels


0.7 (2016-06-09)
----------------

- Bug fix highlight graph location on table hover


0.6 (2016-06-02)
----------------

- Bug fix stat layer joining in Windows.

- Add multiple clicks in sideview tool.

- Add channels to the sideviews.


0.5 (2016-05-20)
----------------

- Bugfix transformation clicked coordinate in RouteTool.

- Statistic scripts performance improved.

- Various bug fixes (e.g. sideview)

- Side view clicking improvements.

- Pumplines.


0.4 (2016-05-10)
----------------

- Several new features were added (side view, netCDF network generation,
  etc.), plus improvements in existing features.


0.3 (2016-04-13)
----------------

- Add tool version number to about box.

- Add support of multiple result files.

- Warn user on adding to many locations to graph.

- Only new locations will be added to graph.

- Improved color selections for timeseries after the first 20.


0.2 (2016-04-12)
----------------

- Another test release.


0.1 (2016-04-11)
----------------

- Test release.
