from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from threedi_results_analysis.models import base_fields

import mock


def test_row_field_value_set_value():
    row = mock.Mock()
    field = mock.Mock()
    row_field_value = base_fields.RowFieldValue(row, field, 42)
    # For coverage, test that setting a value to the current value doesn't
    # fire any signals.
    row_field_value._set_value(42)
    assert not row_field_value.row.model.dataChanged.emit.called


def test_row_field_value_qvalue1():
    row = mock.Mock()
    field = mock.Mock()
    row_field_value = base_fields.RowFieldValue(row, field, 42)
    # Not a specific special field, so we just return the value.
    assert row_field_value.qvalue == 42


def test_row_field_value_qvalue2():
    row = mock.Mock()
    field = mock.Mock()
    # For checkbox fields, we want the proper QT version of true/false.
    field.field_type = base_fields.CHECKBOX_FIELD
    row_field_value = base_fields.RowFieldValue(row, field, True)
    assert row_field_value.qvalue == Qt.Checked
    row_field_value = base_fields.RowFieldValue(row, field, False)
    assert row_field_value.qvalue == Qt.Unchecked


def test_row_field_value_qvalue3():
    row = mock.Mock()
    field = mock.Mock()
    # Color fields should return a qt color.
    field.field_type = base_fields.COLOR_FIELD
    row_field_value = base_fields.RowFieldValue(row, field, [42, 42, 42])
    assert isinstance(row_field_value.qvalue, QColor)


def test_row_field_value_qvalue4():
    row = mock.Mock()
    field = mock.Mock()
    field.field_type = base_fields.COLOR_FIELD
    # Special case: don't return a color if the value is None.
    row_field_value = base_fields.RowFieldValue(row, field, None)
    row_field_value._value = None  # Otherwise default_value() gives us a Mock :-)
    assert row_field_value.qvalue is None
