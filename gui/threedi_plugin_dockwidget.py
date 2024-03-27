from pathlib import Path

from threedi_results_analysis.threedi_plugin_model import ThreeDiGridItem, ThreeDiResultItem
from threedi_results_analysis.utils.constants import TOOLBOX_QGIS_SETTINGS_GROUP
from threedi_results_analysis.gui.threedi_plugin_grid_result_dialog import ThreeDiPluginGridResultDialog
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.PyQt.QtCore import QModelIndex
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot
from qgis.PyQt.QtWidgets import QMenu
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsSettings
from qgis.PyQt.QtGui import QPixmap
from threedi_results_analysis import PLUGIN_DIR
import logging

logger = logging.getLogger(__name__)

FORM_CLASS, _ = uic.loadUiType(
    Path(__file__).parent / 'threedi_plugin_dockwidget_base.ui',
)


class ThreeDiPluginDockWidget(QDockWidget, FORM_CLASS):
    grid_file_selected = pyqtSignal(str)
    result_grid_file_selected = pyqtSignal([str, str])
    align_starts_checked = pyqtSignal(bool)

    grid_removal_selected = pyqtSignal(ThreeDiGridItem)
    result_removal_selected = pyqtSignal(ThreeDiResultItem)

    item_selected = pyqtSignal(QModelIndex)
    item_deselected = pyqtSignal(QModelIndex)

    def __init__(self, parent, iface):
        super(ThreeDiPluginDockWidget, self).__init__(parent)
        self.iface = iface

        self.first_show = True

        self.setupUi(self)
        self.pushButton_Add.clicked.connect(self._add_clicked)
        self.pushButton_RemoveItem.clicked.connect(self._remove_current_index_clicked)
        self.alignStartsCheckBox.stateChanged.connect(self._align_starts_clicked)

        # Set logo
        path_3di_logo = str(PLUGIN_DIR / "icons" / "icon.png")
        logo_3di = QPixmap(path_3di_logo)
        logo_3di = logo_3di.scaledToHeight(30)
        self.logo.setPixmap(logo_3di)

        # Replace any backslashes with slash to make QGIS happy when accessing a Windows network location.
        open_eye_logo = str(PLUGIN_DIR / "icons" / "open.png").replace("\\", "/")
        closed_eye_logo = str(PLUGIN_DIR / "icons" / "closed.png").replace("\\", "/")
        self.treeView.setStyleSheet(f"""QTreeView::indicator:unchecked {{image: url({closed_eye_logo});}}
                                    QTreeView::indicator:checked {{image: url({open_eye_logo});}}""")

        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.customMenuRequested)

        # We'll make the dialog persistent so we can set some signals
        self.dialog = ThreeDiPluginGridResultDialog(self)
        # Map signal to signal
        self.dialog.grid_file_selected.connect(self.grid_file_selected)
        self.dialog.result_grid_file_selected.connect(self.result_grid_file_selected)

    def customMenuRequested(self, pos):
        index = self.treeView.indexAt(pos)
        menu = QMenu(self)
        action_delete = QAction("Delete", self)

        action_delete.triggered.connect(lambda _, sel_index=index: self._remove_current_index_clicked(sel_index))
        menu.addAction(action_delete)
        menu.popup(self.treeView.viewport().mapToGlobal(pos))

    def set_model(self, model):

        tree_view = self.treeView
        tree_view.setModel(model)

        tree_view.selectionModel().selectionChanged.connect(self._selection_changed)
        tree_view.setColumnWidth(1, 65)

        header = tree_view.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.Fixed)

    def get_tools_widget(self):
        return self.toolWidget

    def _add_clicked(self):
        self.dialog.refresh()
        self.dialog.exec()

    def _remove_current_index_clicked(self, index=None):
        # note that index is the "current", not the "selected"
        if not index:
            index = self.treeView.selectionModel().currentIndex()
        if index is not None and index.isValid():
            item = self.treeView.model().itemFromIndex(index)
            if isinstance(item, ThreeDiGridItem):
                self.grid_removal_selected.emit(item)
            elif isinstance(item, ThreeDiResultItem):
                self.result_removal_selected.emit(item)
            else:
                raise RuntimeError("Unknown model item type")

    def _align_starts_clicked(self):
        self.align_starts_checked.emit(self.alignStartsCheckBox.isChecked())

    def _selection_changed(self, selected, deselected):
        deselected_indexes = deselected.indexes()
        if deselected_indexes:
            self.item_deselected.emit(deselected_indexes[0])
        selected_indexes = selected.indexes()
        if selected_indexes:
            self.item_selected.emit(selected_indexes[0])

    def _get_dir(self) -> str:
        value = QgsSettings().value(TOOLBOX_QGIS_SETTINGS_GROUP + "/lastOpenDir")
        if value is None:
            return ""
        dir_path = Path(value)
        if not dir_path.is_dir():
            return ""
        return str(dir_path)

    def _set_dir(self, path: str):
        dir_path = Path(path).parent
        if dir_path.is_dir():
            QgsSettings().setValue(TOOLBOX_QGIS_SETTINGS_GROUP + "/lastOpenDir", str(dir_path))
        else:
            QgsSettings().remove(TOOLBOX_QGIS_SETTINGS_GROUP + "/lastOpenDir")

    @pyqtSlot()
    def toggle_visible(self, *args, **kwargs):
        # Add the dockwidget, tabified with any other right area dock widgets
        if self.first_show:
            main_window = self.iface.mainWindow()
            right_area_dock_widgets = [
                d for d in main_window.findChildren(QDockWidget)
                if main_window.dockWidgetArea(d) == Qt.RightDockWidgetArea
                if d.isVisible()
            ] + [self]
            tabify_with = [right_area_dock_widgets[0].objectName()]
            for dock_widget in right_area_dock_widgets:
                self.iface.removeDockWidget(dock_widget)
                self.iface.addTabifiedDockWidget(
                    Qt.RightDockWidgetArea, dock_widget, tabify_with, True
                )
            self.first_show = False
        else:
            self.setVisible(not self.isVisible())

    @pyqtSlot(ThreeDiGridItem)
    def expand_grid(self, item: ThreeDiGridItem):
        index = self.treeView.model().indexFromItem(item)
        self.treeView.expand(index)
        selection_model = self.treeView.selectionModel()
        # Deselect other grids
        selection_model.clearSelection()

        selection_model.setCurrentIndex(index, selection_model.SelectCurrent)
