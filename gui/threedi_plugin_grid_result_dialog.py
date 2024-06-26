from functools import wraps
from pathlib import Path
import logging
import os

from threedi_results_analysis.utils.constants import TOOLBOX_QGIS_SETTINGS_GROUP
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot, QModelIndex, Qt, QSortFilterProxyModel
from qgis.PyQt.QtWidgets import QAbstractItemView
from qgis.core import QgsSettings
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem
from threedi_mi_utils import list_local_schematisations

logger = logging.getLogger(__name__)

FORM_CLASS, _ = uic.loadUiType(
    Path(__file__).parent / 'threedi_plugin_grid_result_dialog.ui',
)


def disable_dialog(func):
    """
    Calls func while disabling widget.
    """
    @wraps(func)
    def wrapper(obj, *args, **kwargs):
        obj.setEnabled(False)
        try:
            func(obj, *args, **kwargs)
        finally:
            obj.setEnabled(True)
    return wrapper


class ThreeDiPluginGridResultDialog(QtWidgets.QDialog, FORM_CLASS):
    grid_file_selected = pyqtSignal(str)
    result_grid_file_selected = pyqtSignal([str, str])

    def __init__(self, parent):
        super(ThreeDiPluginGridResultDialog, self).__init__(parent)
        self.setupUi(self)

        self.gridQgsFileWidget.fileChanged.connect(self._select_grid)
        self.gridQgsFileWidget.setDefaultRoot(ThreeDiPluginGridResultDialog._get_dir())
        self.gridQgsFileWidget.lineEdit().setEnabled(False)
        self.addGridPushButton.clicked.connect(self._add_grid)

        self.resultQgsFileWidget.fileChanged.connect(self._select_result)
        self.resultQgsFileWidget.setDefaultRoot(ThreeDiPluginGridResultDialog._get_dir())
        self.resultQgsFileWidget.lineEdit().setEnabled(False)
        self.addResultPushButton.clicked.connect(self._add_result)

        self.tabWidget.currentChanged.connect(self._tabChanged)
        self.model = QStandardItemModel()
        self.current_sort_order = Qt.AscendingOrder
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortRole(Qt.DisplayRole)
        self.tableView.setModel(self.proxy_model)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.header_labels = ["Schematisation", "Revision", "Simulation"]
        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.tableView.horizontalHeader().setSortIndicatorShown(True)
        self.tableView.horizontalHeader().setSectionsClickable(True)
        self.tableView.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        self.tableView.clicked.connect(self._item_selected)
        self.tableView.doubleClicked.connect(self._item_double_clicked)

        self.loadResultPushButton.clicked.connect(self._add_result_from_table)
        self.loadGridPushButton.clicked.connect(self._add_grid_from_table)

        self.refresh()

    @pyqtSlot(int)
    def on_header_clicked(self, logicalIndex):
        if self.proxy_model.sortColumn() == logicalIndex:
            self.current_sort_order = Qt.DescendingOrder if self.current_sort_order == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            self.current_sort_order = Qt.AscendingOrder
        self.proxy_model.sort(logicalIndex, self.current_sort_order)

    @pyqtSlot(str)
    def _select_grid(self, input_gridadmin_h5_or_gpkg: str) -> None:

        if not input_gridadmin_h5_or_gpkg:
            self.gridQgsFileWidget.setFilePath("")
            self.addGridPushButton.setEnabled(False)
            return

        ThreeDiPluginGridResultDialog._set_dir(input_gridadmin_h5_or_gpkg)
        self.gridQgsFileWidget.setDefaultRoot(ThreeDiPluginGridResultDialog._get_dir())
        self.resultQgsFileWidget.setDefaultRoot(ThreeDiPluginGridResultDialog._get_dir())

    @pyqtSlot(str)
    def _select_result(self, input_result_nc: str) -> None:
        if not input_result_nc:
            self.resultQgsFileWidget.setFilePath("")
            self.addResultPushButton.setEnabled(False)
            return

        ThreeDiPluginGridResultDialog._set_dir(input_result_nc)
        self.resultQgsFileWidget.setDefaultRoot(ThreeDiPluginGridResultDialog._get_dir())
        self.gridQgsFileWidget.setDefaultRoot(ThreeDiPluginGridResultDialog._get_dir())

    @pyqtSlot()
    @disable_dialog
    def _add_grid(self) -> None:
        if not self.gridQgsFileWidget.filePath():
            return

        self.grid_file_selected.emit(self.gridQgsFileWidget.filePath())

    @pyqtSlot()
    @disable_dialog
    def _add_result(self) -> None:
        if not self.resultQgsFileWidget.filePath():
            return

        grid_file = os.path.join(os.path.dirname(self.resultQgsFileWidget.filePath()), "gridadmin.h5")
        if not os.path.isfile(grid_file):
            grid_file = None

        self.result_grid_file_selected.emit(self.resultQgsFileWidget.filePath(), grid_file)

    @staticmethod
    def _get_dir() -> str:
        value = QgsSettings().value(TOOLBOX_QGIS_SETTINGS_GROUP + "/lastOpenDir")
        if value is None:
            return ""
        dir_path = Path(value)
        if not dir_path.is_dir():
            return ""
        return str(dir_path)

    @staticmethod
    def _set_dir(path: str) -> None:
        dir_path = Path(path).parent
        if dir_path.is_dir():
            QgsSettings().setValue(TOOLBOX_QGIS_SETTINGS_GROUP + "/lastOpenDir", str(dir_path))
        else:
            QgsSettings().remove(TOOLBOX_QGIS_SETTINGS_GROUP + "/lastOpenDir")

    @pyqtSlot(int)
    def _tabChanged(self, idx: int) -> None:
        if self.tabWidget.currentWidget() is self.threedi:
            self.refresh()

    def _retrieve_selected_result_folder(self, index: QModelIndex) -> str:
        result_item = self.model.item(index.row(), 2)
        result_dir = result_item.data()
        assert result_dir
        return result_dir

    def _retrieve_selected_grid_folder(self, index: QModelIndex) -> str:
        # In case this grid has a corresponding result, we'll use that folder
        result_item = self.model.item(index.row(), 2)
        if result_item:
            result_dir = result_item.data()
            assert result_dir
            return result_dir

        revision_item = self.model.item(index.row(), 1)
        grid_dir = revision_item.data()
        assert grid_dir
        return grid_dir

    @pyqtSlot()
    @disable_dialog
    def _add_grid_from_table(self) -> None:
        grid_file = os.path.join(self._retrieve_selected_grid_folder(self.tableView.currentIndex()), "gridadmin.h5")
        self.grid_file_selected.emit(grid_file)

    @pyqtSlot()
    @disable_dialog
    def _add_result_from_table(self) -> None:
        result_file = os.path.join(self._retrieve_selected_result_folder(self.tableView.currentIndex()), "results_3di.nc")
        grid_file = os.path.join(self._retrieve_selected_grid_folder(self.tableView.currentIndex()), "gridadmin.h5")

        # Also emit corresponding grid file, if existst
        if not os.path.isfile(grid_file):
            grid_file = None

        self.result_grid_file_selected.emit(result_file, grid_file)

    def _item_selected(self, index: QModelIndex):
        self.loadGridPushButton.setEnabled(True)
        # Only activate result button when revision contain results
        if self.model.item(index.row(), 2):
            self.loadResultPushButton.setEnabled(True)
        else:
            self.loadResultPushButton.setEnabled(False)

    @disable_dialog
    def _item_double_clicked(self, index: QModelIndex):
        # The selection contains a result
        if self.model.item(index.row(), 2):
            result_file = os.path.join(self._retrieve_selected_result_folder(index), "results_3di.nc")
            grid_file = os.path.join(self._retrieve_selected_grid_folder(index), "gridadmin.h5")

            # Also emit corresponding grid file
            self.result_grid_file_selected.emit(result_file, grid_file)
        else:
            grid_file = os.path.join(self._retrieve_selected_grid_folder(index), "gridadmin.h5")
            self.grid_file_selected.emit(grid_file)

    def refresh(self):
        # Repopulate the table
        self.model.clear()
        self.model.setHorizontalHeaderLabels(self.header_labels)
        threedi_working_dir = QgsSettings().value("threedi/working_dir", "")
        self.messageLabel.setText("")
        if not threedi_working_dir:
            self.messageLabel.setText("Please set your 3Di working directory in the 3Di Models & Simulations settings to be able to load computational grids and results from your 3Di working directory.")
            return

        rows = []
        local_schematisations = list_local_schematisations(threedi_working_dir, use_config_for_revisions=False)
        for schematisation_id, local_schematisation in local_schematisations.items():
            # Iterate over revisions
            for revision_number, local_revision in local_schematisation.revisions.items():
                num_of_results = len(local_revision.results_dirs)
                # Iterate over results
                for result_dir in local_revision.results_dirs:
                    schema_item = QStandardItem(local_schematisation.name)
                    schema_item.setEditable(False)
                    revision_item = QStandardItem(str(revision_number))
                    revision_item.setData(revision_number, Qt.DisplayRole)
                    revision_item.setEditable(False)
                    # We'll store the grid folder with the revision item for fast retrieval
                    revision_item.setData(local_revision.grid_dir)
                    result_item = QStandardItem(Path(result_dir).name)
                    result_item.setEditable(False)
                    # We'll store the result folder with the result_item for fast retrieval
                    result_item.setData(os.path.join(local_revision.results_dir, result_dir))
                    rows.append([schema_item, revision_item, result_item])

                # In case no results are present, but a gridadmin is present, we still add the grid, but without result item
                if num_of_results == 0 and os.path.exists(os.path.join(local_revision.grid_dir, "gridadmin.h5")):
                    schema_item = QStandardItem(local_schematisation.name)
                    schema_item.setEditable(False)
                    revision_item = QStandardItem(str(revision_number))
                    revision_item.setData(revision_number, Qt.DisplayRole)
                    revision_item.setEditable(False)
                    # We'll store the grid folder with the revision item for fast retrieval
                    revision_item.setData(local_revision.grid_dir)
                    rows.append([schema_item, revision_item])

        # Sort table rows by schematisation name and
        # then by revision number using the DisplayRole
        rows.sort(key=lambda x: (x[0].text(), x[1].data(Qt.DisplayRole)))
        for row in rows:
            self.model.appendRow(row)

        for i in range(len(self.header_labels)):
            self.tableView.resizeColumnToContents(i)
