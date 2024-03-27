from qgis.PyQt.QtCore import QObject, pyqtSignal, pyqtSlot
from pathlib import Path
from qgis.core import Qgis, QgsVectorLayer
from threedi_results_analysis.threedi_plugin_model import ThreeDiGridItem, ThreeDiResultItem
from threedi_results_analysis.utils.user_messages import messagebar_message, pop_up_critical
from threedi_results_analysis.threedi_plugin_model import ThreeDiPluginModel
from threedi_results_analysis.utils.constants import TOOLBOX_MESSAGE_TITLE
from threedi_results_analysis.utils.utils import listdirs
import h5py
import logging
logger = logging.getLogger(__name__)


class ThreeDiPluginModelValidator(QObject):
    """
    This class validates 3Di computation grid and result files. When
    a grid or result is valid, a signal is emited
    so listeners can handle accordingly.
    """
    grid_valid = pyqtSignal(ThreeDiGridItem)
    result_valid = pyqtSignal(ThreeDiResultItem, ThreeDiGridItem)
    grid_invalid = pyqtSignal(ThreeDiGridItem)
    result_invalid = pyqtSignal(ThreeDiResultItem, ThreeDiGridItem)

    def __init__(self, model: ThreeDiPluginModel, *args, **kwargs):
        self.model = model
        super().__init__(*args, **kwargs)

    @pyqtSlot(str)
    def validate_grid(self, grid_file: str, result_slug: str = None) -> ThreeDiGridItem:
        """
        Validates the grid and returns the new (or already existing) ThreeDiGridItem. Also emits signal.

        if required_slug is not None, the first grid in the model with this slug will be selected.

        If not, the validator will check whether a grid with the same slug is found as the grid_file.

        If not, the validor will create a new ThreeDiGridItem and emit the grid_valid signal.
        """
        logger.info(f"Validate_grid({grid_file}, {result_slug}")

        # First check whether a grid with the result_slug already exists
        if result_slug:
            for grid in self.model.get_grids():
                # Check whether corresponding grid item belongs to same model as result
                other_grid_model_slug = ThreeDiPluginModelValidator.get_grid_slug(Path(grid.path))
                if result_slug == other_grid_model_slug:
                    print("using result slug")
                    messagebar_message(TOOLBOX_MESSAGE_TITLE, "Result attached to computational grid that was already loaded.", Qgis.Info, 5)
                    return grid

        # Check whether the model already contains a grid with the new grid files slug
        if grid_file:
            grid_model_slug = ThreeDiPluginModelValidator.get_grid_slug(Path(grid_file))
            if grid_model_slug:
                for grid in self.model.get_grids():
                    # Check whether corresponding grid item belongs to same model as result
                    other_grid_model_slug = ThreeDiPluginModelValidator.get_grid_slug(Path(grid.path))
                    if grid_model_slug == other_grid_model_slug:
                        print("using grid slug")
                        messagebar_message(TOOLBOX_MESSAGE_TITLE, "Result attached to computational grid that was already loaded.", Qgis.Info, 5)
                        return grid

        if not grid_file:
            messagebar_message(TOOLBOX_MESSAGE_TITLE, "No computational grid for this result could be found, aborting", Qgis.Critical, 5)
            return None

        # Check whether model already contains this grid file.
        for i in range(self.model.invisibleRootItem().rowCount()):
            grid_item = self.model.invisibleRootItem().child(i)
            if grid_item.path.with_suffix("") == Path(grid_file).with_suffix(""):
                messagebar_message(TOOLBOX_MESSAGE_TITLE, "This computional grid was already loaded.", Qgis.Info, 5)
                self.grid_invalid.emit(ThreeDiGridItem(Path(grid_file), ""))
                return grid_item

        # Note that in the 3Di M&S working directory setup, each results
        # folder in the revision can contain the same gridadmin file. Check
        # whether there is a grid loaded from one of these result folders.
        folder = Path(grid_file).parent
        if folder.parent.name == 'results':
            if str(folder.parent.parent.name).startswith('revision'):
                result_folders = [Path(d) for d in listdirs(folder.parent)]

                # Iterate over the grids
                for i in range(self.model.invisibleRootItem().rowCount()):
                    grid_item = self.model.invisibleRootItem().child(i)
                    assert isinstance(grid_item, ThreeDiGridItem)
                    grid_folder = Path(grid_item.path).parent
                    if grid_folder in result_folders:
                        messagebar_message(TOOLBOX_MESSAGE_TITLE, "This computional grid was already loaded.", Qgis.Info, 5)
                        # Todo: should we do a simple shallow file-compare?
                        self.grid_invalid.emit(grid_item)
                        return grid_item

        new_grid = ThreeDiGridItem(Path(grid_file), "")
        self.grid_valid.emit(new_grid)
        return new_grid

    @pyqtSlot(str, str)
    def validate_result_grid(self, results_path: str, grid_path: str):
        """
        Validate the result, but first validate (and add) the grid.
        """
        # First check whether this is the right grid, or a more appropriate is already
        # in the model (with same slug)
        result_model_slug = ThreeDiPluginModelValidator.get_result_slug(Path(results_path))
        logger.info(f"Validating {results_path} ({result_model_slug}) and {grid_path}")
        grid_item = self.validate_grid(grid_path, result_model_slug)
        if not grid_item:
            messagebar_message(TOOLBOX_MESSAGE_TITLE, "No computational grid for this result could be found, aborting", Qgis.Critical, 5)
            return

        self._validate_result(results_path, grid_item)

    def _validate_result(self, results_path: str, grid_item: ThreeDiGridItem) -> bool:
        logger.info(f"Validating result with grid item {grid_item.text()}")
        """
        Validate the result when added to the selected grid item. Returns True
        on success and emits result_valid or result_invalid.
        """
        def fail(msg):
            messagebar_message(TOOLBOX_MESSAGE_TITLE, msg, Qgis.Warning, 5)
            self.result_invalid.emit(result_item, grid_item)
            return False

        result_item = ThreeDiResultItem(Path(results_path))

        if self.model.contains(Path(results_path), True):
            return fail("This result was already loaded")

        # Check correct file name
        if not result_item.path.name == "results_3di.nc":
            return fail("Unexpected file name for results file")

        # Check opening with h5py, detects a.o. incomplete downloads
        try:
            results_h5 = h5py.File(result_item.path.open("rb"), "r")
        except OSError as error:
            if "truncated file" in str(error):
                return fail(
                    f"Results file {result_item.path} is incomplete. "
                    "If possible, copy or download it again."
                )
            return fail(f"Results file cannot be opened: {str(error.errno)} {str(error.strerror)} {str(error.args)}")

        # Try to open accompanying aggregate results file
        aggregate_results_path = result_item.path.with_name("aggregate_results_3di.nc")
        if aggregate_results_path.exists():
            try:
                h5py.File(aggregate_results_path.open("rb"), "r")
            except OSError as error:
                if "truncated file" in str(error):
                    return fail(
                        f"Aggregate results file {aggregate_results_path} "
                        "is incomplete. If possible, copy or download it "
                        "again."
                    )
                return fail("Aggregate results file cannot be opened.")

        # Any modern enough calc core adds a 'threedicore_version' atribute
        if "threedicore_version" not in results_h5.attrs:
            return fail("Result file is too old and cannot be opened with 3Di Result Analysis.")

        # Check whether corresponding grid item belongs to same model as result
        result_model_slug = ThreeDiPluginModelValidator.get_result_slug(result_item.path)

        grid_model_slug = ThreeDiPluginModelValidator.get_grid_slug(grid_item.path)
        print(f"Comparing grid slug: {grid_model_slug} to result slug: {result_model_slug}")
        logger.info(f"Comparing grid slug: {grid_model_slug} to result slug: {result_model_slug}")

        if not grid_model_slug or not result_model_slug:
            msg = "No grid or result slug available, unable to validate to which 3Di model this computational grid or result belongs"
            messagebar_message(TOOLBOX_MESSAGE_TITLE, msg, Qgis.Warning, 5)
        elif result_model_slug != grid_model_slug:
            # Really wrong grid, find a grid with the right slug, if not available, abort with pop-up
            root_node = grid_item.model().invisibleRootItem()
            for i in range(root_node.rowCount()):
                other_grid_item = root_node.child(i)
                other_grid_model_slug = ThreeDiPluginModelValidator.get_grid_slug(other_grid_item.path)

                print("comparing result slug to other grids again")
                if result_model_slug == other_grid_model_slug:
                    messagebar_message(TOOLBOX_MESSAGE_TITLE, "Result attached to computational grid that was already loaded.", Qgis.Warning, 5)

                    # Propagate the result with the new parent grid
                    self.result_valid.emit(result_item, other_grid_item)
                    return True

            msg = "No computational grid for this result could be found, cannot load this result."
            pop_up_critical(msg)
            return fail(msg)

        self.result_valid.emit(result_item, grid_item)
        return True

    @staticmethod
    def get_grid_slug(geopackage_path: Path) -> str:
        meta_layer = QgsVectorLayer(str(geopackage_path.with_suffix(".gpkg")) + "|layername=meta", "meta", "ogr")

        if not meta_layer.isValid() or not (meta_layer.featureCount() == 1):
            logger.warning("Invalid, zero or more than 1 meta data table. Unable to derive slug")
            return None

        # Take first
        meta = next(meta_layer.getFeatures())
        return meta["model_slug"]

    @staticmethod
    def get_result_slug(netcdf_path: Path) -> str:
        results_h5 = h5py.File(netcdf_path.open("rb"), "r")
        result_model_slug = results_h5.attrs['model_slug'].decode()
        if result_model_slug == "NO SLUG FOUND":
            result_model_slug = ""

        return result_model_slug
