from threedi_results_analysis.threedi_plugin_model import ThreeDiPluginModel, ThreeDiGridItem, ThreeDiResultItem
from threedi_results_analysis.threedi_plugin_model_validation import ThreeDiPluginModelValidator
from threedi_results_analysis.tests.utilities import ensure_qgis_app_is_initialized
import unittest
from pathlib import Path
from mock import patch, call


@patch("threedi_results_analysis.threedi_plugin_model_validation.ThreeDiResultItem")
@patch("threedi_results_analysis.threedi_plugin_model_validation.h5py.File")
class TestResultValidation(unittest.TestCase):
    def setUp(self):
        ensure_qgis_app_is_initialized()
        self.model = ThreeDiPluginModel()
        self.grid_item = ThreeDiGridItem(Path("c:/test/gridadmin.h5"), "text")
        self.model.add_grid(self.grid_item)
        self.validator = ThreeDiPluginModelValidator(self.model)

    def test_creation(self, *args):
        validator = ThreeDiPluginModelValidator(self.model)
        self.assertTrue(validator)

    def test_invalid_result_filename(self, test_h5, result_item_mock):
        with patch.object(self.validator, "result_invalid") as result_invalid:
            self.assertFalse(self.validator._validate_result("c:/test/incorrectfilename_3di.nc", self.grid_item))
            result_invalid.emit.assert_called_once_with(result_item_mock.return_value, self.grid_item)

    def test_missing_threedicore_function(self, test_h5, result_item_mock):
        test_h5.return_value.attrs = ["no_threedicore_version"]
        result_item_mock.return_value.path.name = "results_3di.nc"

        with patch.object(self.validator, "result_invalid") as result_invalid:
            self.assertFalse(self.validator._validate_result("c:/test/results_3di.nc", self.grid_item))
            result_invalid.emit.assert_called_once_with(result_item_mock.return_value, self.grid_item)

    def test_unknown_slug_function(self, test_h5, result_item_mock):
        test_h5.return_value.attrs = {"threedicore_version": "", "model_slug": "result_slug".encode()}
        result_item_mock.return_value.path.name = "results_3di.nc"

        with patch.object(self.validator, "result_invalid") as result_invalid, patch.object(
                ThreeDiPluginModelValidator, "get_grid_slug") as grid_slug:
            grid_slug.return_value = "bla_slug"
            self.assertFalse(self.validator._validate_result("c:/test/results_3di.nc", self.grid_item))
            result_invalid.emit.assert_called_once_with(result_item_mock.return_value, self.grid_item)

    def test_result_item_is_valid(self, test_h5, result_item_mock):
        test_h5.return_value.attrs = {"threedicore_version": "", "model_slug": "result_slug".encode()}
        result_item_mock.return_value.path.name = "results_3di.nc"

        with patch.object(self.validator, "result_valid") as result_valid, patch.object(
                ThreeDiPluginModelValidator, "get_grid_slug") as grid_slug:
            grid_slug.return_value = "result_slug"
            self.assertTrue(self.validator._validate_result("c:/test/results_3di.nc", self.grid_item))
            result_valid.emit.assert_called_once_with(result_item_mock.return_value, self.grid_item)

    def test_result_item_is_reparented(self, test_h5, result_item_mock):
        test_h5.return_value.attrs = {"threedicore_version": "", "model_slug": "result_slug".encode()}
        result_item_mock.return_value.path.name = "results_3di.nc"

        # add a second grid which will have the right slug
        right_grid_item = ThreeDiGridItem(Path("c:/otherfolder/gridadmin.h5"), "text2")
        self.model.add_grid(right_grid_item)

        with patch.object(self.validator, "result_valid") as result_valid, patch.object(
                ThreeDiPluginModelValidator, "get_grid_slug") as grid_slug:
            grid_slug.side_effect = ["bla", "bla", "result_slug"]
            self.assertTrue(self.validator._validate_result("c:/test/results_3di.nc", self.grid_item))
            result_valid.emit.assert_called_once_with(result_item_mock.return_value, right_grid_item)

    def test_result_item_is_already_present(self, test_h5, result_item_mock):
        test_h5.return_value.attrs = {"threedicore_version": "", "model_slug": "result_slug".encode()}
        result_item_mock.return_value.path.name = "results_3di.nc"

        self.model.add_result(ThreeDiResultItem(Path("c:/test/results_3di.nc"), "text"), self.grid_item)

        with patch.object(self.validator, "result_invalid") as result_invalid, patch.object(
                ThreeDiPluginModelValidator, "get_grid_slug") as grid_slug:
            grid_slug.return_value = "result_slug"
            self.assertFalse(self.validator._validate_result("c:/test/results_3di.nc", self.grid_item))
            result_invalid.emit.assert_called_once_with(result_item_mock.return_value, self.grid_item)

    def test_grid_result_with_result_slug_if_already_present(self, test_h5, result_item_mock):
        wrong_grid = ThreeDiGridItem(Path("c:/thisfolder/gridadmin.h5"), "text2")
        self.model.add_grid(wrong_grid)

        correct_grid = ThreeDiGridItem(Path("c:/otherfolder/gridadmin.h5"), "text2")
        self.model.add_grid(correct_grid)

        result_item_mock.return_value.path.name = "results_3di.nc"
        test_h5.return_value.attrs = {"threedicore_version": "", "model_slug": "result_slug".encode()}

        with patch.object(self.validator, "result_valid") as result_valid, patch.object(
            ThreeDiPluginModelValidator, "get_grid_slug") as grid_slug, patch.object(
                    ThreeDiPluginModelValidator, "get_result_slug") as result_slug:
            grid_slug.side_effect = ["wrong_slug", "wrong_slug", "result_slug", "result_slug"]
            result_slug.side_effect = ["result_slug", "result_slug"]

            self.validator.validate_result_grid("c:/test/results_3di.nc", "c:/thisfolder/gridadmin.h5")
            # resets side effect
            grid_slug.side_effect = ["wrong_slug", "wrong_slug", "result_slug", "result_slug"]
            result_slug.side_effect = ["result_slug", "result_slug"]
            self.validator.validate_result_grid("c:/test43/results_3di.nc", "c:/otherfolder/gridadmin.h5")

            calls = [call(result_item_mock.return_value, correct_grid), call(result_item_mock.return_value, correct_grid)]
            result_valid.emit.assert_has_calls(calls)

    def test_grid_result_with_grid_slug_if_already_present(self, test_h5, result_item_mock):
        wrong_grid = ThreeDiGridItem(Path("c:/thisfolder/gridadmin.h5"), "text2")
        self.model.add_grid(wrong_grid)

        correct_grid = ThreeDiGridItem(Path("c:/otherfolder/gridadmin.h5"), "text2")
        self.model.add_grid(correct_grid)

        result_item_mock.return_value.path.name = "results_3di.nc"
        test_h5.return_value.attrs = {"threedicore_version": "", "model_slug": "result_slug".encode()}

        with patch.object(self.validator, "result_valid") as result_valid, patch.object(
            ThreeDiPluginModelValidator, "get_grid_slug") as grid_slug, patch.object(
                    ThreeDiPluginModelValidator, "get_result_slug") as result_slug:
            # last side effect is in _validate_result, prevent for being reparent
            grid_slug.side_effect = ["wrong_slug", "wrong_slug", "wrong_slug", "current_grid", "wrong_slug", "wrong_slug", "current_grid", "result_slug"]
            result_slug.return_value = "result_slug"

            self.validator.validate_result_grid("c:/test/results_3di.nc", "c:/thisfolder/gridadmin.h5")
            calls = [call(result_item_mock.return_value, correct_grid)]
            result_valid.emit.assert_has_calls(calls)

            # Do it again, but let the result be reparent in _validate_result to wrong_grid
            grid_slug.side_effect = ["wrong_slug", "wrong_slug", "wrong_slug", "current_grid", "wrong_slug", "wrong_slug", "current_grid", "current_grid", "wrong_slug", "result_slug"]
            self.validator.validate_result_grid("c:/test/results_3di.nc", "c:/thisfolder/gridadmin.h5")
            calls = [call(result_item_mock.return_value, wrong_grid)]
            result_valid.emit.assert_has_calls(calls)


class TestGridValidator(unittest.TestCase):
    def setUp(self):
        ensure_qgis_app_is_initialized()
        self.model = ThreeDiPluginModel()

    def test_grid_is_valid(self):
        validator = ThreeDiPluginModelValidator(self.model)
        with patch.object(validator, "grid_valid") as grid_valid:
            new_grid_item = validator.validate_grid("c:/test/gridadmin.h5")
            grid_valid.emit.assert_called_once_with(new_grid_item)

    def test_grid_already_present(self):
        grid_item = ThreeDiGridItem(Path("c:/test/gridadmin.h5"), "text")
        self.model.add_grid(grid_item)

        validator = ThreeDiPluginModelValidator(self.model)
        with patch.object(validator, "grid_invalid") as grid_invalid:
            existing_grid = validator.validate_grid("c:/test/gridadmin.h5")
            grid_invalid.emit.assert_called_once()
            self.assertTrue(existing_grid is grid_item)

    def test_grid_with_same_slug_as_result_is_retrieved_instead_of_created(self):
        wrong_grid_item = ThreeDiGridItem(Path("c:/thisfolder/gridadmin.h5"), "text2")
        self.model.add_grid(wrong_grid_item)

        right_grid_item = ThreeDiGridItem(Path("c:/otherfolder/gridadmin.h5"), "text2")
        self.model.add_grid(right_grid_item)

        validator = ThreeDiPluginModelValidator(self.model)
        with patch.object(validator, "grid_valid") as grid_valid, patch.object(
                ThreeDiPluginModelValidator, "get_grid_slug") as grid_slug:
            grid_slug.side_effect = ["bah45", "result_slug"]
            selected_grid = validator.validate_grid("c:/test/gridadmin.h5", "result_slug")

            self.assertTrue(selected_grid is right_grid_item)
            grid_valid.emit.assert_not_called()

    def test_grid_with_same_slug_as_grid_is_retrieved(self):
        wrong_grid_item = ThreeDiGridItem(Path("c:/thisfolder/gridadmin.h5"), "text2")
        self.model.add_grid(wrong_grid_item)

        right_grid_item = ThreeDiGridItem(Path("c:/otherfolder/gridadmin.h5"), "text2")
        self.model.add_grid(right_grid_item)

        validator = ThreeDiPluginModelValidator(self.model)
        with patch.object(validator, "grid_valid") as grid_valid, patch.object(
                ThreeDiPluginModelValidator, "get_grid_slug") as grid_slug:
            grid_slug.side_effect = ["result_slug", "bla", "result_slug"]
            self.assertTrue(validator.validate_grid("c:/test/gridadmin.h5") is right_grid_item)
            grid_valid.emit.assert_not_called()

    def test_grid_with_different_slug_is_created(self):
        # add a first grid which will have the right slug
        right_grid_item = ThreeDiGridItem(Path("c:/otherfolder/gridadmin.h5"), "text2")
        self.model.add_grid(right_grid_item)

        validator = ThreeDiPluginModelValidator(self.model)
        with patch.object(validator, "grid_valid") as grid_valid, patch.object(
                ThreeDiPluginModelValidator, "get_grid_slug") as grid_slug:
            grid_slug.side_effect = ["result_slug", "bla"]
            created_grid = validator.validate_grid("c:/test/gridadmin.h5")
            self.assertTrue(created_grid is not right_grid_item)
            grid_valid.emit.assert_called_once_with(created_grid)

    def test_appropriate_grid_found(self):
        wrong_grid_item = ThreeDiGridItem(Path("c:/test/gridadmin.h5"), "text2")
        self.model.add_grid(wrong_grid_item)
        right_grid_item = ThreeDiGridItem(Path("c:/otherfolder/gridadmin.h5"), "text2")
        self.model.add_grid(right_grid_item)

        validator = ThreeDiPluginModelValidator(self.model)
        with patch.object(validator, "grid_valid") as grid_valid, patch.object(
                ThreeDiPluginModelValidator, "get_grid_slug") as grid_slug:
            grid_slug.side_effect = ["bla", "result_slug"]
            created_grid = validator.validate_grid("", "result_slug")
            self.assertTrue(created_grid is right_grid_item)
            grid_valid.emit.assert_not_called()

    def test_no_appropriate_grid_found(self):
        wrong_grid_item = ThreeDiGridItem(Path("c:/test/gridadmin.h5"), "text2")
        self.model.add_grid(wrong_grid_item)
        also_wrong_grid_item = ThreeDiGridItem(Path("c:/otherfolder/gridadmin.h5"), "text2")
        self.model.add_grid(also_wrong_grid_item)

        validator = ThreeDiPluginModelValidator(self.model)
        with patch.object(
                ThreeDiPluginModelValidator, "get_grid_slug") as grid_slug:
            grid_slug.side_effect = ["bla", "bla"]
            created_grid = validator.validate_grid("", "result_slug")
            self.assertTrue(created_grid is None)
