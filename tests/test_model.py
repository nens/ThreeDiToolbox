from threedi_results_analysis.threedi_plugin_model import ThreeDiPluginModel, ThreeDiGridItem, ThreeDiResultItem
from qgis.PyQt.QtCore import Qt
import unittest
from pathlib import Path


class TestModel(unittest.TestCase):
    def test_creation(self):
        model = ThreeDiPluginModel()
        self.assertTrue(model)

    def test_created_model_has_zero_grids(self):
        model = ThreeDiPluginModel()
        self.assertEqual(model.number_of_grids(), 0)

    def test_created_model_has_zero_results(self):
        model = ThreeDiPluginModel()
        self.assertEqual(model.number_of_results(), 0)

    def test_clear_1(self):
        model = ThreeDiPluginModel()
        self.grid_item = ThreeDiGridItem("c:/test/gridadmin.h5", "text")
        self.assertTrue(model.add_grid(self.grid_item))
        self.assertEqual(model.number_of_grids(), 1)
        model.clear()
        self.assertEqual(model.number_of_grids(), 0)


class TestGrid(unittest.TestCase):
    def setUp(self):
        self.model = ThreeDiPluginModel()
        self.grid_path = Path("c:/test/gridadmin.h5")

    def test_creation(self):
        item = ThreeDiGridItem(self.grid_path, "text")
        self.assertTrue(item)

    def test_adding(self):
        item = ThreeDiGridItem(self.grid_path, "text")
        self.assertTrue(self.model.add_grid(item))

    def test_removal(self):
        item = ThreeDiGridItem(self.grid_path, "text")
        self.assertTrue(self.model.add_grid(item))
        self.assertEqual(self.model.number_of_grids(), 1)
        self.assertTrue(self.model.remove_grid(item))
        self.assertEqual(self.model.number_of_grids(), 0)

    def test_contains_path_check(self):
        item = ThreeDiGridItem(self.grid_path, "text")
        self.assertTrue(self.model.add_grid(item))
        item2 = ThreeDiGridItem(self.grid_path, "text")
        self.assertFalse(self.model.add_grid(item2))

    def test_contains_path_check_extension_ignored(self):
        item = ThreeDiGridItem(self.grid_path, "text")
        self.assertTrue(self.model.add_grid(item))
        item2 = ThreeDiGridItem(self.grid_path.with_suffix('.gpkg'), "text")
        self.assertFalse(self.model.add_grid(item2))

    def test_grid_can_be_retrieved_via_id(self):
        item = ThreeDiGridItem(self.grid_path, "text")
        self.assertTrue(self.model.add_grid(item))
        retrieved_item = self.model.get_grid(item.id)
        self.assertTrue(item is retrieved_item)

        nonexisting_item = self.model.get_grid("thisidprobablydoesntexist")
        self.assertTrue(nonexisting_item is None)

    def test_id_can_be_set(self):
        item = ThreeDiGridItem(self.grid_path, "text", "anewid")
        self.assertTrue(self.model.add_grid(item))
        self.assertEqual(item.id, "anewid")

    def test_id_will_be_set(self):
        item = ThreeDiGridItem(self.grid_path, "text")
        self.assertTrue(self.model.add_grid(item))
        self.assertIsNotNone(item.id)


class TestResult(unittest.TestCase):
    def setUp(self):
        self.result_path = Path("c:/test/results_3di.nc")

        self.model = ThreeDiPluginModel()
        self.grid_item = ThreeDiGridItem("c:/test/gridadmin.h5", "text")
        self.assertTrue(self.model.add_grid(self.grid_item))

    def test_creation(self):
        item = ThreeDiResultItem(self.result_path, "text")
        self.assertTrue(item)

    def test_addition(self):
        item = ThreeDiResultItem(self.result_path, "text")
        self.assertTrue(self.model.add_result(item, self.grid_item))
        self.assertTrue(self.model.number_of_results(), 1)

    def test_removal(self):
        item = ThreeDiResultItem(self.result_path, "text")
        self.assertTrue(self.model.add_result(item, self.grid_item))
        self.assertEqual(self.model.number_of_results(), 1)
        self.assertTrue(self.model.remove_result(item))
        self.assertEqual(self.model.number_of_results(), 0)

    def test_checked_results_also_removed(self):
        item = ThreeDiResultItem(self.result_path, "text")
        item.setCheckState(Qt.CheckState.Checked)
        item2 = ThreeDiResultItem(("c:/test2/results_3di.nc"), "text")

        self.assertTrue(self.model.add_result(item, self.grid_item))
        self.assertTrue(self.model.add_result(item2, self.grid_item))
        self.assertEqual(self.model.number_of_results(), 2)
        self.assertTrue(self.model.remove_result(item))
        self.assertEqual(self.model.number_of_results(), 1)

    def test_removing_grid_removes_result(self):
        item = ThreeDiResultItem(self.result_path, "text")
        self.assertTrue(self.model.add_result(item, self.grid_item))
        self.assertEqual(self.model.number_of_results(), 1)
        self.assertTrue(self.model.remove_grid(self.grid_item))
        self.assertEqual(self.model.number_of_results(), 0)

    def test_removing_by_index(self):
        item = ThreeDiResultItem(self.result_path, "text")
        self.assertTrue(self.model.add_result(item, self.grid_item))
        self.assertEqual(self.model.number_of_results(), 1)
        self.assertTrue(self.model.remove_index(item.index()))
        self.assertEqual(self.model.number_of_results(), 0)

    def test_results_can_be_retrieved(self):
        item = ThreeDiResultItem(self.result_path, "text")
        self.assertTrue(self.model.add_result(item, self.grid_item))
        results = self.model.get_results(checked_only=False)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0] is item)

    def test_result_can_be_retrieved(self):
        item = ThreeDiResultItem(self.result_path, "text")
        self.assertTrue(self.model.add_result(item, self.grid_item))
        retrieved_item = self.model.get_result(item.id)
        self.assertTrue(item is retrieved_item)

        retrieved_item = self.model.get_result("thisidisprobablynotused")
        self.assertFalse(retrieved_item)

    def test_parent_should_be_provided(self):
        item = ThreeDiResultItem(self.result_path, "text")
        self.assertFalse(self.model.add_result(item, None))
