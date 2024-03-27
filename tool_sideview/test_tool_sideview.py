from threedi_results_analysis.tool_sideview.sideview import ThreeDiSideView

import mock
import unittest


class TestThreeDiSideView(unittest.TestCase):
    def setUp(self):
        """test whether ThreeDiSideView can be instantiated"""
        iface = mock.Mock()
        self.sideview = ThreeDiSideView(iface, None)

    def test_icon_path_is_set(self):
        self.assertEqual(
            self.sideview.icon_path, "/root/.local/share/QGIS/QGIS3/profiles/default/python/plugins/threedi_results_analysis/icons/icon_route.png"
        )
