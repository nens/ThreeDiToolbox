# -*- coding: utf-8 -*-
"""
This tool is a direct copy (except some flake8 changes) from:
https://github.com/threedi/beta-plugins/tree/master/threedi_custom_stats

/***************************************************************************
 ThreeDiCustomStats
                                 A QGIS plugin
 This plugin calculates statistics of 3Di results. The user chooses the variable, aggregation method and spatiotemperal filtering.
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
from typing import List

from osgeo.gdal import GetDriverByName
from qgis.core import Qgis, QgsApplication, QgsProject, QgsTask, QgsRasterLayer
from threedi_results_analysis.utils.threedi_result_aggregation.base import aggregate_threedi_results
from threedi_results_analysis.utils.ogr2qgis import as_qgis_memory_layer

# Import the code for the dialog
from .threedi_custom_stats_dialog import ThreeDiCustomStatsDialog
from threedi_results_analysis.threedi_plugin_tool import ThreeDiPluginTool
from threedi_results_analysis.threedi_plugin_model import ThreeDiResultItem, ThreeDiGridItem
from qgis.PyQt.QtCore import pyqtSlot

import os
import os.path
import logging

logger = logging.getLogger(__name__)


# TODO: cfl strictness factors instelbaar maken
# TODO: berekening van max timestep ook op basis van volume vs. debiet
# TODO: opties af laten hangen van wat er in het model aanwezig is; is wel tricky ivm presets
GROUP_NAME = "Result aggregation outputs"


class Aggregate3DiResults(QgsTask):
    def __init__(
        self,
        description: str,
        parent: ThreeDiCustomStatsDialog,
        layer_groups,
        result: ThreeDiResultItem,
        demanded_aggregations: List,
        bbox,
        start_time: int,
        end_time: int,
        only_manholes: bool,
        interpolation_method,
        resample_point_layer: bool,
        resolution,
        output_flowlines: bool,
        output_cells: bool,
        output_nodes: bool,
        output_pumps: bool,
        output_rasters: bool,
    ):
        super().__init__(description, QgsTask.CanCancel)
        self.exception = None
        self.parent = parent
        self.parent.setEnabled(False)
        self.result = result
        self.layer_groups = layer_groups
        self.demanded_aggregations = demanded_aggregations
        self.bbox = bbox
        self.start_time = start_time
        self.end_time = end_time
        self.only_manholes = only_manholes
        self.interpolation_method = interpolation_method
        self.resample_point_layer = resample_point_layer
        self.resolution = resolution
        self.output_flowlines = output_flowlines
        self.output_cells = output_cells
        self.output_nodes = output_nodes
        self.output_pumps = output_pumps
        self.output_rasters = output_rasters

        self.parent.iface.messageBar().pushMessage(
            "3Di Statistics",
            "Started aggregating 3Di results",
            level=Qgis.Info,
            duration=3,
        )
        self.parent.iface.mainWindow().repaint()  # to show the message before the task starts

    def run(self):
        grid_admin = str(self.result.parent().path.with_suffix('.h5'))
        grid_admin_gpkg = str(self.result.parent().path.with_suffix('.gpkg'))
        results_3di = str(self.result.path)

        try:
            self.ogr_ds, self.mem_rasts = aggregate_threedi_results(
                gridadmin=grid_admin,
                gridadmin_gpkg=grid_admin_gpkg,
                results_3di=results_3di,
                demanded_aggregations=self.demanded_aggregations,
                bbox=self.bbox,
                start_time=self.start_time,
                end_time=self.end_time,
                only_manholes=self.only_manholes,
                interpolation_method=self.interpolation_method,
                resample_point_layer=self.resample_point_layer,
                resolution=self.resolution,
                output_flowlines=self.output_flowlines,
                output_cells=self.output_cells,
                output_nodes=self.output_nodes,
                output_pumps=self.output_pumps,
                output_rasters=self.output_rasters,
            )

            return True

        except Exception as e:
            self.exception = e

        return False

    def _get_or_create_result_group(self, result: ThreeDiResultItem, group_name: str):
        # We'll place the result layers in a dedicated result group
        grid_item = result.parent()
        assert grid_item
        tool_group = grid_item.layer_group.findGroup(group_name)
        if not tool_group:
            tool_group = grid_item.layer_group.insertGroup(0, group_name)
            tool_group.willRemoveChildren.connect(lambda n, i1, i2: self._group_removed(n, i1, i2))

        # Add result group
        result_group = tool_group.findGroup(result.text())
        if not result_group:
            result_group = tool_group.addGroup(result.text())
            self.layer_groups[result.id] = result_group
            # Use to modify result name when QgsLayerTreeNode is renamed. Note that this does not cause a
            # infinite signal loop because the model only emits the result_changed when the text has actually
            # changed.
            result_group.nameChanged.connect(lambda _, txt, result_item=result: result_item.setText(txt))

        return result_group

    def _group_removed(self, n, idxFrom, idxTo):
        for result_id in list(self.layer_groups):
            group = self.layer_groups[result_id]
            for i in range(idxFrom, idxTo+1):
                if n.children()[i] is group:
                    del self.layer_groups[result_id]

    def finished(self, result):
        if self.exception is not None:
            self.parent.setEnabled(True)
            self.parent.repaint()
            raise self.exception
        if result:
            # Add layers to layer tree
            # They are added in order so the raster is below the polygon is below the line is below the point layer

            # raster layer
            if len(self.mem_rasts) > 0:
                for rastname, rast in self.mem_rasts.items():
                    raster_output_dir = (
                        self.parent.mQgsFileWidgetRasterFolder.filePath()
                    )
                    raster_output_fn = os.path.join(
                        raster_output_dir, rastname + ".tif"
                    )
                    drv = GetDriverByName("GTiff")
                    drv.CreateCopy(
                        utf8_path=raster_output_fn, src=rast
                    )
                    layer_name = self.parent.lineEditOutputRasterLayer.text() + f": {rastname}"
                    raster_layer = QgsRasterLayer(
                        raster_output_fn,
                        layer_name or f"Aggregation results: raster {rastname}")
                    result_group = self._get_or_create_result_group(self.result, GROUP_NAME)
                    QgsProject.instance().addMapLayer(raster_layer, addToLegend=False)
                    result_group.insertLayer(0, raster_layer)

            # vector layers
            for output_layer_name, layer_name_widget, style_type_widget in [
                ("cell", self.parent.lineEditOutputCellLayer, self.parent.comboBoxCellsStyleType),
                ("flowline", self.parent.lineEditOutputFlowLayer, self.parent.comboBoxFlowlinesStyleType),
                ("pump", self.parent.lineEditOutputPumpsLayer, self.parent.comboBoxPumpsStyleType),
                ("node", self.parent.lineEditOutputNodeLayer, self.parent.comboBoxNodesStyleType),
                ("node_resampled", self.parent.lineEditOutputNodeLayer, self.parent.comboBoxNodesStyleType),
            ]:
                ogr_lyr = self.ogr_ds.GetLayerByName(output_layer_name)
                if ogr_lyr is not None:
                    if ogr_lyr.GetFeatureCount() > 0:
                        layer_name = layer_name_widget.text()
                        qgs_lyr = as_qgis_memory_layer(
                            ogr_lyr,
                            layer_name or f"Aggregation results: {output_layer_name}"
                        )
                        result_group = self._get_or_create_result_group(self.result, GROUP_NAME)
                        QgsProject.instance().addMapLayer(qgs_lyr, addToLegend=False)
                        result_group.insertLayer(0, qgs_lyr)
                        style = (style_type_widget.currentData())
                        style_kwargs = self.parent.get_styling_parameters(output_type=style.output_type)
                        style.apply(qgis_layer=qgs_lyr, style_kwargs=style_kwargs)

            self.parent.setEnabled(True)
            self.parent.iface.messageBar().pushMessage(
                "3Di Result aggregation",
                "Finished custom aggregation",
                level=Qgis.Success,
                duration=3,
            )

        else:
            self.parent.setEnabled(True)
            self.parent.iface.messageBar().pushMessage(
                "3Di Result aggregation",
                "Aggregating 3Di results returned no results",
                level=Qgis.Warning,
                duration=3,
            )

    def cancel(self):
        self.parent.iface.messageBar().pushMessage(
            "3Di Result aggregation",
            "Pre-processing simulation results cancelled by user",
            level=Qgis.Info,
            duration=3,
        )
        super().cancel()


class StatisticsTool(ThreeDiPluginTool):

    def __init__(self, iface, model):
        super().__init__()

        self.iface = iface
        self.model = model
        self.icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "icon_custom_statistics.png")
        self.menu_text = u"Post-processing tool to generate custom time aggregations of 3Di results and visualize these on the map canvas"
        self.dlg = None

        # Keeps track of the layer groups already generated
        self.layer_groups = {}

        # Check if plugin was started the first time in current QGIS session
        self.first_start = True

        self.tm = QgsApplication.taskManager()

    def read(self, _) -> bool:
        """A new project is loaded, see if we can fetch some precreated groups"""
        return self._collect_result_groups()

    def _collect_result_groups(self):
        # Go through the results and check whether corresponding output layer groups already exist
        self.layer_groups = {}

        results = self.model.get_results(False)
        for result in results:
            grid_item = result.parent()
            assert grid_item
            tool_group = grid_item.layer_group.findGroup(GROUP_NAME)
            if tool_group:
                tool_group.willRemoveChildren.connect(lambda n, i1, i2: self._group_removed(n, i1, i2))
                result_group = tool_group.findGroup(result.text())
                if result_group:
                    self.layer_groups[result.id] = result_group
                    result_group.nameChanged.connect(lambda _, txt, result_item=result: result_item.setText(txt))
        return True

    def _group_removed(self, n, idxFrom, idxTo):
        for result_id in list(self.layer_groups):
            group = self.layer_groups[result_id]
            for i in range(idxFrom, idxTo+1):
                if n.children()[i] is group:
                    del self.layer_groups[result_id]

    def run(self):

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start:
            self._collect_result_groups()
            self.first_start = False
            self.dlg = ThreeDiCustomStatsDialog(self.iface, self.model)

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # 3Di results
            result = self.model.get_result(self.dlg.result_id)

            # Filtering parameters
            start_time = self.dlg.doubleSpinBoxStartTime.value()
            end_time = self.dlg.doubleSpinBoxEndTime.value()
            bbox_qgs_rectangle = (
                self.dlg.mExtentGroupBox.outputExtent()
            )  # bbox is now a https://qgis.org/pyqgis/master/core/QgsRectangle.html#qgis.core.QgsRectangle

            bbox = None
            if bbox_qgs_rectangle is not None:
                if not bbox_qgs_rectangle.isEmpty():
                    bbox = [
                        bbox_qgs_rectangle.xMinimum(),
                        bbox_qgs_rectangle.yMinimum(),
                        bbox_qgs_rectangle.xMaximum(),
                        bbox_qgs_rectangle.yMaximum(),
                    ]
            only_manholes = self.dlg.onlyManholeCheckBox.isChecked()

            # Resolution
            resolution = self.dlg.doubleSpinBoxResolution.value()

            # Outputs
            output_flowlines = self.dlg.groupBoxFlowlines.isChecked()
            output_nodes = self.dlg.groupBoxNodes.isChecked()
            output_cells = self.dlg.groupBoxCells.isChecked()
            output_pumps = self.dlg.groupBoxPumps.isChecked()
            output_rasters = self.dlg.groupBoxRasters.isChecked()

            # Resample point layer
            resample_point_layer = self.dlg.checkBoxResample.isChecked()
            if resample_point_layer:
                interpolation_method = "linear"
            else:
                interpolation_method = None

            aggregate_threedi_results_task = Aggregate3DiResults(
                description="Aggregate 3Di Results",
                parent=self.dlg,
                layer_groups=self.layer_groups,
                result=result,
                demanded_aggregations=self.dlg.demanded_aggregations,
                bbox=bbox,
                start_time=start_time,
                end_time=end_time,
                only_manholes=only_manholes,
                interpolation_method=interpolation_method,
                resample_point_layer=resample_point_layer,
                resolution=resolution,
                output_flowlines=output_flowlines,
                output_cells=output_cells,
                output_nodes=output_nodes,
                output_pumps=output_pumps,
                output_rasters=output_rasters,
            )
            self.tm.addTask(aggregate_threedi_results_task)

    @pyqtSlot(ThreeDiResultItem)
    def result_added(self, result_item: ThreeDiResultItem) -> None:
        self.action_icon.setEnabled(self.model.number_of_results() > 0)
        if not self.dlg:
            return

        self.dlg.add_result(result_item)

    @pyqtSlot(ThreeDiResultItem)
    def result_removed(self, result_item: ThreeDiResultItem) -> None:
        self.action_icon.setEnabled(self.model.number_of_results() > 0)
        if not self.dlg:
            return

        # Remove from combobox etc
        self.dlg.remove_result(result_item)

        # Remove group in layer manager
        if result_item.id in self.layer_groups:
            result_group = self.layer_groups[result_item.id]
            tool_group = result_group.parent()
            tool_group.removeChildNode(result_group)

            # In case the tool ("statistics") group is now empty, we'll remove that too
            tool_group = result_item.parent().layer_group.findGroup(GROUP_NAME)
            if len(tool_group.children()) == 0:
                tool_group.parent().removeChildNode(tool_group)

            # Via a callback (willRemoveChildren), the deleted group should already have removed itself from the list
            assert result_item.id not in self.layer_groups

    @pyqtSlot(ThreeDiResultItem)
    def result_changed(self, result_item: ThreeDiResultItem) -> None:
        if result_item.id in self.layer_groups:
            self.layer_groups[result_item.id].setName(result_item.text())

        if not self.dlg:
            return
        self.dlg.change_result(result_item)

    @pyqtSlot(ThreeDiGridItem)
    def grid_changed(self, grid_item: ThreeDiGridItem) -> None:
        if not self.dlg:
            return

        results = []
        self.model.get_results_from_item(grid_item, False, results)
        for result in results:
            self.dlg.change_result(result)

    def on_unload(self):
        if self.dlg:
            self.dlg.close()
            self.dlg = None
            self.first_start = True
        self.layer_groups = {}
