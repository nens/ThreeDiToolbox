from pathlib import Path
from typing import List
from functools import cached_property
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot
from qgis.PyQt.QtCore import QModelIndex, Qt
from qgis.PyQt.QtGui import QStandardItem, QStandardItemModel
from threedi_results_analysis.datasource.threedi_results import ThreediResult

import logging
import uuid

logger = logging.getLogger(__name__)

already_used_ids = []


def _generate_identifier() -> str:
    global already_used_ids
    while True:
        id = str(uuid.uuid4())
        if id not in already_used_ids:
            already_used_ids.append(id)
            return id


class ThreeDiModelItem(QStandardItem):
    """
    Base class for all model items
    """
    id: str  # uuid

    def __init__(self, id: str, *args, **kwargs):
        self.id = id if id else _generate_identifier()
        super().__init__(*args, **kwargs)


class ThreeDiGridItem(ThreeDiModelItem):
    """
    A model item for computation grids
    """
    def __init__(self, path: Path, text: str, id: str = None, *args, **kwargs):
        """
        Args:
            path: Path to gridadmin.gpkg
            text: Name in the GUI
        """
        super().__init__(id, *args, **kwargs)
        self.path = path
        self.setSelectable(True)
        self.setEditable(True)
        self.setText(text)

        # map from table name to layer id, required to check
        # whether a layer is already loaded
        self.layer_ids = {}

        # We only want signals when the text has been changed
        self._old_text = ""

        # layer info
        self.layer_group = None


class ThreeDiResultItem(ThreeDiModelItem):
    """
    A model item for 3Di results.
    """
    def __init__(self, path: Path, id: str = None, *args, **kwargs):
        """
        Args:
            path: Path tp results_3di.nc
        """
        super().__init__(id, *args, **kwargs)
        self.path = path
        self.setCheckable(True)
        self.setCheckState(Qt.CheckState.Unchecked)

        # layer info
        # map of grid layers id to added result field names (tuple of ids)
        # (Two fields, initial_value and result, are required)
        # Used for cleaning up result fields when result is removed
        self._result_field_names = {}

        # Used to distinguish item changed and item checked
        self._old_text = ""

        # Used by Graph tool
        self._pattern = None

        self._timedelta = None

    @cached_property
    def threedi_result(self):
        # ThreediResult is a wrapper around a theedigrid's
        # netcdf support
        return ThreediResult(self.path, self.parent().path.with_suffix(".h5"))


class ThreeDiPluginModel(QStandardItemModel):
    """
    The datamodel of the Toolbox.

    All grids and results are stored in this
    hierarchical model as items. The model itself does not contain much
    functionality, it merely keeps track of the grids and results and emits
    signals when the model is modified.
    """
    grid_added = pyqtSignal(ThreeDiGridItem)
    result_added = pyqtSignal(ThreeDiResultItem)
    result_checked = pyqtSignal(ThreeDiResultItem)
    result_unchecked = pyqtSignal(ThreeDiResultItem)
    result_changed = pyqtSignal(ThreeDiResultItem)
    grid_changed = pyqtSignal(ThreeDiGridItem)
    grid_removed = pyqtSignal(ThreeDiGridItem)
    result_removed = pyqtSignal(ThreeDiResultItem)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setColumnCount(2)
        self.itemChanged.connect(self._item_changed)

    @pyqtSlot(ThreeDiGridItem)
    def add_grid(self, grid_item: ThreeDiGridItem) -> bool:
        """Adds a grid item to the model, emits grid_added"""
        if self.contains(grid_item.path, ignore_suffix=True):
            return False

        grid_item._old_text = grid_item.text()
        self.invisibleRootItem().appendRow(grid_item)
        self.grid_added.emit(grid_item)

        return True

    @pyqtSlot(ThreeDiResultItem, ThreeDiGridItem)
    def add_result(self, result_item: ThreeDiResultItem, parent_item: ThreeDiGridItem) -> bool:
        """Adds a result item to the parent grid item, emits result_added"""
        if self.contains(result_item.path):
            return False

        if not parent_item:
            return False

        result_item._old_text = result_item.text()
        parent_item.appendRow([result_item, QStandardItem()])  # for result time
        self.result_added.emit(result_item)

        return True

    def remove_grid(self, item: ThreeDiGridItem) -> bool:
        """Removes a grid (and children) from the model, possibly emits results_removed and emits grid_removed"""
        return self._clear_recursive(item)

    def remove_result(self, item: ThreeDiResultItem) -> bool:
        """Removes a result from the model, emits result_removed"""
        grid_item = item.parent()
        assert isinstance(grid_item, ThreeDiGridItem)

        item.setCheckState(Qt.CheckState.Unchecked)
        self.result_removed.emit(item)
        grid_item.removeRow(item.row())  # QStandardItem.removeRow does not return bool
        return True

    @pyqtSlot(QModelIndex)
    def remove_index(self, index: QModelIndex) -> bool:
        """Removes a result from the model, emits result_removed"""
        item = self.itemFromIndex(index)
        if isinstance(item, ThreeDiGridItem):
            return self.remove_grid(item)
        if isinstance(item, ThreeDiResultItem):
            return self.remove_result(item)

    def get_grid(self, grid_id: str) -> ThreeDiGridItem:
        """Returns the grid with this id, or None when not exists

            Not fully optimal, retrieves a list with all grids (via get_grids())
            and searches through that list.
        """
        for grid in self.get_grids():
            if grid.id == grid_id:
                return grid

        return None

    def get_result(self, result_id: str) -> ThreeDiResultItem:
        """Returns the result with this id, or None when not exists

            Not fully optimal, retrieves a list with all results
            and searches through that list.
        """
        for result in self.get_results(checked_only=False):
            if result.id == result_id:
                return result

        return None

    def get_grids(self) -> List[ThreeDiGridItem]:
        """Returns the list of grids"""
        def _get_grids(
            results: List[ThreeDiGridItem],
            item: QStandardItemModel
        ):
            if isinstance(item, ThreeDiGridItem):
                results.append(item)

            if item.hasChildren():
                for i in range(item.rowCount()):
                    _get_grids(results, item.child(i))
            return results

        results = []
        _get_grids(results, self.invisibleRootItem())
        return results

    def get_results_from_item(self, item: QStandardItem, checked_only: bool, results: List[ThreeDiResultItem]) -> None:
        """Returns the list of results of a provided item"""
        if isinstance(item, ThreeDiResultItem):
            if checked_only:
                if item.checkState() == Qt.CheckState.Checked:
                    results.append(item)
            else:
                results.append(item)

        if item.hasChildren():
            for i in range(item.rowCount()):
                self.get_results_from_item(item.child(i), checked_only, results)

    def get_results(self, checked_only: bool) -> List[ThreeDiResultItem]:
        """Returns the list of all results (traversal)"""
        results = []
        self.get_results_from_item(self.invisibleRootItem(), checked_only, results)
        return results

    def get_result_field_names(self, layer_id):
        names = {
            f_name
            for result_item in self.get_results(checked_only=False)
            for l_id, f_names in result_item._result_field_names.items()
            for f_name in f_names
            if l_id == layer_id
        }
        return names

    def number_of_grids(self) -> int:
        """Return the number of grid items by doing a full traversal."""
        return self._number_of_type(self.invisibleRootItem(), ThreeDiGridItem)

    def number_of_results(self) -> int:
        """Return the number of result items by doing a full traversal."""
        return self._number_of_type(self.invisibleRootItem(), ThreeDiResultItem)

    def _number_of_type(self, item, type) -> int:
        count = 0
        if isinstance(item, type):
            count += 1

        for i in range(item.rowCount()):
            count += self._number_of_type(item.child(i), type)
        return count

    @pyqtSlot()
    def clear(self) -> None:
        """Removes all items from the model.

        Traverses through the three top-down post-order, emits grid_removed and result_removed
        for each subsequent item.
        """
        # Traverse and emit if desired
        self._clear_recursive(self.invisibleRootItem())

    def _clear_recursive(self, item: QStandardItemModel) -> bool:
        """Traverses through the subthree top-down post-order, emits grid_removed and
        result_removed for each subsequent item. Because of post-order traversal, results are
        removed before grids.

        https://en.wikipedia.org/wiki/Tree_traversal#Arbitrary_trees
        """
        # Traverse into the children
        while item.hasChildren():
            self._clear_recursive(item.child(0))

        # Visit the node
        if isinstance(item, ThreeDiGridItem):
            self.grid_removed.emit(item)
            return self.removeRow(self.indexFromItem(item).row())  # Remove the actual grid
        elif isinstance(item, ThreeDiResultItem):
            return self.remove_result(item)  # Emits

    def contains(self, path: Path, ignore_suffix: bool = False) -> bool:
        """Return if any item has a path attribute equal to path."""
        def _contains(item, path: Path, ignore_suffix: bool):
            if hasattr(item, "path"):
                p1, p2 = item.path, path
                if ignore_suffix:
                    p1, p2 = p1.with_suffix(""), p2.with_suffix("")
                if p1 == p2:
                    return True
            return any(_contains(
                item=item.child(i),
                path=path,
                ignore_suffix=ignore_suffix
            ) for i in range(item.rowCount()))

        return _contains(
            item=self.invisibleRootItem(),
            path=path,
            ignore_suffix=ignore_suffix,
        )

    # @pyqtSlot(QStandardItem)
    def _item_changed(self, item: QStandardItem):
        # Only signal changes in grid and result items
        if not isinstance(item, (ThreeDiGridItem, ThreeDiResultItem)):
            return

        # Distinguish changed and checked
        if item._old_text != item.text():
            item._old_text = item.text()
            if isinstance(item, ThreeDiResultItem):
                self.result_changed.emit(item)
                return
            self.grid_changed.emit(item)
            return

        if isinstance(item, ThreeDiGridItem):
            return

        # Item is a result item with a (possibly?) modified checkstate
        if item.checkState() == Qt.CheckState.Checked:
            # Note that we not allow multiple results to be checked,
            # first deselect the others in case an item is checked.
            for i in range(item.parent().rowCount()):
                other_item = item.parent().child(i)
                if other_item is item:
                    continue
                other_item.setCheckState(Qt.CheckState.Unchecked)
            self.result_checked.emit(item)
            return

        self.set_time_item(item)
        self.result_unchecked.emit(item)

    def set_time_item(self, result_item):
        result_index = self.indexFromItem(result_item)
        time_item = self.itemFromIndex(result_index.siblingAtColumn(1))

        timedelta = result_item._timedelta

        if timedelta is None:
            time_item.setText("")
            return

        time_item.setText('{}d {:02}:{:02}'.format(
            timedelta.days,
            timedelta.seconds // 3600,
            timedelta.seconds % 3600 // 60,
        ))
