from threedi_results_analysis.processing.deps.sufhyd.import_sufhyd_main import Importer
from threedi_results_analysis.processing.deps.sufhyd.sufhyd_importer import SufhydReader

import unittest


class TestReadSufhyd(unittest.TestCase):
    def test_knp(self):
        knp = "*KNP   0000NOORD1                 164371100  388463700   19.14  0   100   100.000        00    5.00                   "

        sufhyd = SufhydReader(knp)
        sufhyd.parse_input()
        data = sufhyd.get_data()

        self.assertEqual(len(data["manholes"]), 1)

        obj = data["manholes"][0]
        self.assertEqual(obj.data["code"], "0000NOORD1")
        self.assertEqual(obj.data["basin"], None)
        self.assertTupleEqual(obj.data["geom"], ("POINT", (164371.1, 388463.7), 28992))
        self.assertEqual(obj.data["surface_level"], 19.14)
        self.assertEqual(obj.data["width"], 100.0)
        self.assertEqual(obj.data["length"], None)
        self.assertEqual(obj.data["bottom_level"], 5.00)
        self.assertEqual(obj.data["material"], None)

    def test_lei(self):
        lei = "*LEI   0000NOORD1   0000NOORD2      5.00    2.002561.63           1.500  2.000 02                                      "

        sufhyd = SufhydReader(lei)
        sufhyd.parse_input()
        data = sufhyd.get_data()

        self.assertEqual(len(data["pipes"]), 1)

        obj = data["pipes"][0]
        self.assertEqual(obj.data["code"], "0000NOORD1_0000NOORD2")
        self.assertEqual(obj.data["basin"], None)

        self.assertEqual(obj.data["connection_node_start.code"], "0000NOORD1")
        self.assertEqual(obj.data["connection_node_end.code"], "0000NOORD2")
        self.assertEqual(obj.data["original_length"], 2561.63)
        self.assertDictEqual(
            obj.data["cross_section_details"],
            {"width": 1.500, "height": 2.000, "shape": "egg"},
        )
        self.assertEqual(obj.data["invert_level_start_point"], 5.00)
        self.assertEqual(obj.data["invert_level_end_point"], 2.00)
        self.assertEqual(obj.data["sewerage_type"], None)
        self.assertEqual(obj.data["material"], None)

    def test_gemaal(self):

        gem = "*GEM   00000IILST   0000GEMAAL 0             3  625.83   12.66   12.61                 3000.00   12.96   12.66                 3300.00   13.96   13.66                 3330.00   14.96   14.66"

        sufhyd = SufhydReader(gem)
        sufhyd.parse_input()
        data = sufhyd.get_data()

        self.assertEqual(len(data["pumpstations"]), 4)

        obj = data["pumpstations"][0]
        self.assertEqual(obj.data["code"], "00000IILST_0000GEMAAL_1")
        self.assertEqual(obj.data["connection_node_start.basin"], None)
        self.assertEqual(obj.data["connection_node_start.code"], "00000IILST")
        self.assertEqual(obj.data["connection_node_end.code"], "0000GEMAAL")
        self.assertEqual(obj.data["start_level"], 12.66)
        self.assertEqual(obj.data["lower_stop_level"], 12.61)
        self.assertEqual(obj.data["upper_stop_level"], None)
        self.assertEqual(obj.data["capacity"], 625.83)

    def test_overstort(self):
        ovs = "*OVS   000000SON2                10.000   17.14 0.941   1   17.04"

        sufhyd = SufhydReader(ovs)
        sufhyd.parse_input()
        data = sufhyd.get_data()

        self.assertEqual(len(data["weirs"]), 1)

        obj = data["weirs"][0]
        self.assertEqual(obj.data["code"], "000000SON2_")
        self.assertEqual(obj.data["connection_node_start.code"], "000000SON2")
        self.assertEqual(obj.data["connection_node_end.code"], "")
        self.assertDictEqual(
            obj.data["cross_section_details"],
            {"width": 10.000, "height": 1.000, "shape": "rectangle"},
        )
        self.assertEqual(obj.data["crest_type"], 1)
        self.assertEqual(obj.data["crest_level"], 17.14)
        self.assertEqual(obj.data["discharge_coefficient_positive"], 0.941)
        self.assertEqual(obj.data["discharge_coefficient_negative"], 0.0)
        self.assertEqual(obj.data["sewerage"], True)
        self.assertDictEqual(
            obj.data["boundary_details"],
            {"waterlevel": 17.04, "winter_wl": None, "summer_wl": None},
        )

    def test_doorlaat(self):
        drl = (
            "*DRL   0000G2175U   0000G2175W 0  3.300  0.850 02   16.02 0.600          2"
        )

        sufhyd = SufhydReader(drl)
        sufhyd.parse_input()
        data = sufhyd.get_data()

        self.assertEqual(len(data["orifices"]), 1)

        obj = data["orifices"][0]
        self.assertEqual(obj.data["code"], "0000G2175U_0000G2175W")
        self.assertEqual(obj.data["connection_node_start.code"], "0000G2175U")
        self.assertEqual(obj.data["connection_node_end.code"], "0000G2175W")
        self.assertDictEqual(
            obj.data["cross_section_details"],
            {"width": 3.300, "height": 0.850, "shape": "egg"},
        )
        self.assertEqual(obj.data["crest_type"], 1)
        self.assertEqual(obj.data["crest_level"], 16.02)
        self.assertEqual(obj.data["discharge_coefficient_positive"], 0.0)
        self.assertEqual(obj.data["discharge_coefficient_negative"], 0.600)
        self.assertEqual(obj.data["sewerage"], True)

    def test_uitlaat(self):
        uit = "*UIT   000000VBT1   000BYPASS1 0   -4.80                "

        sufhyd = SufhydReader(uit)
        sufhyd.parse_input()
        data = sufhyd.get_data()

        self.assertEqual(len(data["outlets"]), 1)

        obj = data["outlets"][0]
        self.assertEqual(obj.data["connection_node.code"], "000000VBT1")
        self.assertEqual(obj.data["value"], -4.80)

    def test_bergend_oppervlak(self):

        bop = "*BOP 016720Rc1                      1  100.00   80.0"

        sufhyd = SufhydReader(bop)
        sufhyd.parse_input()
        data = sufhyd.get_data()

        self.assertEqual(len(data["storage"]), 1)

        obj = data["storage"][0]
        self.assertEqual(obj.data["connection_node.code"], "016720Rc1")
        self.assertEqual(obj.data["bottom_level"], 100.00)
        self.assertEqual(obj.data["storage_area"], 80.0)

    def test_bergend_oppervlak2(self):
        bop = "*AFV   0000011111                       9.00600000.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00"

        sufhyd = SufhydReader(bop)
        sufhyd.parse_input()
        data = sufhyd.get_data()

        self.assertEqual(len(data["impervious_surfaces"]), 2)

        obj = data["impervious_surfaces"][0]
        self.assertEqual(obj["code"], "0000011111")


class TestImportSufhyd(unittest.TestCase):

    file_name = "c:\\tmp\\test.hyd"

    def test_read(self):

        importer = Importer(self.file_name)

        data = importer.load_sufhyd_data()

        self.assertTrue(len(data["pipes"]) > 0)
