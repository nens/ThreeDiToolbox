from qgis.PyQt.QtCore import QAbstractTableModel
from qgis.PyQt.QtCore import QModelIndex
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtCore import Qt
from threedi_results_analysis.models.base_fields import CHECKBOX_FIELD
from threedi_results_analysis.models.base_fields import COLOR_FIELD
from threedi_results_analysis.models.base_fields import VALUE_FIELD

import inspect
import logging


logger = logging.getLogger(__name__)


class BaseModelRow(object):
    """Row inside a BaseModel.

    TODO: please, remove this horrible stuff. We have a feature freeze now, so
    I can only do some minimal renaming to clear it up a bit.
    [reinout, 2019-06-24]

    - Nothing subclasses this BaseModelRow.

    - BaseModelRow is dynamically generated with ``type()`` in BaseModel, but
      that makes no sense if there's just one class.

    - BaseModelRow calls BaseModel all the time. As a class, you should keep
      your fingers out of another class.

    """

    def __init__(self, model=None, **kwargs):

        self.model = model
        self._plots = {}
        # ^^^ TODO: this *might* be used in tool_water_balance and tool_graph,
        # though using such a private attribute is a bit weird.

        for field_name, field_class in self._fields:
            value = None
            if field_name in list(kwargs.keys()):
                value = kwargs[field_name]

            setattr(
                self, field_name, field_class.create_row_field(row=self, value=value)
            )

        # for function_name, function in self._functions:
        #    setattr(self, function_name, function)

    def get_row_nr(self):
        """
        get rownr of this item in the model
        :return: int: row number
        """

        return self.model.rows.index(self)

    def __getitem__(self, item):

        name = self.model.columns[item].name
        return getattr(self, name)

    def get_fields(self, show_only=False):

        if show_only:
            return [
                (name, column_field)
                for name, column_field in self._fields
                if column_field.show
            ]
        else:
            return self._fields


# TODO: nobody knows what BaseModel actually does. And whether we (still) need
# it. So.... one day, try to remove it.
class BaseModel(QAbstractTableModel):
    """Customized QAbstractTableModel with more pythonic way of field
    declaration and storage of settings and values in ModelItems, ItemFields
    and Fields"""

    _base_model_item_class = BaseModelRow
    class_name = "BaseModel"

    def __init__(self, ts_datasources=None, initial_data=[], parent=None):
        """
        initialisation.
        :param data: initial data. Array of item data.
            item format is dictionary with {
                '<field_id>': <field_value>,
                ...
            }
        :param: parent: some parent object used by Qt
        :return: -
        """
        self._rows = []

        super().__init__(parent)

        self.ts_datasources = ts_datasources

        # create item class
        self._fields = sorted(
            [
                (name, column_field)
                for name, column_field in inspect.getmembers(
                    self.Fields, lambda a: not (inspect.isroutine(a))
                )
                if not name.startswith("__") and not name.startswith("_")
            ],
            key=lambda item: item[1]._nr,  # Sort on column_field number
        )
        self.columns = [column_field for name, column_field in self._fields]

        self.item_class = type(
            self.class_name + "Row",
            (self._base_model_item_class, self.Fields),
            {"_fields": self._fields},
        )

        # initiate fields with fieldname, link to model and column_nr
        for i in range(0, len(self._fields)):
            name, field = self._fields[i]
            if hasattr(field, "contribute_to_class"):
                field.contribute_to_class(name, self, i)

        # process initial data
        self.insertRows(initial_data, signal=False)

    def _create_item(self, *args, **kwargs):
        """

        :param args: all (initial) values of the fields. See Fields class for
                     available fields
        :param kwargs: all (initial) values of the fields. See Fields class
                       for available fields
        :return: created item
        """
        return self.item_class(self, *args, **kwargs)

    def rowCount(self, index=QModelIndex):
        """
        get number of rows (nr of items). Required function for
        QAbstractTableModel
        :param index: QModelIndex
        :return:
        """
        return len(self._rows)

    def columnCount(self, index=QModelIndex):
        """
        get visible columns for display in table. Required function for
        QAbstractTableModel
        :param index: QModelIndex
        :return:
        """
        return len(self.columns)

    def index(self, row_nr, col_nr, parent=None):
        """
        Creates index for this model. Required function for QAbstractTableModel
        :param row_nr: int row number
        :param col_nr: int column number
        :param parent: parent of index
        :return: QModelIndex instance
        """
        return self.createIndex(row_nr, col_nr)

    def data(self, index, role=Qt.DisplayRole):
        """Qt function to get data from items for the visible columns"""

        if not index.isValid():
            return None

        row = self.rows[index.row()]

        if role == Qt.DisplayRole:
            if row[index.column()].field_type == VALUE_FIELD:
                return row[index.column()].value
        elif role == Qt.BackgroundRole:
            if row[index.column()].field_type == COLOR_FIELD:
                return row[index.column()].qvalue
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignVCenter
        elif role == Qt.CheckStateRole:
            if row[index.column()].field_type == CHECKBOX_FIELD:
                return row[index.column()].qvalue
            else:
                return None

    def headerData(self, col_nr, orientation=Qt.Horizontal, role=Qt.DisplayRole):
        """
        required Qt function for getting column information
        :param col_nr: column number
        :param orientation: Qt orientation of header Qt.Horizontal or Qt.Vertical
        :param role: Qt Role (DisplayRole, SizeHintRole, etc)
        :return: value of column, given the role
        """
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self.columns[col_nr].column_name
        else:
            # give grey balk at start of row a small dimension to select row
            if Qt.SizeHintRole:
                return QSize(10, 0)

    def setData(self, index, value, role):
        """
        required Qt function for setting data, including sending of signals
        :param index: QtModelIndex instance
        :param value: new value for ItemField
        :param role: Qt role (DisplayRole, CheckStateRole)
        :return: was setting value successful
        """

        # dataChanged.emit is done within the ItemField, triggered by setting
        # the value
        self._rows[index.row()][index.column()].value = value
        return True

    def flags(self, index):

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if self.columns[index.column()].field_type == CHECKBOX_FIELD:
            flags |= Qt.ItemIsUserCheckable | Qt.ItemIsEditable

        return flags

    def insertRows(self, data_items, signal=True):
        """
        required Qt function for adding rows, including sending signals

        :param data_items: list with values as dictionaries
        :param signal: send signal, False will prevent function from sending signal
        """
        if signal:
            self.beginInsertRows(
                QModelIndex(), self.rowCount(), self.rowCount() + len(data_items) - 1
            )

        for data_item in data_items:
            item = self._create_item(**data_item)
            self._rows.append(item)

        if signal:
            self.endInsertRows()

    def removeRows(self, row, count, parent=QModelIndex()):
        """
        required Qt function to remove rows from model
        :param row: first number to remove (count starts with row 1)
        :param count: number of rows to remove
        :param parent: some Qt parameter
        """
        # signal
        self.beginRemoveRows(parent, row, row + count - 1)

        for i in range(row + count - 1, row - 1, -1):
            del self._rows[i]

        # signal
        self.endRemoveRows()

    @property
    def rows(self):
        """
        :return: list of model items of model
        """
        return self._rows

    def set_column_sizes_on_view(self, table_view):
        """Helper function for applying the column sizes on a view.

        :table_view: table view instance that uses this model
        """
        if table_view.model is None:
            raise RuntimeError("No model set on view.")

        for col_nr in range(0, self.columnCount()):
            width = self.columns[col_nr].column_width
            if width:
                table_view.setColumnWidth(col_nr, width)
            if not self.columns[col_nr].show:
                table_view.setColumnHidden(col_nr, True)
