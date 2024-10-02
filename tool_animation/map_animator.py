from bisect import bisect_left
from enum import Enum
from functools import lru_cache
from qgis.core import NULL
from qgis.core import QgsProject
from qgis.PyQt.QtCore import pyqtSlot
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QDoubleValidator
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtGui import QIntValidator
from qgis.PyQt.QtWidgets import QCheckBox
from qgis.PyQt.QtWidgets import QComboBox
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtWidgets import QDialogButtonBox
from qgis.PyQt.QtWidgets import QGridLayout
from qgis.PyQt.QtWidgets import QGroupBox
from qgis.PyQt.QtWidgets import QHBoxLayout
from qgis.PyQt.QtWidgets import QLabel
from qgis.PyQt.QtWidgets import QLineEdit
from qgis.PyQt.QtWidgets import QPushButton
from qgis.PyQt.QtWidgets import QVBoxLayout
from qgis.PyQt.QtWidgets import QWidget
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtXml import QDomElement
from threedi_results_analysis import PLUGIN_DIR
from threedi_results_analysis.datasource.result_constants import AGGREGATION_OPTIONS
from threedi_results_analysis.datasource.result_constants import DISCHARGE
from threedi_results_analysis.datasource.result_constants import H_TYPES
from threedi_results_analysis.datasource.result_constants import NEGATIVE_POSSIBLE
from threedi_results_analysis.datasource.result_constants import Q_TYPES
from threedi_results_analysis.datasource.result_constants import WATERLEVEL
from threedi_results_analysis.datasource.threedi_results import ThreediResult
from threedi_results_analysis.threedi_plugin_model import ThreeDiGridItem
from threedi_results_analysis.threedi_plugin_model import ThreeDiResultItem
from threedi_results_analysis.utils.timing import timing
from threedi_results_analysis.utils.user_messages import pop_up_critical
from threedi_results_analysis.utils.user_messages import StatusProgressBar
from threedi_results_analysis.utils.utils import generate_parameter_config
from threedi_results_analysis.utils.utils import is_substance_variable
from threedi_results_analysis.utils.utils import pretty
from threedigrid.admin.constants import NO_DATA_VALUE
from typing import List

import copy
import logging
import math
import numpy as np
import threedi_results_analysis.tool_animation.animation_styler as styler


logger = logging.getLogger(__name__)


class MethodEnum(str, Enum):
    PRETTY = "Pretty Breaks"
    PERCENTILE = "Equal Count (Quantile)"


class MapAnimatorSettings(object):
    lower_cutoff_percentile: float = 2.0
    upper_cutoff_percentile: float = 98.0
    method: MethodEnum = MethodEnum.PRETTY
    nr_classes: int = 24  # Must be EVEN!

    def __str__(self):
        return f"{self.lower_cutoff_percentile} {self.upper_cutoff_percentile} {self.method.value} {self.nr_classes}"


class MapAnimatorSettingsdialog(QDialog):
    def __init__(self, parent, title: str, default_settings: MapAnimatorSettings):
        super().__init__(parent)
        self.setWindowTitle(f"Visualisation settings for {title}")

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        settings_group = QGroupBox(self)
        settings_group.setLayout(QGridLayout())

        # Set up GUI and populate with settings
        settings_group.layout().addWidget(QLabel("Lower cutoff percentile:"), 0, 0)
        self.lower_cutoff_percentile_lineedit = QLineEdit(str(default_settings.lower_cutoff_percentile), settings_group)
        lower_percentile_validator = QDoubleValidator(0.0, 100.0, 2, self.lower_cutoff_percentile_lineedit)
        lower_percentile_validator.setNotation(QDoubleValidator.StandardNotation)
        self.lower_cutoff_percentile_lineedit.setValidator(lower_percentile_validator)
        settings_group.layout().addWidget(self.lower_cutoff_percentile_lineedit, 0, 1)

        settings_group.layout().addWidget(QLabel("Upper cutoff percentile:"), 1, 0)
        self.upper_cutoff_percentile_lineedit = QLineEdit(str(default_settings.upper_cutoff_percentile), settings_group)
        upper_percentile_validator = QDoubleValidator(0.0, 100.0, 2, self.upper_cutoff_percentile_lineedit)
        upper_percentile_validator.setNotation(QDoubleValidator.StandardNotation)
        self.upper_cutoff_percentile_lineedit.setValidator(upper_percentile_validator)
        settings_group.layout().addWidget(self.upper_cutoff_percentile_lineedit, 1, 1)

        settings_group.layout().addWidget(QLabel("Method:"), 2, 0)
        self.method_combo = QComboBox(settings_group)
        self.method_combo.addItems([s.value for s in MethodEnum])
        for c in range(self.method_combo.count()):
            if default_settings.method.value == self.method_combo.itemText(c):
                self.method_combo.setCurrentIndex(c)
                break
        settings_group.layout().addWidget(self.method_combo, 2, 1)

        settings_group.layout().addWidget(QLabel("Preferred number of classes:"), 3, 0)
        self.nr_classes_lineedit = QLineEdit(str(default_settings.nr_classes), settings_group)
        self.nr_classes_lineedit.setValidator(QIntValidator(2, 42, self.nr_classes_lineedit))
        settings_group.layout().addWidget(self.nr_classes_lineedit, 3, 1)

        layout.addWidget(settings_group)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        layout.addWidget(buttonBox)

    def accept(self) -> None:
        # Check logic
        if int(self.nr_classes_lineedit.text()) % 2 != 0:
            pop_up_critical("Number of classes should be even.")
            return
        if int(self.nr_classes_lineedit.text()) <= 0 or int(self.nr_classes_lineedit.text()) > 42:
            pop_up_critical("Number of classes should be greater than 0 and less then 42.")
            return
        upper_cutoff_percentile = float(self.upper_cutoff_percentile_lineedit.text())
        lower_cutoff_percentile = float(self.lower_cutoff_percentile_lineedit.text())
        if upper_cutoff_percentile <= 0 or upper_cutoff_percentile >= 100:
            pop_up_critical("The upper cutoff percentile should be greater than 0 and less than 100.")
            return
        if lower_cutoff_percentile <= 0 or lower_cutoff_percentile >= 100:
            pop_up_critical("The lower cutoff percentile should be greater than 0 and less than 100.")
            return

        if upper_cutoff_percentile <= lower_cutoff_percentile:
            pop_up_critical("The upper cutoff percentile should be greater than the lower cutoff percentile.")
            return

        return super().accept()

    def get_settings(self) -> MapAnimatorSettings:
        result = MapAnimatorSettings()
        result.lower_cutoff_percentile = float(self.lower_cutoff_percentile_lineedit.text())
        result.upper_cutoff_percentile = float(self.upper_cutoff_percentile_lineedit.text())
        result.nr_classes = int(self.nr_classes_lineedit.text())
        result.method = MethodEnum(self.method_combo.currentText())
        return result


def get_layer_by_id(layer_id):
    return QgsProject.instance().mapLayer(layer_id)


def strip_agg_options(param: str) -> str:
    for opt in AGGREGATION_OPTIONS:
        if param.endswith("_" + opt):
            stripchars = 1 + len(opt)
            return param[:-stripchars]
    return param


@lru_cache(maxsize=None)
def threedi_result_legend_class_bounds(
    threedi_result: ThreediResult,
    groundwater: bool,
    variable: str,
    absolute: bool,
    lower_threshold: float,
    lower_cutoff_percentile: float,
    upper_cutoff_percentile: float,
    relative_to_t0: bool,
    nr_classes: int,
    simple=False,
    method: str = "Pretty Breaks",
) -> List[float]:
    """
    Calculate percentile values given variable in a 3Di results netcdf

    If variable is water level and relative_to_t0 = True,
    nodatavalues in the water level timeseries (i.e., dry nodes)
    will be replaced by the node's bottom level (z-coordinate)

    :param gr: GridH5ResultAdmin
    :param groundwater: calculate percentiles for groundwater (True) or anything but groundwater (False)
    :param variable: one of threedi_results_analysis.datasource.result_constants.SUBGRID_MAP_VARIABLES,
      except q_pump
    :param percentile: Percentile or sequence of class_bounds to compute, which must be between 0 and 100 inclusive.
    :param absolute: calculate percentiles on absolute values
    :param lower_threshold: ignore values below this threshold
    :param relative_to_t0: calculate percentiles on difference w/ initial values (applied before absolute)
    :param nodatavalue: ignore these values
    :param method: 'Pretty Breaks' or 'Equal Count (Quantile)'
    """

    class_bounds_empty = [0] * nr_classes
    class_bounds_percentiles = np.linspace(
        0, 100, nr_classes, dtype=int
    ).tolist()

    if groundwater and not threedi_result.result_admin.has_groundwater:
        return class_bounds_empty

    stripped_variable = strip_agg_options(variable)
    gr = threedi_result.get_gridadmin(variable)
    if is_substance_variable(variable):
        nodes_or_lines = gr.get_model_instance_by_field_name(variable)
    elif stripped_variable in Q_TYPES:
        if groundwater:
            nodes_or_lines = gr.lines.filter(kcu__in=[-150, 150])
        else:
            nodes_or_lines = gr.lines.filter(kcu__ne=-150).filter(kcu__ne=150)
    elif stripped_variable in H_TYPES:
        if groundwater:
            nodes_or_lines = gr.nodes.filter(node_type__in=[2, 6])
            if variable == WATERLEVEL.name:
                bottom_level = gr.cells.filter(node_type__in=[2, 6]).dmax
        else:
            nodes_or_lines = gr.nodes.filter(node_type__ne=2).filter(node_type__ne=6)
            if variable == WATERLEVEL.name:
                bottom_level = (
                    gr.cells.filter(node_type__ne=2)
                    .filter(node_type__ne=6)
                    .dmax
                )
    else:
        raise ValueError(f"unknown variable: {variable}")

    if simple:
        # only read the first and the last steps
        timestamps = threedi_result.get_timestamps(variable)
        indexes = slice(None, None, timestamps.size - 1)
        ts = nodes_or_lines.timeseries(indexes=indexes)
    else:
        ts = nodes_or_lines.timeseries(indexes=slice(None))

    if is_substance_variable(variable):
        values = ts.get_filtered_field_value("concentration")
    else:
        values = ts.get_filtered_field_value(variable)
    values[values == NO_DATA_VALUE] = np.nan

    # TODO: this should move inside "if relative to t0" once the styling supports "all other values"
    if variable == WATERLEVEL.name:
        # replace NaN with dmax a.k.a. bottom_level
        mask = np.isnan(values)
        values[mask] = np.broadcast_to(bottom_level, values.shape)[mask]

    if relative_to_t0:
        values -= values[0]

    if absolute:
        np.abs(values, out=values)

    values_above_threshold = values[values > lower_threshold]
    if np.isnan(values_above_threshold).all():
        return class_bounds_empty

    if lower_cutoff_percentile is not None:
        lower_cutoff_value = np.nanpercentile(values_above_threshold, lower_cutoff_percentile)
    elif upper_cutoff_percentile is not None:
        lower_cutoff_value = np.nanmin(values_above_threshold)

    if upper_cutoff_percentile is not None:
        upper_cutoff_value = np.nanpercentile(values_above_threshold, upper_cutoff_percentile)
    elif lower_cutoff_percentile is not None:
        upper_cutoff_value = np.nanmax(values_above_threshold)

    if upper_cutoff_percentile is not None or lower_cutoff_percentile is not None:
        values_cutoff = values_above_threshold[
            np.logical_and(
                values_above_threshold > lower_cutoff_value,
                values_above_threshold < upper_cutoff_value
            )
        ]

    if method == MethodEnum.PRETTY.value:
        try:
            result = pretty(values_cutoff, n=nr_classes)
        except ValueError:  # All values are the same
            result = class_bounds_empty
    elif method == MethodEnum.PERCENTILE.value:
        result = np.nanpercentile(
            values_cutoff, class_bounds_percentiles
        ).tolist()
    else:
        raise ValueError(f"'method' must be one of '{MethodEnum.PRETTY.value}', '{MethodEnum.PERCENTILE.value}'")

    real_min = 0 if absolute else np.nanmin(values).item()
    real_max = np.nanmax(values).item()
    if result[0] == real_min:
        if lower_threshold > real_min:
            result = np.insert(result, 1, lower_threshold)  # create a class for all values that can be regarded as 0
    else:
        result = np.insert(result, 0, real_min)
    if result[-1] != real_max:
        result = np.insert(result, len(result), real_max)

    return result


class MapAnimator(QGroupBox):
    """ """

    def __init__(self, parent, model):

        super().__init__("Visualization settings", parent)
        self.model = model
        self.node_parameters = None
        self.line_parameters = None

        self.node_parameter_setting = {}
        self.line_parameter_setting = {}

        self.current_datetime = None
        self.setup_ui(parent)

    @pyqtSlot(ThreeDiResultItem)
    def results_changed(self, item: ThreeDiResultItem):
        results = self.model.get_results(checked_only=True)
        active = bool(results)

        self.line_parameter_combo_box.setEnabled(active)
        self.node_parameter_combo_box.setEnabled(active)
        self.difference_checkbox.setEnabled(active)
        self.setEnabled(active)

        self._update_parameter_attributes()
        self._update_parameter_combo_boxes()
        self._update_parameter_settings()

        if not active:
            return

        self._restyle(lines=True, nodes=True)
        self.update_results()
        # iface.mapCanvas().refresh()

    def _update_parameter_settings(self):
        # Update cached parameter settings, remove param if no longer present
        param_settings_to_delete = []
        for param_key in self.node_parameter_setting:
            found = False
            for param in self.node_parameters.values():
                if param_key == f"{param['name']}-{param['unit']}-{param['parameters']}":
                    # This parameter is still present in results, so keep it.
                    found = True
                    break
            if not found:
                param_settings_to_delete.append(param_key)
        for param_key in param_settings_to_delete:
            logger.info(f"Removing settings for {param_key} as no longer present in all results")
            del self.node_parameter_setting[param_key]

        param_settings_to_delete.clear()
        for param_key in self.line_parameter_setting:
            found = False
            for param in self.line_parameters.values():
                if param_key == f"{param['name']}-{param['unit']}-{param['parameters']}":
                    found = True
                    break
            if not found:
                param_settings_to_delete.append(param_key)
        for param_key in param_settings_to_delete:
            logger.info(f"Removing settings for {param_key} as no longer present in all results")
            del self.line_parameter_setting[param_key]

    def write(self, doc: QDomDocument, xml_elem: QDomElement) -> bool:
        """Called when a QGS project is written, allowing each tool to presist
        additional info int the dedicated xml tools node."""

        animator_node = doc.createElement("map_animator")
        xml_elem.appendChild(animator_node)

        node_parameter_setting_element = doc.createElement("node_parameter_setting")
        for param_key, settings in self.node_parameter_setting.items():
            node_parameter_setting_element.appendChild(MapAnimator._setting_to_xml(doc, param_key, settings))

        line_parameter_setting_element = doc.createElement("line_parameter_setting")
        for param_key, settings in self.line_parameter_setting.items():
            line_parameter_setting_element.appendChild(MapAnimator._setting_to_xml(doc, param_key, settings))

        animator_node.appendChild(node_parameter_setting_element)
        animator_node.appendChild(line_parameter_setting_element)

        return True

    @staticmethod
    def _setting_to_xml(doc: QDomDocument, param_key: str, settings: MapAnimatorSettings) -> QDomElement:
        settings_element = doc.createElement("ParameterSetting")
        # We write the parameter key as attribute as it might contain spaces
        settings_element.setAttribute("parameter", param_key)
        lower_cutoff_percentile_element = doc.createElement("lower_cutoff_percentile")
        lower_cutoff_percentile_element.appendChild(doc.createTextNode(str(settings.lower_cutoff_percentile)))
        upper_cutoff_percentile_element = doc.createElement("upper_cutoff_percentile")
        upper_cutoff_percentile_element.appendChild(doc.createTextNode(str(settings.upper_cutoff_percentile)))
        method_element = doc.createElement("method")
        method_element.appendChild(doc.createTextNode(settings.method.value))
        nr_classes_element = doc.createElement("nr_classes")
        nr_classes_element.appendChild(doc.createTextNode(str(settings.nr_classes)))
        settings_element.appendChild(lower_cutoff_percentile_element)
        settings_element.appendChild(upper_cutoff_percentile_element)
        settings_element.appendChild(method_element)
        settings_element.appendChild(nr_classes_element)
        return settings_element

    def read(self, xml_elem: QDomElement) -> bool:
        animator_node = xml_elem.firstChildElement("map_animator")
        if not animator_node:
            logger.info("No animation settings in project")
            return True

        self.node_parameter_setting.clear()
        nodes_parameter_settings = animator_node.elementsByTagName("node_parameter_setting")
        assert nodes_parameter_settings.count() == 1
        nodes_parameter_settings = nodes_parameter_settings.item(0).toElement()
        param_nodes = nodes_parameter_settings.childNodes()
        for i in range(param_nodes.count()):
            param_node = param_nodes.at(i).toElement()
            param_key = param_node.attribute("parameter")
            self.node_parameter_setting[param_key] = MapAnimator._setting_from_xml(param_node)

        self.line_parameter_setting.clear()
        line_parameter_settings = animator_node.elementsByTagName("line_parameter_setting")
        assert line_parameter_settings.count() == 1
        line_parameter_settings = line_parameter_settings.item(0).toElement()
        param_lines = line_parameter_settings.childNodes()
        for i in range(param_lines.count()):
            param_line = param_lines.at(i).toElement()
            param_key = param_line.attribute("parameter")
            self.line_parameter_setting[param_key] = MapAnimator._setting_from_xml(param_line)

        return True

    @staticmethod
    def _setting_from_xml(param_node: QDomElement) -> MapAnimatorSettings:
        setting = MapAnimatorSettings()
        assert param_node.elementsByTagName("lower_cutoff_percentile").count() == 1
        setting.lower_cutoff_percentile = float(param_node.elementsByTagName("lower_cutoff_percentile").item(0).toElement().text())
        assert param_node.elementsByTagName("upper_cutoff_percentile").count() == 1
        setting.upper_cutoff_percentile = float(param_node.elementsByTagName("upper_cutoff_percentile").item(0).toElement().text())
        assert param_node.elementsByTagName("method").count() == 1
        setting.method = MethodEnum(param_node.elementsByTagName("method").item(0).toElement().text())
        assert param_node.elementsByTagName("nr_classes").count() == 1
        setting.nr_classes = int(param_node.elementsByTagName("nr_classes").item(0).toElement().text())
        return setting

    def _update_parameter_attributes(self):
        config = self._get_active_parameter_config()
        self.line_parameters = {r["name"]: r for r in config["q"]}
        self.node_parameters = {r["name"]: r for r in config["h"]}

    def _style_line_layers(self, result_item: ThreeDiResultItem, progress_bar):
        current_line_settings = self.line_parameter_setting.get(self.current_line_parameter_key, MapAnimatorSettings())
        threedi_result = result_item.threedi_result
        line_parameter_class_bounds, _ = self._get_class_bounds_line(
            threedi_result, self.current_line_parameter["parameters"], current_line_settings
        )
        grid_item = result_item.parent()
        assert isinstance(grid_item, ThreeDiGridItem)
        layer_id = grid_item.layer_ids["flowline"]
        virtual_field_name = result_item._result_field_names[layer_id][0]
        postfix = virtual_field_name[6:]  # remove "result" prefix
        layer = get_layer_by_id(layer_id)
        styler.style_animation_flowline_current(
            layer,
            line_parameter_class_bounds,
            self.current_line_parameter["parameters"],
            postfix,
        )
        progress_bar.increase_progress()

    def _style_node_layers(self, result_item: ThreeDiResultItem, progress_bar):
        """ Compute class bounds and apply style to node and cell layers. """
        current_node_settings = self.node_parameter_setting.get(self.current_node_parameter_key, MapAnimatorSettings())
        threedi_result = result_item.threedi_result
        node_parameter_class_bounds, _ = self._get_class_bounds_node(
            threedi_result, self.current_node_parameter["parameters"], current_node_settings
        )

        # Adjust the styling of the grid layer based on the bounds and result field name
        grid_item = result_item.parent()
        assert isinstance(grid_item, ThreeDiGridItem)

        layer_id = grid_item.layer_ids["node"]
        layer = get_layer_by_id(layer_id)
        virtual_field_name = result_item._result_field_names[layer_id][0]
        postfix = virtual_field_name[6:]  # remove "result" prefix
        if self.difference_checkbox.isChecked():
            styler.style_animation_node_difference(
                layer,
                node_parameter_class_bounds,
                self.current_node_parameter["parameters"],
                False,
                current_node_settings.nr_of_classes,
                postfix,
            )
        else:
            styler.style_animation_node_current(
                layer,
                node_parameter_class_bounds,
                self.current_node_parameter["parameters"],
                False,
                postfix,
            )
        progress_bar.increase_progress()

        # Pure 1D models do not have cells
        if "cell" in grid_item.layer_ids:
            logger.info("Styling cell layer")
            layer_id = grid_item.layer_ids["cell"]
            layer = get_layer_by_id(layer_id)
            virtual_field_name = result_item._result_field_names[layer_id][0]
            postfix = virtual_field_name[6:]  # remove "result" prefix
            if self.difference_checkbox.isChecked():
                styler.style_animation_node_difference(
                    layer,
                    node_parameter_class_bounds,
                    self.current_node_parameter["parameters"],
                    True,
                    current_node_settings.nr_of_classes,
                    postfix,
                )
            else:
                styler.style_animation_node_current(
                    layer,
                    node_parameter_class_bounds,
                    self.current_node_parameter["parameters"],
                    True,
                    postfix,
                )
        progress_bar.increase_progress()

    @property
    def current_line_parameter(self):
        return self.line_parameters[self.line_parameter_combo_box.currentText()]

    @property
    def current_node_parameter(self):
        return self.node_parameters[self.node_parameter_combo_box.currentText()]

    @property
    def current_node_parameter_key(self):
        return f"{self.current_node_parameter['name']}-{self.current_node_parameter['unit']}-{self.current_node_parameter['parameters']}"

    @property
    def current_line_parameter_key(self):
        return f"{self.current_line_parameter['name']}-{self.current_line_parameter['unit']}-{self.current_line_parameter['parameters']}"

    def _restyle(self, lines, nodes):
        result_items = self.model.get_results(checked_only=True)
        total = (int(lines) + 2 * int(nodes)) * len(result_items)
        progress_bar = StatusProgressBar(total - 1, "Styling layers")

        for result_item in result_items:
            if lines:
                self._style_line_layers(result_item, progress_bar)
            if nodes:
                self._style_node_layers(result_item, progress_bar)
        del progress_bar

    def _restyle_and_update_lines(self):
        """To be used when line parameter changes."""
        self._restyle(lines=True, nodes=False)
        self.update_results()

    def _restyle_and_update_nodes(self):
        """To be used when node parameter or relative checkbox changes."""
        self._restyle(lines=False, nodes=True)
        self.update_results()

    def _get_class_bounds_node(self, threedi_result, node_variable, settings: MapAnimatorSettings):
        base_nc_name = strip_agg_options(node_variable)
        if (
            base_nc_name in NEGATIVE_POSSIBLE and NEGATIVE_POSSIBLE[base_nc_name]
            or self.difference_checkbox.isChecked()
        ):
            lower_threshold = float("-Inf")
        else:
            lower_threshold = styler.DEFAULT_LOWER_THRESHOLD

        kwargs = dict(
            threedi_result=threedi_result,
            variable=node_variable,
            absolute=False,
            lower_threshold=lower_threshold,
            lower_cutoff_percentile=settings.lower_cutoff_percentile,
            upper_cutoff_percentile=settings.upper_cutoff_percentile,
            relative_to_t0=self.difference_checkbox.isChecked(),
            nr_classes=settings.nr_classes,
            method=settings.method,
        )
        with timing('percentiles1'):
            surfacewater_bounds = threedi_result_legend_class_bounds(
                groundwater=False, **kwargs,
            )
        with timing('percentiles2'):
            groundwater_bounds = threedi_result_legend_class_bounds(
                groundwater=True, **kwargs,
            )
        return surfacewater_bounds, groundwater_bounds

    def _get_class_bounds_line(self, threedi_result, line_variable, settings: MapAnimatorSettings):
        kwargs = dict(
            threedi_result=threedi_result,
            variable=line_variable,
            absolute=True,
            lower_threshold=styler.DEFAULT_LOWER_THRESHOLD,
            lower_cutoff_percentile=settings.lower_cutoff_percentile,
            upper_cutoff_percentile=settings.upper_cutoff_percentile,
            relative_to_t0=self.difference_checkbox.isChecked(),
            nr_classes=settings.nr_classes,
            method=settings.method,
        )
        with timing('percentiles3'):
            surfacewater_bounds = threedi_result_legend_class_bounds(
                groundwater=False, **kwargs,
            )
        with timing('percentiles4'):
            groundwater_bounds = threedi_result_legend_class_bounds(
                groundwater=True, **kwargs,
            )
        return surfacewater_bounds, groundwater_bounds

    def _update_parameter_combo_boxes(self):
        """
        Fills parameter and combo boxes based on selected result
        """
        self._update_parameter_attributes()

        Q_CUM = 'q_cum'
        default_short_names = {WATERLEVEL.name, Q_CUM}
        if Q_CUM not in (v['parameters'] for v in self.line_parameters.values()):
            default_short_names.add(DISCHARGE.name)

        for combo_box, parameters in (
            (self.line_parameter_combo_box, self.line_parameters),
            (self.node_parameter_combo_box, self.node_parameters),
        ):
            current_long_name = combo_box.currentText()
            combo_box.clear()
            if parameters:
                long_names = sorted(parameters)
                combo_box.addItems(long_names)
                try:
                    # keep last choice if possible
                    new_index = long_names.index(current_long_name)
                except ValueError:
                    # activate a default item if possible
                    for index, long_name in enumerate(long_names):
                        short_name = parameters[long_name]["parameters"]
                        if short_name in default_short_names:
                            new_index = index
                            break
                    else:  # no break, activate the first item
                        new_index = 0
                combo_box.setCurrentIndex(new_index)

    def _get_active_parameter_config(self):
        """
        Generates a parameter dict based on selected results.
        """
        q_vars = []
        h_vars = []

        for result in self.model.get_results(checked_only=True):
            threedi_result = result.threedi_result
            available_subgrid_vars = threedi_result.available_subgrid_map_vars

            # Make a deepcopy because we don't want to change the cached variables
            # in threedi_result.available_subgrid_map_vars
            available_subgrid_vars = copy.deepcopy(available_subgrid_vars)
            # 'q_pump' is a special case, which is currently not supported in the
            # animation tool.
            if "q_pump" in available_subgrid_vars:
                available_subgrid_vars.remove("q_pump")
            agg_vars = threedi_result.available_aggregation_vars[:]  # a copy
            available_wq_vars = threedi_result.available_water_quality_vars[:]  # a copy

            parameter_config = generate_parameter_config(
                available_subgrid_vars, agg_vars=agg_vars, wq_vars=available_wq_vars
            )

            def _intersection(a: List, b: List):
                if not a:
                    return b

                return [x for x in a if x in b]

            q_vars = _intersection(q_vars, parameter_config["q"])
            h_vars = _intersection(h_vars, parameter_config["h"])

        config = {"q": q_vars, "h": h_vars}
        return config

    @pyqtSlot()
    def update_results(self):
        if not self.isEnabled():
            return
        for result_item in self.model.get_results(checked_only=True):
            self._update_result_item_results(result_item)

    @lru_cache(maxsize=None)
    def _get_feature_ids(self, layer):
        return np.array([f.id() for f in layer.getFeatures()], dtype="i8")

    def _update_result_item_results(self, result_item):
        """Fill initial value and result fields of the animation layers, based
        on currently set animation datetime and parameters."""
        logger.info(f"Render {result_item.text()} at {result_item._timedelta}")
        grid_item = result_item.parent()

        layers_to_update = [
            (
                get_layer_by_id(grid_item.layer_ids["flowline"]),
                self.current_line_parameter,
            ),
            (
                get_layer_by_id(grid_item.layer_ids["node"]),
                self.current_node_parameter,
            ),
        ]

        # Pure 1D models do not have a cells
        if "cell" in grid_item.layer_ids:
            layers_to_update.append(
                (
                    get_layer_by_id(grid_item.layer_ids["cell"]),
                    self.current_node_parameter,
                ))

        # add item with relative time to model
        threedi_result = result_item.threedi_result

        for layer, parameter_config in layers_to_update:

            layer_id = layer.id()
            provider = layer.dataProvider()
            parameter = parameter_config["parameters"]
            parameter_long_name = parameter_config["name"]
            parameter_units = parameter_config["unit"]

            # determine timestep number for current parameter
            current_seconds = result_item._timedelta.total_seconds()
            parameter_timestamps = threedi_result.get_timestamps(parameter)
            timestep_nr = bisect_left(parameter_timestamps, current_seconds)
            timestep_nr = min(timestep_nr, parameter_timestamps.size - 1)

            # get the data
            ids = self._get_feature_ids(layer)
            values_t0 = threedi_result.get_values_by_timestep_nr(
                variable=parameter, timestamp_idx=0, node_ids=ids,
            )
            values_ti = threedi_result.get_values_by_timestep_nr(
                variable=parameter, timestamp_idx=timestep_nr, node_ids=ids,
            )

            # theedigrid may have returned masked arrays in the past
            if isinstance(values_t0, np.ma.MaskedArray):
                values_t0 = values_t0.filled(np.NaN)
            if isinstance(values_ti, np.ma.MaskedArray):
                values_ti = values_ti.filled(np.NaN)

            if parameter == WATERLEVEL.name:
                # dry cells have a NO_DATA_VALUE water level
                values_t0[values_t0 == NO_DATA_VALUE] = np.NaN
                values_ti[values_ti == NO_DATA_VALUE] = np.NaN

            # determine which fields to update
            ti_field_index, t0_field_index = (
                layer.fields().indexOf(n)
                for n in result_item._result_field_names[layer_id]
            )
            assert ti_field_index != -1
            assert t0_field_index != -1

            # update layer
            update_dict = {
                k: {
                    t0_field_index: NULL if math.isnan(v0) else v0,
                    ti_field_index: NULL if math.isnan(vi) else vi,
                } for k, v0, vi in zip(
                    ids.tolist(),
                    values_t0.tolist(),
                    values_ti.tolist(),
                )
            }
            provider.changeAttributeValues(update_dict)

            if (
                self.difference_checkbox.isChecked()
                and parameter_config == self.current_node_parameter
            ):
                layer_name_postfix = "relative to t0"
            else:
                layer_name_postfix = "current timestep"
            layer_name = (
                f"{parameter_long_name} [{parameter_units}] ({layer_name_postfix})"
            )

            layer.setName(layer_name)

            # Don't update invisible layers
            layer_tree_root = QgsProject.instance().layerTreeRoot()
            layer_tree_layer = layer_tree_root.findLayer(layer)
            if layer_tree_layer.isVisible():
                layer.triggerRepaint()

    def setup_ui(self, parent_widget: QWidget):
        parent_widget.layout().addWidget(self)

        self.HLayout = QHBoxLayout(self)
        self.setLayout(self.HLayout)

        line_group = QGroupBox("Flowline variable", self)
        line_group.setLayout(QGridLayout())

        self.line_parameter_combo_box = QComboBox(line_group)
        self.line_parameter_combo_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.line_parameter_combo_box.setToolTip("Choose flowline variable to display")
        line_group.layout().addWidget(self.line_parameter_combo_box, 0, 0, 1, 2, Qt.AlignTop)
        equalizer_icon = QIcon(str(PLUGIN_DIR / "icons" / "sliders.svg"))

        setting_button_line = QPushButton(equalizer_icon, "", line_group)
        setting_button_line.setFixedSize(QSize(26, 26))
        setting_button_line.clicked.connect(self.show_line_settings)
        line_group.layout().addWidget(setting_button_line, 1, 1)

        self.HLayout.addWidget(line_group)

        node_group = QGroupBox("Node variable", self)
        node_group.setLayout(QGridLayout())
        self.node_parameter_combo_box = QComboBox(node_group)
        self.node_parameter_combo_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.node_parameter_combo_box.setToolTip("Choose node variable to display")
        node_group.layout().addWidget(self.node_parameter_combo_box, 0, 0, 1, 2)

        self.difference_checkbox = QCheckBox("Relative", self)
        self.difference_checkbox.setToolTip(
            "Display difference relative to simulation start (nodes only)"
        )

        node_group.layout().addWidget(self.difference_checkbox, 1, 0)

        setting_button_node = QPushButton(equalizer_icon, "", line_group)
        setting_button_node.setFixedSize(QSize(26, 26))
        setting_button_node.clicked.connect(self.show_node_settings)
        node_group.layout().addWidget(setting_button_node, 1, 1)

        self.HLayout.addWidget(node_group)

        self.line_parameter_combo_box.activated.connect(self._restyle_and_update_lines)
        self.node_parameter_combo_box.activated.connect(self._restyle_and_update_nodes)
        self.difference_checkbox.stateChanged.connect(self._restyle_and_update_nodes)

        self.setEnabled(False)

    @pyqtSlot(bool)
    def show_node_settings(self, _: bool):
        current_node_settings = MapAnimatorSettings()
        if self.current_node_parameter_key in self.node_parameter_setting:
            current_node_settings = self.node_parameter_setting[self.current_node_parameter_key]

        dialog = MapAnimatorSettingsdialog(self, self.current_node_parameter['name'], current_node_settings)
        if dialog.exec():
            self.node_parameter_setting[self.current_node_parameter_key] = dialog.get_settings()
            self._restyle(lines=False, nodes=True)

    @pyqtSlot(bool)
    def show_line_settings(self, _: bool):
        current_line_settings = MapAnimatorSettings()
        if self.current_line_parameter_key in self.line_parameter_setting:
            current_line_settings = self.line_parameter_setting[self.current_line_parameter_key]

        dialog = MapAnimatorSettingsdialog(self, self.current_line_parameter['name'], current_line_settings)
        if dialog.exec():
            self.line_parameter_setting[self.current_line_parameter_key] = dialog.get_settings()
            self._restyle(lines=True, nodes=False)

    @staticmethod
    def index_to_duration(index, timestamps):
        """Return the duration between start of simulation and the selected time index

        Duration is returned as a tuple (days, hours, minutes) of the current active
        datasource, rounded down.

        Args:
            index (int): time index of the current selected datasource

        Returns:
            tuple days, hours, minutes

        """
        selected_timestamp = int(timestamps[index])
        days = selected_timestamp // 86400
        hours = (selected_timestamp // 3600) % 24
        minutes = (selected_timestamp // 60) % 60
        return days, hours, minutes
