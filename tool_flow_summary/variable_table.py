
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QAbstractItemView
from qgis.PyQt.QtWidgets import QHeaderView
from qgis.PyQt.QtWidgets import QTableWidget
from qgis.PyQt.QtWidgets import QTableWidgetItem
from typing import List
from typing import Tuple


class VariableTable(QTableWidget):
    def __init__(self, parent):
        super().__init__(0, 1, parent)
        self.setHorizontalHeaderLabels([""])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        self.verticalHeader().hide()
        self.setSortingEnabled(False)
        self.setSelectionMode(QAbstractItemView.NoSelection)

        # for proper aligning, we always need to reserve space for the scrollbar
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # The list of parameters shown in the summary, idx corresponding to row idx in the table
        self.param_names : List[str] = []

    def add_summary_results(self, result_text: str, group_data):
        header_item = QTableWidgetItem(result_text)
        self.insertColumn(self.columnCount())
        self.setHorizontalHeaderItem(self.columnCount()-1, header_item)

        for param in group_data:
            param_name, param_value = self._format_variable(param, group_data[param])

            # Check if we've added this parameter before, then use that row idx,
            # otherwise append to bottom of table
            try:
                param_index = self.param_names.index(param_name)
            except ValueError:
                param_index = len(self.param_names)
                self.param_names.append(param_name)
                # Add a new row and set the parameter name
                assert param_index == self.rowCount()
                self.insertRow(param_index)
                item = QTableWidgetItem(param_name)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignRight)
                self.setItem(param_index, 0, item)

            item = QTableWidgetItem(param_value)
            item.setTextAlignment(Qt.AlignRight)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.setItem(param_index, self.columnCount()-1, item)

        for idx in range(self.columnCount()):
            self.horizontalHeader().setSectionResizeMode(idx, QHeaderView.Stretch)

    def clean_results(self) -> None:
        self.clearContents()
        self.setColumnCount(1)
        self.setRowCount(0)
        self.setHorizontalHeaderLabels([""])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.param_names.clear()

    def remove_result(self, idx: int) -> None:
        self.removeColumn(idx)
        for idx in range(self.columnCount()):
            self.horizontalHeader().setSectionResizeMode(idx, QHeaderView.Stretch)

    def change_result(self, idx: int, text: str) -> None:
        self.setHorizontalHeaderItem(idx, QTableWidgetItem(text))

    def _format_variable(self, param_name: str, param_data: dict) -> Tuple[str, str]:

        param_name = param_name.replace("_", " ")
        if type(param_data) is dict:
            param_name = f'{param_name} [{param_data["units"]}]'
            param_data = param_data["value"]

        # numbers in 4 decimals, except when in scientific notation
        if isinstance(param_data, float):
            string_repr = str(param_data)
            if "e" in string_repr:
                param_data = string_repr
            else:
                param_data = "{:.4f}".format(param_data)
        else:
            param_data = str(param_data)

        param_name = param_name[0].capitalize() + param_name[1:]
        return param_name, param_data
