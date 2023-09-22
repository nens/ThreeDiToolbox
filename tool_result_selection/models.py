from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtCore import Qt
from ThreeDiToolbox.models.base import BaseModel
from ThreeDiToolbox.models.base_fields import CheckboxField
from ThreeDiToolbox.models.base_fields import ValueField

import logging


logger = logging.getLogger(__name__)


def get_line_pattern(item_field):
    """Return (default) line pattern for plots from this datasource.

    Look at the already-used styles and try to pick an unused one.

    :param item_field:
    :return: QT line pattern
    """
    available_styles = [
        Qt.SolidLine,
        Qt.DashLine,
        Qt.DotLine,
        Qt.DashDotLine,
        Qt.DashDotDotLine,
    ]

    already_used_patterns = [item.pattern.value for item in item_field.row.model.rows]

    for style in available_styles:
        if style not in already_used_patterns:
            # Hurray, an unused style.
            return style
    # No unused styles. Use the solid line style as a default.
    return Qt.SolidLine


class ValueWithChangeSignal(object):
    """Value for use inside a BaseModel. A change emits a signal.

    It works like a python property. The whole ``__get__``, ``instance``,
    ``owner`` stuff is explained here:
    https://stackoverflow.com/a/18038707/27401

    The ``signal_setting_name`` has to do with the way project state is saved,
    see ``utils/qprojects.py``.

    """

    def __init__(self, signal_name, signal_setting_name, initial_value=None):
        """Initialize ourselves as a kind-of-python-property.

        ``signal_name`` is the name of a class attribute that should be a qtsignal.

        ``signal_setting_name`` is the string that gets emitted as the first
        argument of the signal. It functions as a key for the key/value state
        storage mechanism from ``utils.qprojects.py``.

        """
        self.signal_name = signal_name
        self.signal_setting_name = signal_setting_name
        self.value = initial_value

    def __get__(self, instance, owner):
        return self.value

    def __set__(self, instance, value):
        self.value = value
        getattr(instance, self.signal_name).emit(self.signal_setting_name, value)


class TimeseriesDatasourceModel(BaseModel):
    """Model for selecting threedi netcdf results.

    Used as ``self.ts_datasources`` throughout the entire plugin.

    Often, ``self.ts_datasources.rows[0]`` is used, as the first one is
    effectively treated as the selected datasource

    We're also used for storing the selected model schematisation as
    :py:attr:`model_spatialite_filepath`.

    """

    model_schematisation_change = pyqtSignal(str, str)
    results_change = pyqtSignal(str, list)

    def __init__(self):
        BaseModel.__init__(self)
        self.dataChanged.connect(self.on_change)
        self.rowsRemoved.connect(self.on_change)
        self.rowsInserted.connect(self.on_change)

    tool_name = "result_selection"
    #: model_spatialite_filepath is the currently selected 3di model db.
    model_spatialite_filepath = ValueWithChangeSignal(
        "model_schematisation_change", "model_schematisation"
    )
    # TODO: don't we want a similar one for the selected netcdf? Instead of doing [0]?

    class Fields(object):
        active = CheckboxField(
            show=True, default_value=True, column_width=20, column_name=""
        )
        name = ValueField(show=True, column_width=130, column_name="Name")
        file_path = ValueField(show=True, column_width=615, column_name="File")
        type = ValueField(show=False)
        pattern = ValueField(show=False, default_value=get_line_pattern)

    def reset(self):
        self.removeRows(0, self.rowCount())

    def on_change(self, start=None, stop=None, etc=None):
        # TODO: what are emitted aren't directories but datasource models?
        self.results_change.emit("result_directories", self.rows)


class DownloadableResultModel(BaseModel):
    """Model with 3di results that can be downloaded from lizard."""

    class Fields(object):
        name = ValueField(show=True, column_width=250, column_name="Name")
        size_mebibytes = ValueField(
            show=True, column_width=120, column_name="Size (MiB)"
        )
        url = ValueField(show=True, column_width=300, column_name="URL")
        results = ValueField(show=False)  # the scenario results
