# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import pyqtSlot
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QAbstractItemView
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtWidgets import QGridLayout
from qgis.PyQt.QtWidgets import QHBoxLayout
from qgis.PyQt.QtWidgets import QPushButton
from qgis.PyQt.QtWidgets import QSizePolicy
from qgis.PyQt.QtWidgets import QSpacerItem
from qgis.PyQt.QtWidgets import QTableWidget
from qgis.PyQt.QtWidgets import QTableWidgetItem
from qgis.PyQt.QtWidgets import QWidget
from threedi_results_analysis.threedi_plugin_model import ThreeDiGridItem
from threedi_results_analysis.threedi_plugin_model import ThreeDiResultItem
from threedi_results_analysis.threedi_plugin_tool import ThreeDiPluginTool
from typing import Callable
from typing import Dict
from typing import Tuple

import json
import logging
import os


logger = logging.getLogger(__name__)

INTERESTING_HEADERS = ["volume_balance", "volume_balance_of_0d_model"]


class FlowSummaryTool(ThreeDiPluginTool):

    def __init__(self, parent, iface, model):
        super().__init__(parent)
        self.iface = iface
        self.model = model
        self.setup_ui()

    def setup_ui(self) -> None:
        self.icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "icon_watershed.png")
        self.menu_text = "Flow summary tool"
        self.main_widget = QDialog(None)
        self.main_widget.setWindowTitle("Flow summary")
        self.main_widget.setLayout(QGridLayout())
        self.table_widget = QTableWidget(0, 1, self.main_widget)
        self.table_widget.setHorizontalHeaderLabels(["Variable"])
        self.table_widget.resizeColumnsToContents()
        self.table_widget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.verticalHeader().hide()
        self.table_widget.setSortingEnabled(False)
        self.table_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.main_widget.layout().addWidget(self.table_widget)
        self.main_widget.setEnabled(True)
        self.main_widget.hide()
        self.main_widget.setWindowFlags(Qt.WindowStaysOnTopHint)

        # Add ok button
        button_widget = QWidget(self.main_widget)
        button_widget.setLayout(QHBoxLayout(button_widget))
        spacer_item = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        button_widget.layout().addItem(spacer_item)
        ok_button = QPushButton("Ok", button_widget)
        button_widget.layout().addWidget(ok_button, alignment=Qt.AlignRight)
        self.main_widget.layout().addWidget(button_widget)
        ok_button.clicked.connect(self.main_widget.hide)

    def _format_variable(self, name: str) -> str:
        return name

    def show_summary_grid(self, item: ThreeDiGridItem) -> None:
        results = []
        self.model.get_results_from_item(item=item, checked_only=False, results=results)
        for result in results:
            self.show_summary_result(result)

    def show_summary_result(self, item: ThreeDiResultItem) -> None:
        self.table_widget.insertColumn(self.table_widget.columnCount())
        header_item = QTableWidgetItem(item.text())

        self.table_widget.setHorizontalHeaderItem(self.table_widget.columnCount()-1, header_item)
        self.result_count = 0

        # find and parse the result files
        flow_summary_path = item.path.parent / "flow_summary.json"
        if not flow_summary_path.exists():
            logger.warning(f"Flow summary file from Result {item.text()} cannot be found.")
            # TODO: make red, but unclear how to style individual items in header
            return

        # TODO: keep track of existing params

        # TODO: keep track of existing results

        # retrieve all the entries in this file
        with flow_summary_path.open() as file:
            data = json.load(file)

            row_count = 0
            for interesting_header in INTERESTING_HEADERS:
                if interesting_header in data:
                    for param in data[interesting_header]:
                        self.table_widget.insertRow(self.table_widget.rowCount())
                        self.table_widget.setItem(row_count, 0, QTableWidgetItem(f'{param} [{data[interesting_header][param]["units"]}]'))
                        self.table_widget.setItem(row_count, 1, QTableWidgetItem(str(data[interesting_header][param]["value"])))
                        row_count += 1

        self.table_widget.resizeColumnsToContents()
        self.result_count += 1

        self.main_widget.show()

    def get_custom_actions(self) -> Dict[QAction, Tuple[Callable[[ThreeDiGridItem], None], Callable[[ThreeDiResultItem], None]]]:
        return {QAction("Show flow summary"): (self.show_summary_grid, self.show_summary_result)}

    def on_unload(self) -> None:
        del self.main_widget
        self.main_widget = None

    @pyqtSlot(ThreeDiResultItem)
    def result_removed(self, result_item: ThreeDiResultItem):
        # Remove column if required
        pass

    @pyqtSlot(ThreeDiResultItem)
    def result_changed(self, result_item: ThreeDiResultItem):
        # Change column header if required
        pass

    def run(self) -> None:
        self.main_widget.show()
