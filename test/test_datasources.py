from __future__ import print_function
from builtins import object
import mock
import os
import unittest
import tempfile
import shutil

try:
    from qgis.core import QgsVectorLayer, QgsFeature, QgsPointXY, QgsField, QgsGeometry
except ImportError:
    pass

from qgis.PyQt.QtCore import QVariant

try:
    from ThreeDiToolbox.datasource.spatialite import Spatialite
except ImportError:
    print("Can't import Spatialite.")
    Spatialite = None
from ThreeDiToolbox.datasource.netcdf import find_h5_file, find_aggregation_netcdf
from ThreeDiToolbox.datasource.netcdf_groundwater import (
    NetcdfGroundwaterDataSource,
    find_aggregation_netcdf_gw,
)
from ThreeDiToolbox.test.utilities import TemporaryDirectory
from ThreeDiToolbox.test.utilities import ensure_qgis_app_is_initialized

spatialite_datasource_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "data", "test_spatialite.sqlite"
)

netcdf_groundwater_datasource_nc_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "data",
    "testmodel",
    "v2_bergermeer",
    "results_3di.nc",
)


def result_data_is_available(flow_agg_must_exist=False):
    """Check if we have the necessary result data for the tests."""
    if not os.path.exists(netcdf_groundwater_datasource_nc_path):
        return False
    try:
        find_h5_file(netcdf_groundwater_datasource_nc_path)
    except IndexError:
        return False
    if flow_agg_must_exist:
        try:
            find_aggregation_netcdf(netcdf_groundwater_datasource_nc_path)
        except IndexError:
            return False
    return True


@unittest.skipIf(Spatialite is None, "Can't import Spatialite datasource")
class TestSpatialiteDataSource(unittest.TestCase):
    def setUp(self):
        ensure_qgis_app_is_initialized()
        self.tmp_directory = tempfile.mkdtemp()
        self.spatialite_path = os.path.join(self.tmp_directory, "test.sqlite")

    def tearDown(self):
        shutil.rmtree(self.tmp_directory)

    def test_create_empty_table(self):
        spl = Spatialite(self.spatialite_path + "1")

        layer = spl.create_empty_layer(
            "table_one", fields=["id INTEGER", "name TEXT NULLABLE"]
        )
        # test table is created
        self.assertIsNotNone(layer)

        self.assertTrue("table_one" in [c[1] for c in spl.getTables()])
        self.assertFalse("table_two" in spl.getTables())

        # test adding data
        self.assertEqual(layer.featureCount(), 0)
        pr = layer.dataProvider()

        feat = QgsFeature()
        feat.setAttributes([1, "test"])
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(1.0, 2.0)))

        pr.addFeatures([feat])
        self.assertEqual(layer.featureCount(), 1)

    def test_import_layer(self):
        spl = Spatialite(self.spatialite_path + "3")

        # create memory layer
        uri = "Point?crs=epsg:4326&index=yes"
        layer = QgsVectorLayer(uri, "test_layer", "memory")
        pr = layer.dataProvider()

        # add fields
        pr.addAttributes(
            [
                QgsField("id", QVariant.Int),
                QgsField("col2", QVariant.Double),
                QgsField("col3", QVariant.String, None, 20),
                QgsField("col4", QVariant.TextFormat),
            ]
        )
        # tell the vector layer to fetch changes from the provider
        layer.updateFields()
        pr = layer.dataProvider()
        feat = QgsFeature()
        feat.setAttributes([1, "test"])
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(1.0, 2.0)))
        pr.addFeatures([feat])

        spl_layer = spl.import_layer(layer, "table_one", "id")

        self.assertIsNotNone(spl_layer)
        self.assertTrue("table_one" in [c[1] for c in spl.getTables()])
        self.assertEqual(layer.featureCount(), 1)


class TestNetcdfGroundwaterDataSource(unittest.TestCase):
    def test_constructor(self):
        """Test empty constructor."""
        NetcdfGroundwaterDataSource()

    def test_sanity(self):
        nds = NetcdfGroundwaterDataSource()
        m = mock.MagicMock()
        nds._ds = m
        # sanity test
        self.assertEqual(nds.ds, m)

    def test_get_timestamps(self):
        nds = NetcdfGroundwaterDataSource()
        m = mock.MagicMock()
        nds._ds = m
        nds.get_timestamps()

    @mock.patch(
        "ThreeDiToolbox.datasource.netcdf_groundwater.NetcdfGroundwaterDataSource.available_subgrid_map_vars",
        ["s1"],
    )
    @mock.patch(
        "ThreeDiToolbox.datasource.netcdf_groundwater.NetcdfGroundwaterDataSource.gridadmin_result"
    )
    def test_get_timeseries(self, gridadmin_result_mock):
        nds = NetcdfGroundwaterDataSource()
        m = mock.MagicMock()
        nds._ds = m
        nds.get_timeseries("nodes", 3, "s1")

    def test_find_agg_fail(self):
        with TemporaryDirectory() as tempdir:
            nc_path = os.path.join(tempdir, "bla.nc")
            with self.assertRaises(IndexError):
                find_aggregation_netcdf_gw(nc_path)

    def test_find_agg_success(self):
        with TemporaryDirectory() as tempdir:
            nc_path = os.path.join(tempdir, "bla.nc")
            agg_path = os.path.join(tempdir, "aggregate_results_3di.nc")
            with open(agg_path, "w") as aggfile:
                aggfile.write("doesnt matter")
            agg_path_found = find_aggregation_netcdf_gw(nc_path)
            self.assertEqual(agg_path, agg_path_found)
