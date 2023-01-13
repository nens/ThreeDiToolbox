# TODO: calculate seperate class_bounds for groundwater

from qgis.core import NULL
from qgis.core import QgsProject
from qgis.core import QgsVectorLayer
from qgis.core import QgsWkbTypes
from qgis.utils import iface
from qgis.PyQt.QtCore import pyqtSlot
from qgis.PyQt.QtWidgets import QCheckBox
from qgis.PyQt.QtWidgets import QComboBox
from qgis.PyQt.QtWidgets import QFrame
from qgis.PyQt.QtWidgets import QLCDNumber
from qgis.PyQt.QtWidgets import QHBoxLayout
from qgis.PyQt.QtWidgets import QLabel
from qgis.PyQt.QtWidgets import QWidget
from qgis.PyQt.QtWidgets import QGroupBox
from threedigrid.admin.constants import NO_DATA_VALUE
from threedigrid.admin.gridresultadmin import GridH5ResultAdmin
from ThreeDiToolbox.datasource.result_constants import DISCHARGE
from ThreeDiToolbox.datasource.result_constants import H_TYPES
from ThreeDiToolbox.datasource.result_constants import NEGATIVE_POSSIBLE
from ThreeDiToolbox.datasource.result_constants import Q_TYPES
from ThreeDiToolbox.datasource.result_constants import WATERLEVEL
from ThreeDiToolbox.threedi_plugin_model import ThreeDiResultItem, ThreeDiGridItem
from ThreeDiToolbox.utils.utils import generate_parameter_config
from typing import Iterable
from typing import List
from typing import Union
from math import nan as NaN

import ThreeDiToolbox.tool_animation.animation_styler as styler
import copy
import logging
import numpy as np


logger = logging.getLogger(__name__)


class PercentileError(ValueError):
    """Raised when calculation of percentiles resulted in NaN"""

    pass


def copy_layer_into_memory_layer(source_layer, layer_name):
    source_provider = source_layer.dataProvider()

    uri = "{0}?crs=EPSG:{1}".format(
        QgsWkbTypes.displayString(source_provider.wkbType()).lstrip("WKB"),
        str(source_provider.crs().postgisSrid()),
    )

    dest_layer = QgsVectorLayer(uri, layer_name, "memory")
    dest_provider = dest_layer.dataProvider()

    dest_provider.addAttributes(source_provider.fields())
    dest_layer.updateFields()

    dest_provider.addFeatures([f for f in source_provider.getFeatures()])
    dest_layer.updateExtents()

    return dest_layer


def threedi_result_percentiles(
    gr: GridH5ResultAdmin,
    groundwater: bool,
    variable: str,
    percentile: Union[float, Iterable],
    absolute: bool,
    lower_threshold: float,
    relative_to_t0: bool,
    nodatavalue=NO_DATA_VALUE,
) -> Union[float, List[float]]:
    """
    Calculate given percentile given variable in a 3Di results netcdf

    If variable is water level and relative_to_t0 = True,
    nodatavalues in the water level timeseries (i.e., dry nodes)
    will be replaced by the node's bottom level (z-coordinate)


    :param gr: GridH5ResultAdmin
    :param groundwater: calculate percentiles for groundwater (True) or anything but groundwater (False)
    :param variable: one of ThreeDiToolbox.datasource.result_constants.SUBGRID_MAP_VARIABLES,
    with the exception of q_pump
    :param percentile: Percentile or sequence of class_bounds to compute, which must be between 0 and 100 inclusive.
    :param absolute: calculate percentiles on absolute values
    :param lower_threshold: ignore values below this threshold
    :param relative_to_t0: calculate percentiles on difference w/ initial values (applied before absolute)
    :param nodatavalue: ignore these values
    """
    if variable in Q_TYPES:
        if groundwater:
            nodes_or_lines = gr.lines.filter(kcu__in=[-150, 150])
        else:
            nodes_or_lines = gr.lines.filter(kcu__ne=-150).filter(kcu__ne=150)
    elif variable in H_TYPES:
        if groundwater:
            nodes_or_lines = gr.nodes.filter(node_type__in=[2, 6])
            if variable == WATERLEVEL.name and relative_to_t0:
                z_coordinates = gr.cells.filter(node_type__in=[2, 6]).z_coordinate
        else:
            nodes_or_lines = gr.nodes.filter(node_type__ne=2).filter(node_type__ne=6)
            if variable == WATERLEVEL.name and relative_to_t0:
                z_coordinates = (
                    gr.cells.filter(node_type__ne=2)
                    .filter(node_type__ne=6)
                    .z_coordinate
                )
    else:
        raise ValueError("unknown variable")

    last_timestamp = nodes_or_lines.timestamps[-1]
    ts = nodes_or_lines.timeseries(0, last_timestamp)
    values = getattr(ts, variable)
    values_t0 = values[0]
    if absolute:
        values = np.absolute(values)
        values_t0 = np.absolute(values_t0)
    values[values == nodatavalue] = np.nan
    values_t0[values_t0 == nodatavalue] = np.nan

    if relative_to_t0:
        if variable == WATERLEVEL.name:
            values_t0[np.isnan(values_t0)] = z_coordinates[np.isnan(values_t0)]
            z_coordinates_tiled = np.tile(z_coordinates, (values.shape[0], 1))
            values[np.isnan(values)] = z_coordinates_tiled[np.isnan(values)]
        values -= values_t0
    values_above_threshold = values[values > lower_threshold]
    if np.isnan(values_above_threshold).all():
        raise PercentileError
    np_percentiles = np.nanpercentile(values_above_threshold, percentile)
    if isinstance(np_percentiles, np.ndarray):
        result = list(map(float, np_percentiles))
    else:
        result = float(np_percentiles)
    return result


class MapAnimator(QGroupBox):
    """ """

    EMPTY_CLASS_BOUNDS = [0] * (styler.ANIMATION_LAYERS_NR_LEGEND_CLASSES + 1)

    def __init__(self, parent, model):

        super().__init__("Animation", parent)
        self.model = model
        self.node_parameters = {}
        self.line_parameters = {}
        self.current_node_parameter = None
        self.current_line_parameter = None
        self.line_parameter_class_bounds = self.EMPTY_CLASS_BOUNDS
        self.node_parameter_class_bounds = self.EMPTY_CLASS_BOUNDS
        self.groundwater_line_parameter_class_bounds = self.EMPTY_CLASS_BOUNDS
        self.groundwater_node_parameter_class_bounds = self.EMPTY_CLASS_BOUNDS

        # layers: store only layer id str to avoid keeping reference to deleted C++ object
        self._node_layer = None
        self._cell_layer = None
        self._line_layer_1d = None
        self._line_layer_2d = None
        self._line_layer_groundwater = None
        self._node_layer_groundwater = None
        self._cell_layer_groundwater = None
        self.setup_ui(parent)

    @pyqtSlot(ThreeDiResultItem)
    def results_changed(self, item: ThreeDiResultItem):
        self.setEnabled(self.model.number_of_results() > 0)

    @pyqtSlot(ThreeDiResultItem)
    def result_activated(self, item: ThreeDiResultItem):

        # Fill comboboxes based on result file
        self.fill_parameter_combobox_items()

        self.current_line_parameter = self.line_parameters[self.line_parameter_combo_box.currentText()]
        self.current_node_parameter = self.node_parameters[self.node_parameter_combo_box.currentText()]

        logger.info("Updating class bounds")
        self.update_class_bounds(update_nodes=True, update_lines=True)
        logger.info("Resetting time line")
        self._update_results(update_nodes=True, update_lines=True)

        # Set the right styling on the layers
        self.style_layers(style_nodes=True, style_lines=True)

        self.line_parameter_combo_box.setEnabled(True)
        self.node_parameter_combo_box.setEnabled(True)
        self.difference_checkbox.setEnabled(True)
        self.difference_label.setEnabled(True)
        self.lcd.setEnabled(True)

        iface.mapCanvas().refresh()

    def style_layers(self, style_lines: bool, style_nodes: bool):
        """
        Apply styling to surface water and groundwater flowline layers,
        based value distribution in the results and difference vs. current choice
        """

        # has_groundwater = (
        #    self.model.get_selected_results()[0].threedi_result.result_admin.has_groundwater  # TODO: ACTIVE
        # )

        # TODO: difference checkbox
        # if style_nodes:
        #     if self.difference_checkbox.isChecked():
        #         # nodes
        #         styler.style_animation_node_difference(
        #             self.node_layer,
        #             self.node_parameter_class_bounds,
        #             self.current_node_parameter["parameters"],
        #             cells=False,
        #         )

        # Adjust the styling of the grid layer based on the bounds and result field name
        item = self.model.get_selected_results()[0]
        grid_item = item.parent()
        assert isinstance(grid_item, ThreeDiGridItem)

        layer_id = grid_item.layer_ids["flowline"]
        virtual_field_name = item._result_field_names[layer_id][0]
        postfix = virtual_field_name[6:]  # remove "result" prefix

        layer = QgsProject.instance().mapLayer(layer_id)

        if style_lines:
            logger.info("Styling flowline layer")
            styler.style_animation_flowline_current(
                layer,
                self.line_parameter_class_bounds,
                self.current_line_parameter["parameters"],
                postfix,
            )

        if style_nodes:
            layer_id = grid_item.layer_ids["node"]
            layer = QgsProject.instance().mapLayer(layer_id)
            virtual_field_name = item._result_field_names[layer_id][0]
            postfix = virtual_field_name[6:]  # remove "result" prefix

            logger.info("Styling node layer")
            styler.style_animation_node_current(
                layer,
                self.node_parameter_class_bounds,
                self.current_node_parameter["parameters"],
                False,
                postfix,
            )

            layer_id = grid_item.layer_ids["cell"]
            layer = QgsProject.instance().mapLayer(layer_id)
            virtual_field_name = item._result_field_names[layer_id][0]
            postfix = virtual_field_name[6:]  # remove "result" prefix

            logger.info("Styling cell layer")
            styler.style_animation_node_current(
                layer,
                self.node_parameter_class_bounds,
                self.current_node_parameter["parameters"],
                True,
                postfix,
            )

    def on_line_parameter_change(self):
        pass

    def on_node_parameter_change(self):
        pass

    def on_difference_checkbox_state_change(self):
        self.update_class_bounds(update_nodes=True, update_lines=False)
        self._update_results(update_nodes=True, update_lines=False)
        self.style_layers(style_nodes=True, style_lines=False)

    def update_class_bounds(self, update_nodes: bool, update_lines: bool):
        gr = (
            self.model.get_selected_results()[0].threedi_result.result_admin  # TODO: ACTIVE
        )

        if update_nodes:
            if (
                NEGATIVE_POSSIBLE[self.current_node_parameter["parameters"]]
                or self.difference_checkbox.isChecked()
            ):
                lower_threshold = float("-Inf")
            else:
                lower_threshold = 0

            try:
                self.node_parameter_class_bounds = threedi_result_percentiles(
                    gr=gr,
                    groundwater=False,
                    variable=self.current_node_parameter["parameters"],
                    percentile=list(
                        range(0, 100, int(100 / styler.ANIMATION_LAYERS_NR_LEGEND_CLASSES))
                    )
                    + [100],
                    absolute=False,
                    lower_threshold=lower_threshold,
                    relative_to_t0=self.difference_checkbox.isChecked(),
                )
            except PercentileError:
                self.node_parameter_class_bounds = self.EMPTY_CLASS_BOUNDS

            if gr.has_groundwater:
                try:
                    self.groundwater_node_parameter_class_bounds = (
                        threedi_result_percentiles(
                            gr=gr,
                            groundwater=True,
                            variable=self.current_node_parameter["parameters"],
                            percentile=list(
                                range(
                                    0,
                                    100,
                                    int(100 / styler.ANIMATION_LAYERS_NR_LEGEND_CLASSES),
                                )
                            )
                            + [100],
                            absolute=False,
                            lower_threshold=lower_threshold,
                            relative_to_t0=self.difference_checkbox.isChecked(),
                        )
                    )
                except PercentileError:
                    self.groundwater_node_parameter_class_bounds = (
                        self.EMPTY_CLASS_BOUNDS
                    )

        if update_lines:
            try:
                self.line_parameter_class_bounds = threedi_result_percentiles(
                    gr=gr,
                    groundwater=False,
                    variable=self.current_line_parameter["parameters"],
                    percentile=list(
                        range(0, 100, int(100 / styler.ANIMATION_LAYERS_NR_LEGEND_CLASSES))
                    )
                    + [100],
                    absolute=True,
                    lower_threshold=float(0),
                    relative_to_t0=self.difference_checkbox.isChecked(),
                )
            except PercentileError:
                self.line_parameter_class_bounds = self.EMPTY_CLASS_BOUNDS

            if gr.has_groundwater:
                try:
                    self.groundwater_line_parameter_class_bounds = (
                        threedi_result_percentiles(
                            gr=gr,
                            groundwater=True,
                            variable=self.current_line_parameter["parameters"],
                            percentile=list(
                                range(
                                    0,
                                    100,
                                    int(100 / styler.ANIMATION_LAYERS_NR_LEGEND_CLASSES),
                                )
                            )
                            + [100],
                            absolute=True,
                            lower_threshold=float(0),
                            relative_to_t0=self.difference_checkbox.isChecked(),
                        )
                    )
                except PercentileError:
                    self.groundwater_line_parameter_class_bounds = (
                        self.EMPTY_CLASS_BOUNDS
                    )

    def fill_parameter_combobox_items(self):
        """
        Fills comboboxes with parameters based on selected result
        """
        parameter_config = self._get_active_parameter_config()

        for combo_box, parameters, pc in (
            (
                self.line_parameter_combo_box,
                self.line_parameters,
                parameter_config["q"],
            ),
            (
                self.node_parameter_combo_box,
                self.node_parameters,
                parameter_config["h"],
            ),
        ):

            combo_box.clear()

            parameters.update(dict([(p["name"], p) for p in pc]))
            for param_name, param in parameters.items():
                if param["parameters"] in (DISCHARGE.name, WATERLEVEL.name):
                    idx = 0
                else:
                    idx = 99999
                combo_box.insertItem(idx, param_name)
            combo_box.setCurrentIndex(0)

    def _get_active_parameter_config(self):
        """
        Generates a parameter dict based on results file.
        """
        active_result = self.model.get_selected_results()[0]  # TODO: ACTIVE

        if active_result is not None:
            # TODO: just taking the first datasource, not sure if correct:
            threedi_result = active_result.threedi_result
            available_subgrid_vars = threedi_result.available_subgrid_map_vars
            # Make a deepcopy because we don't want to change the cached variables
            # in threedi_result.available_subgrid_map_vars
            available_subgrid_vars = copy.deepcopy(available_subgrid_vars)
            # 'q_pump' is a special case, which is currently not supported in the
            # animation tool.
            if "q_pump" in available_subgrid_vars:
                available_subgrid_vars.remove("q_pump")

            parameter_config = generate_parameter_config(
                available_subgrid_vars, agg_vars=[]
            )
        else:
            parameter_config = {"q": {}, "h": {}}

        return parameter_config

    def _update_results(self, update_nodes: bool, update_lines: bool):
        self.update_results(0, update_nodes, update_lines)  # TODO: last timestep_nr should be stored

    def update_results(self, timestep_nr, update_nodes: bool, update_lines: bool):
        """Fill the initial_value and result fields of the animation layers, depending on active result parameter"""

        # messagebar_message("Timestep in MapAnimator", f"{timestep_nr}")

        if self.isEnabled():

            if not self.current_line_parameter or not self.current_node_parameter:
                return

            result = self.model.get_selected_results()[0]  # TODO: ACTIVE
            threedi_result = result.threedi_result

            # Update UI (LCD)
            days, hours, minutes = MapAnimator.index_to_duration(timestep_nr, threedi_result.get_timestamps())
            formatted_display = "{:d} {:02d}:{:02d}".format(days, hours, minutes)
            self.lcd.display(formatted_display)

            layers_to_update = []

            qgs_instance = QgsProject.instance()
            grid = result.parent()
            line, node, cell = (
                qgs_instance.mapLayer(grid.layer_ids[k])
                for k in ("flowline", "node", "cell")
            )
            layers_to_update.append((line, self.current_line_parameter))
            layers_to_update.append((node, self.current_node_parameter))
            layers_to_update.append((cell, self.current_node_parameter))

            # TODO relocate this
            ids_by_layer_attr = "_ids_by_layer"
            if not hasattr(self, ids_by_layer_attr):
                ids_by_layer = {}
                setattr(self, ids_by_layer_attr, ids_by_layer)
            else:
                ids_by_layer = getattr(self, ids_by_layer_attr)

            for layer, parameter_config in layers_to_update:

                if layer is None:
                    continue

                layer_id = layer.id()
                provider = layer.dataProvider()
                parameter = parameter_config["parameters"]
                parameter_long_name = parameter_config["name"]
                parameter_units = parameter_config["unit"]
                values_t0 = threedi_result.get_values_by_timestep_nr(parameter, 0)
                values_ti = threedi_result.get_values_by_timestep_nr(
                    parameter, timestep_nr
                )

                if isinstance(values_t0, np.ma.MaskedArray):
                    values_t0 = values_t0.filled(np.NaN)
                if isinstance(values_ti, np.ma.MaskedArray):
                    values_ti = values_ti.filled(np.NaN)

                # I suspect the two lines above intend to do the same as the two (new) lines below, but the lines above
                # don't work. Perhaps issue should be solved in threedigrid? [LvW]
                if parameter == WATERLEVEL.name:
                    # dry cells have a NO_DATA_VALUE water level
                    values_t0[values_t0 == NO_DATA_VALUE] = np.NaN
                    values_ti[values_ti == NO_DATA_VALUE] = np.NaN

                if layer_id in result._result_field_names:
                    ti_field_index, t0_field_index = (
                        layer.fields().indexOf(n)
                        for n in result._result_field_names[layer_id]
                    )
                    assert ti_field_index != -1
                    assert t0_field_index != -1
                else:
                    t0_field_index = layer.fields().lookupField("initial_value")
                    ti_field_index = layer.fields().lookupField("result")

                try:
                    ids = ids_by_layer[layer_id]
                except KeyError:
                    ids = np.array([
                        f.id()
                        for f in layer.getFeatures()
                    ], dtype="i8")
                    ids_by_layer[layer_id] = ids

                # NOTE OF CAUTION: subtracting 1 from id  is mandatory for
                # groundwater because those indexes start from 1 (something to
                # do with a trash element), but for the non-groundwater version
                # it is not. HOWEVER, due to some magic hackery in how the
                # *_result layers are created/copied from the regular result
                # layers, the resulting feature ids also start from 1, which
                # why we need to subtract it in both cases, which btw is
                # purely coincidental.
                # TODO: to avoid all this BS this part should be refactored
                # by passing the index to get_values_by_timestep_nr, which
                # should take this into account
                dvalues_t0 = values_t0[ids - 1]
                dvalues_ti = values_ti[ids - 1]
                update_dict = {
                    k: {
                        t0_field_index: NULL if v0 is NaN else v0,
                        ti_field_index: NULL if vi is NaN else vi,
                    } for k, v0, vi in zip(
                        ids.tolist(),
                        dvalues_t0.tolist(),
                        dvalues_ti.tolist(),
                    )
                }
                provider.changeAttributeValues(update_dict)

                if self.difference_checkbox.isChecked() and layer in (
                    self.node_layer,
                    self.node_layer_groundwater,
                    self.cell_layer,
                    self.cell_layer_groundwater,
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

        self.line_parameter_combo_box = QComboBox(self)
        self.line_parameter_combo_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.line_parameter_combo_box.setToolTip("Choose flowline variable to display")
        self.HLayout.addWidget(self.line_parameter_combo_box)

        hline1 = QFrame()
        hline1.setFrameShape(QFrame.VLine)
        hline1.setFrameShadow(QFrame.Sunken)
        self.HLayout.addWidget(hline1)

        self.node_parameter_combo_box = QComboBox(self)
        self.node_parameter_combo_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.node_parameter_combo_box.setToolTip("Choose node variable to display")
        self.HLayout.addWidget(self.node_parameter_combo_box)

        self.difference_checkbox = QCheckBox(self)
        self.difference_checkbox.setToolTip(
            "Display difference relative to simulation start (nodes only)"
        )
        self.difference_label = QLabel(self)
        self.difference_label.setText("Relative")
        self.difference_label.setToolTip(
            "Display difference relative to simulation start (nodes only)"
        )
        self.HLayout.addWidget(self.difference_checkbox)
        self.HLayout.addWidget(self.difference_label)

        hline2 = QFrame()
        hline2.setFrameShape(QFrame.VLine)
        hline2.setFrameShadow(QFrame.Sunken)
        self.HLayout.addWidget(hline2)

        self.lcd = QLCDNumber()
        self.lcd.setToolTip('Time format: "days hours:minutes"')
        self.lcd.setSegmentStyle(QLCDNumber.Flat)

        # Let lcd display a maximum of 9 digits, this way it can display a maximum
        # simulation duration of 999 days, 23 hours and 59 minutes.
        self.lcd.setDigitCount(9)
        self.HLayout.addWidget(self.lcd)

        self.line_parameter_combo_box.activated.connect(
            self.on_line_parameter_change
        )
        self.node_parameter_combo_box.activated.connect(
            self.on_node_parameter_change
        )
        self.difference_checkbox.stateChanged.connect(
            self.on_difference_checkbox_state_change
        )
        self.active = False
        self.setEnabled(False)

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
