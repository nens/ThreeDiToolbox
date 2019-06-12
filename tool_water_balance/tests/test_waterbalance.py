from qgis.core import QgsCoordinateReferenceSystem
from qgis.core import QgsCoordinateTransform
from qgis.core import QgsGeometry
from qgis.core import QgsPoint
from qgis.core import QgsProject
from ThreeDiToolbox.tool_result_selection.models import TimeseriesDatasourceModel
from ThreeDiToolbox.tool_water_balance.tools.waterbalance import WaterBalanceCalculation

import os.path
import unittest


test_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)))


@unittest.skip("TODO: add the required files")
class WaterbalanceClassTest(unittest.TestCase):
    """Test the QGIS Environment"""

    def setUp(self):
        model_dir = os.path.join(test_dir, "bigdata", "vecht_rekenen_tekenen_demo")

        self.ts_datasources = TimeseriesDatasourceModel()
        self.ts_datasources.spatialite_filepath = os.path.join(
            model_dir, "vecht_s2.sqlite"
        )
        items = [
            {
                "type": "netcdf",
                "name": "subgrid_map",
                "file_path": os.path.join(
                    model_dir, "vecht_s2_scenario", "results", "subgrid_map.nc"
                ),
            }
        ]
        self.ts_datasources.insertRows(items)

        polygon_points = [
            QgsPoint(216196, 502444),
            QgsPoint(216196, 502371),
            QgsPoint(216210, 502371),
            QgsPoint(216210, 502444),
            QgsPoint(216196, 502444),
        ]
        self.polygon = QgsGeometry.fromPolygonXY([polygon_points])

        tr = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem(
                28992, QgsCoordinateReferenceSystem.PostgisCrsId
            ),
            QgsCoordinateReferenceSystem(
                4326, QgsCoordinateReferenceSystem.PostgisCrsId
            ),
            QgsProject.instance(),
        )
        self.polygon.transform(tr)

    def test_link_selection(self):
        calc = WaterBalanceCalculation(self.ts_datasources)
        links = calc.get_incoming_and_outcoming_link_ids(self.polygon, None)

        self.assertListEqual(links["2d_in"], [2253, 2254, 2255, 2256, 9610])
        self.assertListEqual(links["2d_out"], [2265, 2266, 2267, 2268, 12861])

    def test_flow_aggregation(self):
        calc = WaterBalanceCalculation(self.ts_datasources)
        flow_links = calc.get_incoming_and_outcoming_link_ids(self.polygon, None)

        calc.get_aggregated_flows(flow_links)
