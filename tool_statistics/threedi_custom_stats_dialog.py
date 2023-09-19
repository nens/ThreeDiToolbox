# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ThreeDiCustomStatsDialog
                                 A QGIS plugin
 This plugin calculates statistics of 3Di results. The user chooses the variable, aggregation method and
 spatiotemperal filtering.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2019-11-27
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Leendert van Wolfswinkel | Nelen en Schuurmans
        email                : leendert.vanwolfswinkel@nelen-schuurmans.nl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
import sys
from types import MethodType

from qgis.PyQt import QtWidgets
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QPersistentModelIndex
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsCoordinateReferenceSystem
from qgis.gui import QgsFileWidget
from threedigrid.admin.gridresultadmin import GridH5ResultAdmin
from threedi_results_analysis.threedi_plugin_model import ThreeDiResultItem
from threedi_results_analysis.utils.user_messages import pop_up_critical

import logging

logger = logging.getLogger(__name__)

from .presets import PRESETS, Preset, NO_PRESET
from threedi_results_analysis.utils.threedi_result_aggregation.aggregation_classes import (
    Aggregation,
    AggregationSign,
    filter_demanded_aggregations,
    VT_NAMES,
    VT_FLOW,
    VT_FLOW_HYBRID,
    VT_NODE,
    VT_NODE_HYBRID,
    VR_INTERFLOW,
    VR_SIMPLE_INFILTRATION,
    VR_INTERCEPTION,
    VR_NAMES,
)
from threedi_results_analysis.utils.threedi_result_aggregation.constants import (
    AGGREGATION_VARIABLES,
    AGGREGATION_METHODS,
    AGGREGATION_SIGNS,
    NA_TEXT,
)
from .style import (
    DEFAULT_STYLES,
    STYLES,
    Style
)

# This loads the .ui file so that PyQt can populate the plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(
    os.path.join(
        os.path.dirname(__file__), "threedi_custom_stats_dialog_base.ui"
    )
)

DEFAULT_AGGREGATION = Aggregation(
    variable=AGGREGATION_VARIABLES.get_by_short_name("q"),
    sign=AggregationSign(short_name="net", long_name="Net"),
    method=AGGREGATION_METHODS.get_by_short_name("sum"),
)


def update_column_widget(
    self, demanded_aggregations, aggregation_variable_types: list
):
    self.clear()
    filtered_das = filter_demanded_aggregations(
        demanded_aggregations, aggregation_variable_types
    )
    for da in filtered_das:
        column_name = da.as_column_name()
        if column_name is not None:
            self.addItem(da.as_column_name())
    self.addItem("")


class ThreeDiCustomStatsDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, model, parent=None):
        """Constructor."""
        super(ThreeDiCustomStatsDialog, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.model = model

        self.gr = None
        self.result_id = None
        self.demanded_aggregations = []

        for preset in PRESETS:
            self.comboBoxPreset.addItem(preset.name)
            self.comboBoxPreset.setItemData(
                self.comboBoxPreset.count() - 1, preset
            )
        self.comboBoxPreset.currentIndexChanged.connect(
            self.preset_combobox_changed
        )

        self.pushButtonAddAggregation.clicked.connect(self.add_aggregation)
        self.pushButtonRemoveAggregation.clicked.connect(
            self.remove_aggregation
        )
        self.add_aggregation()
        self.tableWidgetAggregations.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.Stretch
        )
        self.tableWidgetAggregations.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.Stretch
        )
        self.tableWidgetAggregations.horizontalHeader().setSectionResizeMode(
            2, QtWidgets.QHeaderView.Stretch
        )
        self.tableWidgetAggregations.horizontalHeader().setSectionResizeMode(
            3, QtWidgets.QHeaderView.Stretch
        )

        # Populate the combobox with the results

        self.resultComboBox.activated.connect(self.results_3di_selected)
        self._populate_results()
        self.resultComboBox.setCurrentIndex(-1)

        self.pushButtonMapCanvas.clicked.connect(self.set_extent_from_map_canvas)
        self.set_extent_from_map_canvas()
        self.mExtentGroupBox.setChecked(False)

        self.init_styling_tab()
        self.set_styling_tab()

        self.dialogButtonBoxOKCancel.button(
            QtWidgets.QDialogButtonBox.Ok
        ).setEnabled(False)

    def _populate_results(self) -> None:
        self.resultComboBox.clear()
        for result in self.model.get_results(checked_only=False):
            self.resultComboBox.addItem(result.text(), result.id)

    def add_aggregation(
        self, *args, aggregation: Aggregation = DEFAULT_AGGREGATION, update_output_layer_names: bool = True
    ):
        """Add a new row to tableWidgetAggregations, always last row"""
        self.tableWidgetAggregations.insertRow(
            self.tableWidgetAggregations.rowCount()
        )
        current_row = self.tableWidgetAggregations.rowCount() - 1

        # variable column
        variable_combobox = QtWidgets.QComboBox()
        for i, variable in enumerate(AGGREGATION_VARIABLES):
            variable_combobox.addItem(
                VT_NAMES[variable.var_type] + ": " + variable.long_name
            )
            variable_combobox.setItemData(i, variable)
        idx = variable_combobox.findText(
            aggregation.variable.long_name, Qt.MatchEndsWith
        )
        variable_combobox.setCurrentIndex(idx)
        variable_combobox.activated.connect(
            self.variable_combobox_text_changed
        )
        self.tableWidgetAggregations.setCellWidget(
            current_row, 0, variable_combobox
        )

        # sign column
        direction_combobox = QtWidgets.QComboBox()
        counter = 0
        for s in AGGREGATION_SIGNS:
            direction_combobox.addItem(s.long_name)
            direction_combobox.setItemData(counter, s)
            counter += 1
        direction_combobox.setCurrentText(aggregation.sign.long_name)
        self.tableWidgetAggregations.setCellWidget(
            current_row, 1, direction_combobox
        )
        direction_combobox.currentTextChanged.connect(
            self.direction_combobox_text_changed
        )

        # method column
        method_combobox = QtWidgets.QComboBox()
        for i, method_str in enumerate(
            aggregation.variable.applicable_methods
        ):
            method = AGGREGATION_METHODS.get_by_short_name(method_str)
            method_combobox.addItem(method.long_name)
            method_combobox.setItemData(i, method)
        if aggregation.method:
            method_combobox.setCurrentText(aggregation.method.long_name)
        self.tableWidgetAggregations.setCellWidget(
            current_row, 2, method_combobox
        )
        method_combobox.currentTextChanged.connect(
            self.method_combobox_text_changed
        )

        # threshold column
        method = method_combobox.currentData()
        self.set_threshold_widget(row=current_row, method=method)

        # units column
        units_combobox = QtWidgets.QComboBox()
        self.tableWidgetAggregations.setCellWidget(
            current_row, 4, units_combobox
        )
        self.set_units_widget(
            row=current_row,
            variable=variable_combobox.itemData(
                variable_combobox.currentIndex()
            ),
            method=method,
        )

        # set the threshold _after_ the units widget is in place
        if aggregation.threshold is not None:
            threshold_widget = self.tableWidgetAggregations.cellWidget(current_row, 3)
            threshold_widget.setValue(aggregation.threshold)

        # TODO: dit is nu lastig te setten obv aggregation, omdat die wel een attribuut multiplier heeft,
        #  maar niet een attribuut units. laat ik nu even voor wat het is
        units_combobox.currentTextChanged.connect(
            self.units_combobox_text_changed
        )

        self.update_demanded_aggregations()
        self.set_styling_tab()
        if update_output_layer_names:
            self._update_output_layer_fields_based_on_aggregations()
        self.validate()
        self._update_variable_list()

    def remove_aggregation(self):
        index_list = []
        for (
            model_index
        ) in self.tableWidgetAggregations.selectionModel().selectedRows():
            index = QPersistentModelIndex(model_index)
            index_list.append(index)

        for index in index_list:
            self.tableWidgetAggregations.removeRow(index.row())

        self.update_demanded_aggregations()
        self._update_output_layer_fields_based_on_aggregations()
        self.validate()

    def variable_combobox_text_changed(self):
        row = self.tableWidgetAggregations.currentRow()
        variable_widget = self.tableWidgetAggregations.cellWidget(row, 0)
        variable = variable_widget.itemData(variable_widget.currentIndex())
        self.set_method_widget(row, variable)
        self.set_direction_widget(row, variable)
        self.update_demanded_aggregations()
        self._update_output_layer_fields_based_on_aggregations()
        self.validate()

    def method_combobox_text_changed(self):
        row = self.tableWidgetAggregations.currentRow()
        variable_widget = self.tableWidgetAggregations.cellWidget(row, 0)
        variable = variable_widget.itemData(variable_widget.currentIndex())
        method_widget = self.tableWidgetAggregations.cellWidget(row, 2)
        method = method_widget.itemData(method_widget.currentIndex())
        self.set_threshold_widget(row=row, method=method)
        self.set_units_widget(row=row, variable=variable, method=method)
        self.update_demanded_aggregations()
        self._update_output_layer_fields_based_on_aggregations()

    def direction_combobox_text_changed(self):
        self.update_demanded_aggregations()
        self._update_output_layer_fields_based_on_aggregations()

    def threshold_value_changed(self):
        self.update_demanded_aggregations()

    def units_combobox_text_changed(self):
        self.update_demanded_aggregations()
        self._update_output_layer_fields_based_on_aggregations()

    def set_direction_widget(self, row, variable):
        na_index = self.tableWidgetAggregations.cellWidget(row, 1).findText(
            NA_TEXT
        )
        if variable.signed:
            if na_index != -1:
                self.tableWidgetAggregations.cellWidget(row, 1).removeItem(
                    na_index
                )
            self.tableWidgetAggregations.cellWidget(row, 1).setCurrentIndex(0)
        else:
            if na_index == -1:
                self.tableWidgetAggregations.cellWidget(row, 1).addItem(
                    NA_TEXT
                )
                na_index = self.tableWidgetAggregations.cellWidget(
                    row, 1
                ).findText(NA_TEXT)
            self.tableWidgetAggregations.cellWidget(row, 1).setCurrentIndex(
                na_index
            )
        self.tableWidgetAggregations.cellWidget(row, 1).setEnabled(
            variable.signed
        )

    def set_method_widget(self, row, variable):
        method_widget = self.tableWidgetAggregations.cellWidget(row, 2)
        method_widget.blockSignals(True)
        method_widget.setEnabled(False)
        method_widget.clear()
        if variable.applicable_methods:
            for method_short_name in variable.applicable_methods:
                method = AGGREGATION_METHODS.get_by_short_name(method_short_name)
                method_widget.addItem(method.long_name, method)
                method_widget.setEnabled(True)
        method_widget.blockSignals(False)
        method = method_widget.itemData(method_widget.currentIndex())
        self.set_threshold_widget(row=row, method=method)

    def set_threshold_widget(self, row, method):
        if method is not None and method.threshold_sources:
            threshold_widget = QtWidgets.QComboBox()
            signal = threshold_widget.currentIndexChanged
            for threshold_source in method.threshold_sources:
                threshold_widget.addItem(threshold_source)
        else:
            threshold_widget = QtWidgets.QDoubleSpinBox()
            threshold_widget.setRange(sys.float_info.min, sys.float_info.max)
            signal = threshold_widget.valueChanged

        threshold_widget.setEnabled(method is not None and method.has_threshold)
        self.tableWidgetAggregations.setCellWidget(row, 3, threshold_widget)
        signal.connect(self.threshold_value_changed)

    def set_units_widget(self, row, variable, method):
        """Called when variable or method changes"""
        units_widget = self.tableWidgetAggregations.cellWidget(row, 4)
        units_widget.clear()

        if not method:
            text = next(iter(variable.units.items()))[0][0]
            return units_widget.addItem(text, 1)
        if method.is_percentage:
            return units_widget.addItem("%", 1)
        if method.is_duration:
            return units_widget.addItem("s", 1)

        for i, (units, multiplier_tuple) in enumerate(variable.units.items()):
            multiplier = multiplier_tuple[0]
            if method.integrates_over_time:
                units_str = units[0]
            else:
                units_str = "/".join(units)
                if len(multiplier_tuple) == 2:
                    multiplier *= multiplier_tuple[1]
            # add item to the widget if no similar item exists:
            if not any(
                units_str in units_widget.itemText(x)
                for x in range(units_widget.count())
            ):
                units_widget.addItem(units_str, multiplier)

    def get_styling_parameters(self, output_type):
        if output_type == "node":
            params_widget = self.tableWidgetNodesStyleParams
        elif output_type == "flowline":
            params_widget = self.tableWidgetFlowlinesStyleParams
        elif output_type == "cell":
            params_widget = self.tableWidgetCellsStyleParams
        else:
            raise ValueError(
                "Invalid output type. Choose one of [node, flowline, cell]."
            )
        result = {}
        for row in range(params_widget.rowCount()):
            result[
                params_widget.item(row, 0).text()
            ] = params_widget.cellWidget(row, 1).currentText()
        return result

    def init_styling_tab(self):
        for style in STYLES:
            if style.output_type == "flowline":
                type_widget = self.comboBoxFlowlinesStyleType
            elif style.output_type == "node":
                type_widget = self.comboBoxNodesStyleType
            elif style.output_type == "cell":
                type_widget = self.comboBoxCellsStyleType

            row = type_widget.count()
            type_widget.addItem(style.name)
            type_widget.setItemData(row, style)

        self.comboBoxFlowlinesStyleType.currentIndexChanged.connect(
            self.flowline_styling_type_changed
        )
        self.comboBoxNodesStyleType.currentIndexChanged.connect(
            self.node_styling_type_changed
        )
        self.comboBoxCellsStyleType.currentIndexChanged.connect(
            self.cell_styling_type_changed
        )
        self.doubleSpinBoxResolution.valueChanged.connect(
            self.raster_resolution_changed
        )
        self.doubleSpinBoxNodesLayerResolution.valueChanged.connect(
            self.nodes_layer_resolution_changed
        )
        self.groupBoxRasters.toggled.connect(self.enable_raster_folder_widget)
        self.mQgsFileWidgetRasterFolder.setStorageMode(
            QgsFileWidget.GetDirectory
        )
        self.mQgsFileWidgetRasterFolder.fileChanged.connect(self.validate)

    def set_styling_tab(
        self,
        flowlines_style: Style = None,
        nodes_style: Style = None,
        cells_style: Style = None,
        flowlines_style_param_values: dict = None,
        cells_style_param_values: dict = None,
        nodes_style_param_values: dict = None,
        uncheck_flowlines_groupbox: bool = False,
        uncheck_nodes_groupbox: bool = False,
        uncheck_cells_groupbox: bool = False
    ):
        """
        Styles can be set (e.g. when a preset is used) or be None so the default for the first variable is used
        """
        # Flowlines
        filtered_das = filter_demanded_aggregations(
            self.demanded_aggregations, [VT_FLOW, VT_FLOW_HYBRID]
        )
        if len(filtered_das) > 0:
            if flowlines_style is None:
                flowlines_style_name = DEFAULT_STYLES[
                    filtered_das[0].variable.short_name
                ]["flowline"].name
            else:
                flowlines_style_name = flowlines_style.name
            idx = self.comboBoxFlowlinesStyleType.findText(
                flowlines_style_name
            )
            if idx > -1:
                self.comboBoxFlowlinesStyleType.setCurrentIndex(idx)
            self.groupBoxFlowlines.setChecked(True)
            self.groupBoxFlowlines.setEnabled(True)
            self.flowline_styling_type_changed(
                param_values=flowlines_style_param_values
            )
        else:
            self.groupBoxFlowlines.setEnabled(False)
            self.groupBoxFlowlines.setChecked(False)
        if uncheck_flowlines_groupbox:
            self.groupBoxFlowlines.setChecked(False)

        # Nodes and cells
        filtered_das = filter_demanded_aggregations(
            self.demanded_aggregations, [VT_NODE, VT_NODE_HYBRID]
        )
        if len(filtered_das) > 0:
            if nodes_style is None:
                nodes_style_name = DEFAULT_STYLES[
                    filtered_das[0].variable.short_name
                ]["node"].name
            else:
                nodes_style_name = nodes_style.name
            idx = self.comboBoxNodesStyleType.findText(nodes_style_name)
            if idx > -1:
                self.comboBoxNodesStyleType.setCurrentIndex(idx)
            self.groupBoxNodes.setEnabled(True)
            self.groupBoxNodes.setChecked(True)
            if uncheck_nodes_groupbox:
                self.groupBoxNodes.setChecked(False)

            if cells_style is None:
                cells_style_name = DEFAULT_STYLES[
                    filtered_das[0].variable.short_name
                ]["cell"].name
            else:
                cells_style_name = cells_style.name

            idx = self.comboBoxCellsStyleType.findText(cells_style_name)
            if idx > -1:
                self.comboBoxCellsStyleType.setCurrentIndex(idx)
            self.groupBoxCells.setEnabled(True)
            self.groupBoxCells.setChecked(True)
            if uncheck_cells_groupbox:
                self.groupBoxCells.setChecked(False)

            # Do not automatically set groupBoxRasters to Checked because this requires follow-up input from the user
            self.groupBoxRasters.setEnabled(True)

            self.node_styling_type_changed(
                param_values=nodes_style_param_values
            )
            self.cell_styling_type_changed(
                param_values=cells_style_param_values
            )

        else:
            self.groupBoxNodes.setEnabled(False)
            self.groupBoxCells.setEnabled(False)
            self.groupBoxRasters.setEnabled(False)

            self.groupBoxNodes.setChecked(False)
            self.groupBoxCells.setChecked(False)
            self.groupBoxRasters.setChecked(False)

    def styling_type_changed(
        self, output_type: str, param_values: dict = None
    ):
        if output_type == "flowline":
            params_widget = self.tableWidgetFlowlinesStyleParams
            type_widget = self.comboBoxFlowlinesStyleType
            aggregation_variable_types = [VT_FLOW, VT_FLOW_HYBRID]
        elif output_type == "node":
            params_widget = self.tableWidgetNodesStyleParams
            type_widget = self.comboBoxNodesStyleType
            aggregation_variable_types = [VT_NODE, VT_NODE_HYBRID]
        elif output_type == "cell":
            params_widget = self.tableWidgetCellsStyleParams
            type_widget = self.comboBoxCellsStyleType
            aggregation_variable_types = [VT_NODE, VT_NODE_HYBRID]
        else:
            raise ValueError(
                "Invalid output type. Choose one of [node, flowline, cell]."
            )
        for i in reversed(range(params_widget.rowCount())):
            params_widget.removeRow(i)
        item_data = type_widget.itemData(type_widget.currentIndex())
        type_widget.setEnabled(True)
        if item_data is not None:
            params = item_data.params
            for row, (param_name, param_type) in enumerate(params.items()):
                params_widget.insertRow(row)
                param_name_item = QtWidgets.QTableWidgetItem(param_name)
                params_widget.setItem(row, 0, param_name_item)
                param_input_widget = QtWidgets.QComboBox()
                param_input_widget.update = MethodType(
                    update_column_widget, param_input_widget
                )
                param_input_widget.update(
                    demanded_aggregations=self.demanded_aggregations,
                    aggregation_variable_types=aggregation_variable_types,
                )
                params_widget.setCellWidget(row, 1, param_input_widget)
        if param_values is not None:
            for param, value in param_values.items():
                row = params_widget.findItems(param, Qt.MatchFixedString)[
                    0
                ].row()
                params_input_widget = params_widget.cellWidget(row, 1)
                idx = params_input_widget.findText(value)
                params_input_widget.setCurrentIndex(idx)

    def node_styling_type_changed(
        self, signal: int = 1, param_values: dict = None
    ):
        self.styling_type_changed(
            output_type="node", param_values=param_values
        )

    def cell_styling_type_changed(
        self, signal: int = 1, param_values: dict = None
    ):
        self.styling_type_changed(
            output_type="cell", param_values=param_values
        )

    def flowline_styling_type_changed(
        self, signal: int = 1, param_values: dict = None
    ):
        self.styling_type_changed(
            output_type="flowline", param_values=param_values
        )

    def raster_resolution_changed(self):
        self.doubleSpinBoxNodesLayerResolution.setValue(
            self.doubleSpinBoxResolution.value()
        )

    def nodes_layer_resolution_changed(self):
        self.doubleSpinBoxResolution.setValue(
            self.doubleSpinBoxNodesLayerResolution.value()
        )

    def update_gr(self, results_3di, gridadmin):
        if os.path.isfile(results_3di) and os.path.isfile(gridadmin):
            self.gr = GridH5ResultAdmin(gridadmin, results_3di)
            crs = QgsCoordinateReferenceSystem(
                "EPSG:{}".format(self.gr.epsg_code)
            )
            self.mExtentGroupBox.setOutputCrs(crs)
            output_timestep_best_guess = int(
                self.gr.nodes.timestamps[-1]
                / (len(self.gr.nodes.timestamps) - 1)
            )
            self.doubleSpinBoxStartTime.setMaximum(
                int(self.gr.nodes.timestamps[-1])
            )
            self.doubleSpinBoxStartTime.setSingleStep(
                output_timestep_best_guess
            )
            self.doubleSpinBoxEndTime.setSingleStep(output_timestep_best_guess)
            self.doubleSpinBoxEndTime.setMaximum(
                int(self.gr.nodes.timestamps[-1])
            )
            self.doubleSpinBoxEndTime.setValue(
                int(self.gr.nodes.timestamps[-1])
            )
            self.doubleSpinBoxResolution.setValue(self.gr.grid.dx[0])
            self.doubleSpinBoxNodesLayerResolution.setValue(self.gr.grid.dx[0])
            if self.mQgsFileWidgetRasterFolder.filePath() == "":
                results_3di_dir = os.path.dirname(results_3di)
                self.mQgsFileWidgetRasterFolder.setFilePath(results_3di_dir)
        else:
            self.gr = None

        self._update_variable_list()

    def results_3di_selected(self, index):
        result_id = self.resultComboBox.itemData(index)
        result = self.model.get_result(result_id)
        results_3di = result.path
        gridadmin = result.parent().path.with_suffix('.h5')
        assert os.path.isfile(results_3di) and os.path.isfile(gridadmin)
        self.update_gr(str(results_3di), str(gridadmin))
        if self.validate():
            self.result_id = result_id

    def add_result(self, result_item: ThreeDiResultItem) -> None:
        currentIndex = self.resultComboBox.currentIndex()
        self.resultComboBox.addItem(result_item.text(), result_item.id)
        self.resultComboBox.setCurrentIndex(currentIndex)

    def remove_result(self, result_item: ThreeDiResultItem):
        idx = self.resultComboBox.findData(result_item.id)
        logger.info(f"Removing result {result_item.id} at index {idx}")
        assert idx != -1
        if idx == self.resultComboBox.currentIndex():
            # TODO: clean up?
            self.resultComboBox.setCurrentIndex(-1)

        self.resultComboBox.removeItem(idx)

    def change_result(self, result_item: ThreeDiResultItem):
        idx = self.resultComboBox.findData(result_item.id)
        assert idx != -1
        self.resultComboBox.setItemText(idx, result_item.text())

        # # also rename result layer groups
        # if result_item.id in self.preloaded_layers:
        #     layer_result_group = self.preloaded_layers[result_item.id]["group"]
        #     layer_result_group.setName(result_item.text())

    def set_extent_from_map_canvas(self):
        canvas_extent = self.iface.mapCanvas().extent()
        project = QgsProject.instance()
        crs = project.crs()
        self.mExtentGroupBox.setOutputExtentFromUser(canvas_extent, crs)

    def enable_raster_folder_widget(self):
        if self.groupBoxRasters.isChecked():
            self.mQgsFileWidgetRasterFolder.setEnabled(True)
        else:
            self.mQgsFileWidgetRasterFolder.setEnabled(False)
        self.validate()

    def preset_combobox_changed(self, index):
        logger.error("preset_combobox_changed")
        preset = self.comboBoxPreset.itemData(index)

        # Check whether the currently selected model support the preset's aggregations
        if self.gr:
            containing_information = self._retrieve_model_info()
            for agg_var in preset.aggregations():
                missing_info = [item for item in agg_var.variable.requirements if item not in containing_information]
                if missing_info:
                    pop_up_critical(f"The currently selected 3Di model does not contain all required info for aggregation '{agg_var.variable.long_name}': {[VR_NAMES[item] for item in missing_info]}")
                    no_preset_idx = self.comboBoxPreset.findText(NO_PRESET.name)
                    self.comboBoxPreset.setCurrentIndex(no_preset_idx)  # reset to no preset
                    return

        self.presetHelpTextBrowser.setText(preset.description)
        self.apply_preset(preset)
        self._update_variable_list()

    def apply_preset(self, preset: Preset):
        """
        Set dialog widgets according to given preset.
        If no styling is given for an output_type, that output type's styling panel checkbox is set to False
        """

        # Set the default output layer names based on preset, if the current layer name value is not modified yet
        if not self.lineEditOutputFlowLayer.isModified():
            self.lineEditOutputFlowLayer.setText(preset.flowlines_layer_name if preset.flowlines_layer_name else "")

        if not self.lineEditOutputCellLayer.isModified():
            self.lineEditOutputCellLayer.setText(preset.cells_layer_name if preset.cells_layer_name else "")

        if not self.lineEditOutputNodeLayer.isModified():
            self.lineEditOutputNodeLayer.setText(preset.nodes_layer_name if preset.nodes_layer_name else "")

        if not self.lineEditOutputRasterLayer.isModified():
            self.lineEditOutputRasterLayer.setText(preset.raster_layer_name if preset.raster_layer_name else "")

        # set manhole filter
        self.onlyManholeCheckBox.setChecked(preset.only_manholes)

        # remove existing aggregations
        self.tableWidgetAggregations.setRowCount(0)

        # add aggregations from preset
        for da in preset.aggregations():
            self.add_aggregation(aggregation=da, update_output_layer_names=(preset == NO_PRESET))

        # set "resample point layer" from preset
        self.checkBoxResample.setChecked(preset.resample_point_layer)

        # set styling from preset
        self.set_styling_tab(
            flowlines_style=preset.flowlines_style,
            nodes_style=preset.nodes_style,
            cells_style=preset.cells_style,
            flowlines_style_param_values=preset.flowlines_style_param_values,
            nodes_style_param_values=preset.nodes_style_param_values,
            cells_style_param_values=preset.cells_style_param_values,
            uncheck_flowlines_groupbox=preset.flowlines_style is None,
            uncheck_nodes_groupbox=preset.nodes_style is None,
            uncheck_cells_groupbox=preset.cells_style is None

        )

    def _update_output_layer_fields_based_on_aggregations(self):
        logger.info("Output layer suggestion based on selected aggregations")

        # Set the default output layer names based on preset, if the current layer name value is empty
        suggested_flow_output_layer_name = "flowlines: "
        suggested_cell_output_layer_name = "cells: "
        suggested_node_output_layer_name = "nodes: "
        suggested_raster_output_layer_name = "raster: "

        postfix = ""
        if len(self.demanded_aggregations) == 0:
            postfix = "aggregation output layer"
        elif len(self.demanded_aggregations) == 1:
            agg_var = self.demanded_aggregations[0]
            postfix = agg_var.variable.long_name
            if agg_var.sign:
                postfix += " " + agg_var.sign.short_name
            if agg_var.method:
                postfix += " " + agg_var.method.short_name
            postfix += f" [{agg_var.unit_str}]"  # attribute attached in update_demanded_aggegrations()
        else:
            postfix = "multiple aggregations"

        if not self.lineEditOutputFlowLayer.isModified():
            self.lineEditOutputFlowLayer.setText(suggested_flow_output_layer_name + postfix)

        if not self.lineEditOutputCellLayer.isModified():
            self.lineEditOutputCellLayer.setText(suggested_cell_output_layer_name + postfix)

        if not self.lineEditOutputNodeLayer.isModified():
            self.lineEditOutputNodeLayer.setText(suggested_node_output_layer_name + postfix)

        if not self.lineEditOutputRasterLayer.isModified():
            self.lineEditOutputRasterLayer.setText(suggested_raster_output_layer_name + postfix)

    def _retrieve_model_info(self):
        containing_information = []
        if self.gr:
            if self.gr.has_simple_infiltration:
                containing_information.append(VR_SIMPLE_INFILTRATION)
            if getattr(self.gr, "has_interflow", True):
                containing_information.append(VR_INTERFLOW)
            elif self.gr.has_interflow:
                containing_information.append(VR_INTERFLOW)
            if self.gr.has_interception:
                containing_information.append(VR_INTERCEPTION)

        return containing_information

    def _update_variable_list(self):
        # Tterate over the rows and check the items in the variable combobox: disable variable when currently loaded
        # model is not supporting this variable
        containing_information = self._retrieve_model_info()

        row_count = self.tableWidgetAggregations.rowCount()
        for row in range(row_count):
            variable_widget = self.tableWidgetAggregations.cellWidget(row, 0)
            #  Iterate over the variables in the combobox
            for item_idx in range(variable_widget.count()):
                variable = variable_widget.itemData(item_idx)

                if self.gr:
                    missing_info = [item for item in variable.requirements if item not in containing_information]
                    if missing_info:
                        if item_idx == variable_widget.currentIndex():
                            pop_up_critical(f"The currently selected model does not contain all required info for aggregation '{variable.long_name}': {[VR_NAMES[item] for item in missing_info]}")
                        variable_widget.model().item(item_idx).setEnabled(False)
                    else:
                        variable_widget.model().item(item_idx).setEnabled(True)
                else:
                    variable_widget.model().item(item_idx).setEnabled(True)

    def update_demanded_aggregations(self):
        self.demanded_aggregations = []
        row_count = self.tableWidgetAggregations.rowCount()
        for row in range(row_count):
            # Variable
            variable_widget = self.tableWidgetAggregations.cellWidget(row, 0)
            variable = variable_widget.itemData(variable_widget.currentIndex())

            # Direction
            direction_widget = self.tableWidgetAggregations.cellWidget(row, 1)
            sign = direction_widget.itemData(direction_widget.currentIndex())

            # Method
            method_widget = self.tableWidgetAggregations.cellWidget(row, 2)
            method = method_widget.itemData(method_widget.currentIndex())

            # Threshold
            threshold_widget = self.tableWidgetAggregations.cellWidget(row, 3)
            if method is not None and method.threshold_sources:
                threshold = threshold_widget.currentText()
            else:
                threshold = threshold_widget.value()

            # Multiplier (unit conversion)
            units_widget = self.tableWidgetAggregations.cellWidget(row, 4)
            multiplier = units_widget.itemData(units_widget.currentIndex())

            da = Aggregation(
                variable=variable,
                sign=sign,
                method=method,
                threshold=threshold,
                multiplier=multiplier,
            )

            # For visualisation-purposes we also (redundantly) attach the unit text
            da.unit_str = units_widget.currentText()

            if da.is_valid():
                self.demanded_aggregations.append(da)

            else:
                # This method is often called due to a signal being fired, but this can also happen when the contents of
                # the row's widgets are not yet complete, i.e. the information in the row cannot be tranlated to a
                # valid Aggregation instance. We just continue, but self.demanded_aggregations_are_valid() will now
                # return False until update_demanded_aggregations() will be called again with valid contents in the
                # aggregations table
                return

        self.set_styling_tab()

    def demanded_aggregations_are_valid(self) -> bool:
        """
        Checks if the contents of the table of demanded aggregations can be interpreted in a valid way
        """
        if self.tableWidgetAggregations.rowCount() != len(
            self.demanded_aggregations
        ):
            return False
        if not all([da.is_valid() for da in self.demanded_aggregations]):
            return False
        return True

    def validate(self) -> bool:
        valid = True
        logger.info([agg.variable.long_name for agg in self.demanded_aggregations])
        if not isinstance(self.gr, GridH5ResultAdmin):
            logger.warning("Invalid or no result file selected")
            valid = False
        if not self.tableWidgetAggregations.rowCount() > 0:
            logger.warning("Zero aggregations selected")
            valid = False
        if (
            self.groupBoxRasters.isChecked()
            and self.mQgsFileWidgetRasterFolder.filePath() == ""
        ):
            logger.warning("No raster folder selected")
            valid = False
        if not self.demanded_aggregations_are_valid():
            logger.warning("Demanded aggregations are not valid")
            valid = False

        # Check whether the demanded aggregations are compatible with the model (or: model contains all required info)
        if self.gr:
            containing_information = self._retrieve_model_info()

            for agg in self.demanded_aggregations:
                missing_info = [item not in containing_information for item in agg.variable.requirements]
                if missing_info:
                    logger.warning(f"Model does not contain all info for demanded aggregations: {[VR_NAMES[item] for item in missing_info]}")
                    valid = False
                    break

        self.dialogButtonBoxOKCancel.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(valid)

        return valid
