from pathlib import Path
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtGui import QStandardItem, QStandardItemModel

import logging

logger = logging.getLogger(__name__)


class ThreeDiGridItem(QStandardItem):
    def __init__(self, path, text: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.path = Path(path)
        self.layer_group = None

        self.setSelectable(True)
        self.setEditable(True)
        self.setText(text)


class ThreeDiResultItem(QStandardItem):
    def __init__(self, path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.path = Path(path)
        self.setCheckable(True)
        self.setCheckState(2)


class ThreeDiPluginModel(QStandardItemModel):
    grid_item_added = pyqtSignal(ThreeDiGridItem)
    result_item_added = pyqtSignal(ThreeDiResultItem)
    result_item_checked = pyqtSignal(ThreeDiResultItem)
    result_item_unchecked = pyqtSignal(ThreeDiResultItem)
    result_item_selected = pyqtSignal(ThreeDiResultItem)
    result_item_deselected = pyqtSignal(ThreeDiResultItem)
    grid_item_selected = pyqtSignal(ThreeDiGridItem)
    grid_item_deselected = pyqtSignal(ThreeDiGridItem)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.itemChanged.connect(self.item_changed)

    def item_changed(self, item):
        if isinstance(item, ThreeDiResultItem):
            {
                2: self.result_item_checked, 0: self.result_item_unchecked,
            }[item.checkState()].emit(item)
        elif isinstance(item, ThreeDiGridItem):
            logger.info("Item data changed")

    def add_grid_file(self, input_gridadmin_h5_or_gpkg: str) -> bool:
        """Converts h5 grid file to gpkg and add the layers to the project"""
        parent_item = self.invisibleRootItem()
        path_h5_or_gpkg = Path(input_gridadmin_h5_or_gpkg)
        grid_item = ThreeDiGridItem(path_h5_or_gpkg, ThreeDiPluginModel._resolve_grid_item_text(path_h5_or_gpkg))
        parent_item.appendRow(grid_item)
        self.grid_item_added.emit(grid_item)

    def add_result_file(self, input_result_nc: str) -> bool:
        """Converts h5 grid file to gpkg and add the layers to the project"""
        # TODO add it under the right grid - inspect the paths?
        parent_item = self.invisibleRootItem().child(0)
        path_nc = Path(input_result_nc)
        result_item = ThreeDiResultItem(path_nc, path_nc.stem)
        parent_item.appendRow(result_item)
        self.result_item_added.emit(result_item)

    def select_item(self, index):
        item = self.itemFromIndex(index)
        if isinstance(item, ThreeDiGridItem):
            self.grid_item_selected.emit(item)
        elif isinstance(item, ThreeDiResultItem):
            self.result_item_selected.emit(item)

    def deselect_item(self, index):
        item = self.itemFromIndex(index)
        if isinstance(item, ThreeDiGridItem):
            self.grid_item_deselected.emit(item)
        elif isinstance(item, ThreeDiResultItem):
            self.result_item_selected.emit(item)

    @staticmethod
    def _resolve_grid_item_text(path: Path) -> str:
        """The text of the grid item depends on its containing file structure"""
        return path.parent.stem
