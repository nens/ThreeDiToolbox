from qgis.core import QgsFeatureRequest
from qgis.core import Qgis
from qgis.core import QgsWkbTypes
from qgis.core import QgsValueMapFieldFormatter
from qgis.core import QgsMapLayer
from qgis.core import QgsFeature
from qgis.gui import QgsMapToolIdentify
from qgis.gui import QgsRubberBand
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtCore import pyqtSlot
from qgis.PyQt.QtCore import QEvent
from qgis.PyQt.QtCore import QMetaObject
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QCheckBox
from qgis.PyQt.QtWidgets import QComboBox
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.PyQt.QtWidgets import QHBoxLayout
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtWidgets import QPushButton
from qgis.PyQt.QtWidgets import QSizePolicy
from qgis.PyQt.QtWidgets import QSpacerItem
from qgis.PyQt.QtWidgets import QTableView
from qgis.PyQt.QtWidgets import QAbstractItemView
from qgis.PyQt.QtWidgets import QTabWidget
from qgis.PyQt.QtWidgets import QVBoxLayout
from qgis.PyQt.QtWidgets import QWidget
from ThreeDiToolbox.datasource.result_constants import LAYER_QH_TYPE_MAPPING
from ThreeDiToolbox.tool_graph.graph_model import LocationTimeseriesModel
from ThreeDiToolbox.utils.user_messages import messagebar_message
from ThreeDiToolbox.utils.user_messages import statusbar_message
from ThreeDiToolbox.utils.utils import generate_parameter_config
from ThreeDiToolbox.utils.constants import TOOLBOX_MESSAGE_TITLE
from qgis.core import QgsVectorLayer
from ThreeDiToolbox.datasource.threedi_results import normalized_object_type
from ThreeDiToolbox.threedi_plugin_model import ThreeDiPluginModel, ThreeDiResultItem

from typing import List

import logging
import pyqtgraph as pg


logger = logging.getLogger(__name__)

pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")

# Layer providers that we can use for the graph
VALID_PROVIDERS = ["spatialite", "memory", "ogr"]
# providers which don't have a primary key
PROVIDERS_WITHOUT_PRIMARY_KEY = ["memory", "ogr"]


def is_threedi_layer(vector_layer: QgsVectorLayer) -> bool:
    """
    Checks whether a layer has been generated by the 3Di toolbox.

    It is an extensive check, trying to be backwards compatible with older tools.
    """
    if not vector_layer:
        return False

    provider = vector_layer.dataProvider()
    valid_object_type = normalized_object_type(vector_layer.name())

    if provider.name() in ["spatialite", "memory", "ogr"] and valid_object_type:
        return True
    elif vector_layer.objectName() in ("flowline", "node", "pump_linestring"):
        return True

    return False


class GraphPlot(pg.PlotWidget):
    """Graph element"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.showGrid(True, True, 0.5)
        self.current_parameter = None
        self.location_model = None
        self.result_model = None
        self.parent = parent
        self.absolute = False
        self.current_time_units = "hrs"
        self.setLabel("bottom", "Time", self.current_time_units)
        # Auto SI prefix scaling doesn't work properly with m3, m2 etc.
        self.getAxis("left").enableAutoSIPrefix(False)

    def on_close(self):
        """
        unloading widget and remove all required stuff
        :return:
        """
        if self.location_model:
            self.location_model.dataChanged.disconnect(self.location_data_changed)
            self.location_model.rowsInserted.disconnect(self.on_insert_locations)
            self.location_model.rowsAboutToBeRemoved.disconnect(
                self.on_remove_locations
            )
            self.location_model = None

    def closeEvent(self, event):
        """
        overwrite of QDockWidget class to emit signal
        :param event: QEvent
        """
        self.on_close()
        event.accept()

    def set_location_model(self, model):
        self.location_model = model
        self.location_model.dataChanged.connect(self.location_data_changed)
        self.location_model.rowsInserted.connect(self.on_insert_locations)
        self.location_model.rowsAboutToBeRemoved.connect(self.on_remove_locations)

    def set_result_model(self, model: ThreeDiPluginModel):
        self.result_model = model

    def on_insert_locations(self, parent, start, end):
        """
        add list of items to graph. based on Qt addRows model trigger
        :param parent: parent of event (Qt parameter)
        :param start: first row nr
        :param end: last row nr
        """
        for i in range(start, end + 1):
            item = self.location_model.rows[i]
            for i in range(len(self.result_model.get_results(selected=True))):  # iterate rows
                if True:  # ds.active.value:
                    result_item = self.result_model.get_results(selected=True)[i]
                    self.addItem(
                        item.plots(
                            self.current_parameter["parameters"],
                            result_item,
                            absolute=self.absolute,
                            time_units=self.current_time_units,
                        )
                    )

    def on_remove_locations(self, index, start, end):
        """
        remove items from graph. based on Qt model removeRows
        trigger
        :param index: Qt Index (not used)
        :param start: first row nr
        :param end: last row nr
        """
        logger.error(f"remove location: {index} {start} {end}")
        for i in range(start, end + 1):
            item = self.location_model.rows[i]
            if True:  # item.active.value:
                for r in range(len(self.result_model.get_results(selected=True))):  # rows:
                    if True:  # ds.active.value:
                        result_item = self.result_model.get_results(selected=True)[r]
                        self.removeItem(
                            item.plots(self.current_parameter["parameters"], result_item=result_item, time_units=self.current_time_units, absolute=self.absolute)
                        )

    def location_data_changed(self, index):
        """
        change graphs based on changes in locations
        :param index: index of changed field
        """
        if self.location_model.columns[index.column()].name == "active":

            for i in range(len(self.result_model.get_results(selected=True))):  # rows:
                if True:  # self.result_model.rows[i].active.value:
                    result_item = self.result_model.get_results(selected=True)[i]
                    if self.location_model.rows[index.row()].active.value:
                        self.show_timeseries(index.row(), result_item)
                    else:
                        self.hide_timeseries(index.row(), result_item)

        elif self.location_model.columns[index.column()].name == "hover":
            item = self.location_model.rows[index.row()]
            for i in range(len(self.result_model.get_results(selected=True))):  # rows:
                if True:  # ds.active.value:
                    result_item = self.result_model.get_results(selected=True)[i]
                    width = 2
                    if item.hover.value:
                        width = 5
                    item.plots(self.current_parameter["parameters"], result_item=result_item, time_units=self.current_time_units, absolute=self.absolute).setPen(
                        color=item.color.qvalue, width=width, style=result_item._pattern)

    def hide_timeseries(self, location_nr, result_item):
        """
        hide timeseries of location in graph
        :param row_nr: integer, row number of location
        """

        plot = self.location_model.rows[location_nr].plots(
            self.current_parameter["parameters"], result_item=result_item, time_units=self.current_time_units, absolute=self.absolute
        )
        self.removeItem(plot)

    def show_timeseries(self, location_nr, result_item):
        """
        show timeseries of location in graph
        :param row_nr: integer, row number of location
        """

        plot = self.location_model.rows[location_nr].plots(
            self.current_parameter["parameters"], result_item=result_item, time_units=self.current_time_units, absolute=self.absolute
        )
        self.addItem(plot)

    def set_parameter(self, parameter, time_units):
        """
        on selection of parameter (in combobox), change timeseries in graphs
        :param parameter: parameter identification string
        :param time_units: current time units string
        """

        if self.current_parameter == parameter and self.current_time_units == time_units:
            return

        old_parameter = self.current_parameter
        old_time_units = self.current_time_units
        self.current_parameter = parameter
        self.current_time_units = time_units

        for item in self.location_model.rows:
            if True:  # item.active.value:
                for i in range(len(self.result_model.get_results(selected=True))):  # rows:
                    if True:  # ds.active.value:
                        result_item = self.result_model.get_results(selected=True)[i]

                        self.removeItem(
                            item.plots(old_parameter["parameters"], result_item=result_item, time_units=old_time_units, absolute=self.absolute)
                        )
                        self.addItem(
                            item.plots(self.current_parameter["parameters"], result_item=result_item, time_units=self.current_time_units, absolute=self.absolute)
                        )

        self.setLabel(
            "left", self.current_parameter["name"], self.current_parameter["unit"]
        )


class LocationTimeseriesTable(QTableView):

    hoverExitRow = pyqtSignal(int)
    hoverExitAllRows = pyqtSignal()  # exit the whole widget
    hoverEnterRow = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QTreeView::item:hover{background-color:#FFFF00;}")
        self.setMouseTracking(True)
        self.verticalHeader().hide()
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.model = None

        self._last_hovered_row = None
        self.viewport().installEventFilter(self)

    def on_close(self):
        """
        unloading widget and remove all required stuff
        :return:
        """
        self.setMouseTracking(False)
        self.viewport().removeEventFilter(self)

    def closeEvent(self, event):
        """
        overwrite of QDockWidget class to emit signal
        :param event: QEvent
        """
        self.on_close()
        event.accept()

    def eventFilter(self, widget, event):
        if widget is self.viewport():

            if event.type() == QEvent.MouseMove:
                row = self.indexAt(event.pos()).row()
                if row == 0 and self.model and row > self.model.rowCount():
                    row = None

            elif event.type() == QEvent.Leave:
                row = None
                self.hoverExitAllRows.emit()
            else:
                row = self._last_hovered_row

            if row != self._last_hovered_row:
                if self._last_hovered_row is not None:
                    try:
                        self.hover_exit(self._last_hovered_row)
                    except IndexError:
                        logger.warning(
                            "Hover row index %s out of range" % self._last_hovered_row
                        )
                    # self.hoverExitRow.emit(self._last_hovered_row)
                # self.hoverEnterRow.emit(row)
                if row is not None:
                    try:
                        self.hover_enter(row)
                    except IndexError:
                        logger.warning("Hover row index %s out of range" % row)
                self._last_hovered_row = row
                pass
        return QTableView.eventFilter(self, widget, event)

    def hover_exit(self, row_nr):
        if row_nr >= 0:
            item = self.model.rows[row_nr]
            item.hover.value = False

    def hover_enter(self, row_nr):
        if row_nr >= 0:
            item = self.model.rows[row_nr]
            obj_id = item.object_id.value
            obj_type = item.object_type.value
            self.hoverEnterRow.emit(obj_id, obj_type)
            item.hover.value = True

    def setModel(self, model):
        super().setModel(model)
        self.model = model
        # https://stackoverflow.com/questions/3433664/how-to-make-sure-
        # columns-in-qtableview-are-resized-to-the-maximum
        self.setVisible(False)
        self.resizeColumnsToContents()
        self.setVisible(True)
        self.model.set_column_sizes_on_view(self)
        # first two columns (checkbox, color) can be set small always
        self.setColumnWidth(0, 20)  # checkbox
        self.setColumnWidth(1, 20)  # color field
        # 3rd column (id) can be wide (in case of high id)
        # 4th column (name) can be wide (e.g. '2d_groundwater')


class GraphWidget(QWidget):
    def __init__(
        self,
        parent=None,
        model: ThreeDiPluginModel = None,
        parameter_config=[],
        name="",
        geometry_type=QgsWkbTypes.Point,
    ):
        super().__init__(parent)

        self.name = name
        self.model = model
        self.parent = parent
        self.geometry_type = geometry_type

        self.setup_ui()

        self.location_model = LocationTimeseriesModel(self.model)
        self.graph_plot.set_location_model(self.location_model)
        self.graph_plot.set_result_model(self.model)
        self.location_timeseries_table.setModel(self.location_model)

        # set listeners
        self.parameter_combo_box.currentIndexChanged.connect(self.parameter_change)
        self.ts_units_combo_box.currentIndexChanged.connect(self.time_units_change)
        self.remove_timeseries_button.clicked.connect(self.remove_objects_table)
        self.model.result_removed.connect(self.result_removed)

        # init parameter selection
        self.set_parameter_list(parameter_config)

        self.marker = QgsRubberBand(self.parent.iface.mapCanvas())
        self.marker.setColor(Qt.red)
        self.marker.setWidth(2)

    @pyqtSlot(ThreeDiResultItem)
    def result_removed(self, result_item: ThreeDiResultItem):
        # Remove corresponding plots that refer to this item
        item_idx_to_remove = []
        for count, item in enumerate(self.location_model.rows):
            if item.result.value is result_item:
                item_idx_to_remove.append(count)

        for item_idx in item_idx_to_remove:
            self.location_model.removeRows(item_idx, 1)

    def set_parameter_list(self, parameter_config):

        # reset
        nr_old_parameters = self.parameter_combo_box.count()

        self.parameters = dict([(p["name"], p) for p in parameter_config])

        self.parameter_combo_box.insertItems(0, [p["name"] for p in parameter_config])

        # todo: find best matching parameter based on previous selection
        if nr_old_parameters > 0:
            self.parameter_combo_box.setCurrentIndex(0)

        nr_parameters_tot = self.parameter_combo_box.count()
        for i in reversed(
            list(range(nr_parameters_tot - nr_old_parameters, nr_parameters_tot))
        ):
            self.parameter_combo_box.removeItem(i)

        # self.graph_plot.set_parameter(self.current_parameter)

    def on_close(self):
        """
        unloading widget and remove all required stuff
        :return:
        """
        self.parameter_combo_box.currentIndexChanged.disconnect(self.parameter_change)
        self.remove_timeseries_button.clicked.disconnect(self.remove_objects_table)

    def closeEvent(self, event):
        """
        overwrite of QDockWidget class to emit signal
        :param event: QEvent
        """
        self.on_close()
        event.accept()

    def highlight_feature(self, obj_id, obj_type):

        layers = self.parent.iface.mapCanvas().layers()
        for lyr in layers:
            # Clear other layers
            # lyr.removeSelection()
            if lyr.objectName() == obj_type:
                # query layer for object
                filt = u'"id" = {0}'.format(obj_id)
                request = QgsFeatureRequest().setFilterExpression(filt)
                features = lyr.getFeatures(request)
                for feature in features:
                    self.marker.setToGeometry(feature.geometry(), lyr)

    def unhighlight_all_features(self):
        """Remove the highlights from all layers"""
        self.marker.reset()

    def setup_ui(self):
        """
        Create Qt widgets and elements
        """

        self.setObjectName(self.name)
        self.hLayout = QHBoxLayout(self)
        self.hLayout.setObjectName("hLayout")

        # add combobox for time units selection
        self.ts_units_combo_box = QComboBox(self)
        self.ts_units_combo_box.insertItems(0, ["hrs", "mins", "s"])

        # add graphplot
        self.graph_plot = GraphPlot(self)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.graph_plot.sizePolicy().hasHeightForWidth())
        self.graph_plot.setSizePolicy(sizePolicy)
        self.graph_plot.setMinimumSize(QSize(250, 250))
        self.hLayout.addWidget(self.graph_plot)

        # add layout for timeseries table and other controls
        self.vLayoutTable = QVBoxLayout(self)
        self.hLayout.addLayout(self.vLayoutTable)

        # add combobox for parameter selection
        self.parameter_combo_box = QComboBox(self)
        self.vLayoutTable.addWidget(self.parameter_combo_box)
        self.vLayoutTable.addWidget(self.ts_units_combo_box)

        # add timeseries table
        self.location_timeseries_table = LocationTimeseriesTable(self)
        self.location_timeseries_table.hoverEnterRow.connect(self.highlight_feature)
        self.location_timeseries_table.hoverExitAllRows.connect(
            self.unhighlight_all_features
        )
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.location_timeseries_table.sizePolicy().hasHeightForWidth()
        )
        self.location_timeseries_table.setSizePolicy(sizePolicy)
        self.location_timeseries_table.setMinimumSize(QSize(250, 0))
        self.vLayoutTable.addWidget(self.location_timeseries_table)

        # add buttons below table
        self.hLayoutButtons = QHBoxLayout(self)
        self.vLayoutTable.addLayout(self.hLayoutButtons)

        self.remove_timeseries_button = QPushButton(self)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.remove_timeseries_button.sizePolicy().hasHeightForWidth()
        )
        self.remove_timeseries_button.setSizePolicy(sizePolicy)
        self.remove_timeseries_button.setObjectName("remove_timeseries_button")
        self.hLayoutButtons.addWidget(self.remove_timeseries_button)
        self.hLayoutButtons.addItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )
        self.remove_timeseries_button.setText("Delete")

    def parameter_change(self, nr):
        """
        set current selected parameter and trigger refresh of graphs
        :param nr: nr of selected option of combobox
        :return:
        """
        self.current_parameter = self.parameters[self.parameter_combo_box.currentText()]
        time_units = self.ts_units_combo_box.currentText()
        self.graph_plot.setLabel("bottom", "Time", time_units)
        self.graph_plot.set_parameter(self.current_parameter, time_units)
        self.graph_plot.plotItem.vb.menu.viewAll.triggered.emit()

    def time_units_change(self):
        parameter_idx = self.parameter_combo_box.currentIndex()
        self.parameter_change(parameter_idx)

    def get_feature_index(self, layer, feature):
        """
        get the id of the selected id feature
        :param layer: selected Qgis layer to be added
        :param feature: selected Qgis feature to be added
        :return: idx (integer)
        We can't do ``feature.id()``, so we have to pick something that we
        have agreed on. For now we have hardcoded the 'id' field as the
        default, but that doesn't mean it's always the case in the future
        when more layers are added!
        """
        idx = feature.id()
        if layer.dataProvider().name() in PROVIDERS_WITHOUT_PRIMARY_KEY:
            idx = feature["id"]
        return idx

    def get_object_name(self, layer, feature):
        """
        get the object_name (display_name / type)  of the selected id feature
        :param layer: selected Qgis layer to be added
        :param feature: selected Qgis feature to be added
        :return: object_name (string)
        To get a object_name we use the following logic:
        - get the 'display_name' column if available;
        - if not: get the 'type' column if available;
        - if not: get the 'line_type' column if available;
        - if not: get the 'node_type' column if available;
        - if not: object_name = 'N/A'
        """
        for column_nr, field in enumerate(layer.fields()):
            if "display_name" in field.name():
                return feature[column_nr]
        for column_nr, field in enumerate(layer.fields()):
            if field.name() == "type":
                return feature[column_nr]

        # Apply ValueMap field formatter
        for column_nr, field in enumerate(layer.fields()):
            if field.name() == "line_type":
                config = layer.editorWidgetSetup(column_nr).config()
                return QgsValueMapFieldFormatter().representValue(layer, column_nr, config, None, feature[column_nr])
        for column_nr, field in enumerate(layer.fields()):
            if field.name() == "node_type":
                config = layer.editorWidgetSetup(column_nr).config()
                return QgsValueMapFieldFormatter().representValue(layer, column_nr, config, None, feature[column_nr])

        logger.warning("Layer has no 'display_name', it's probably a result "
                       "layer, but putting a placeholder object name just "
                       "for safety."
                       )

        return "N/A"

    def add_objects(self, layer: QgsVectorLayer, features: List[QgsFeature]) -> bool:
        """
        :param layer: layer of features
        :param features: Qgis layer features to be added
        :return: boolean: new objects are added
        """

        if not is_threedi_layer(layer):
            msg = """Please select results from either the 'flowlines', 'nodes' or
            'pumplines' layer."""
            messagebar_message(TOOLBOX_MESSAGE_TITLE, msg, Qgis.Warning, 5.0)
            return

        # Retrieve existing items
        existing_items = [
            "%s_%s" % (item.object_type.value, str(item.object_id.value))
            for item in self.location_model.rows
        ]

        # Determine new items
        new_items = []
        for feature in features:
            new_idx = self.get_feature_index(layer, feature)
            new_object_name = self.get_object_name(layer, feature)

            result_items = self.model.get_results(selected=False)
            for result_item in result_items:
                if (layer.objectName() + "_" + str(new_idx)) not in existing_items:
                    item = {
                        "object_type": layer.objectName(),
                        "object_id": new_idx,
                        "object_name": new_object_name,
                        "result": result_item,
                    }
                    new_items.append(item)

        if len(new_items) > 20:
            msg = (
                "%i new objects selected. Adding those to the plot can "
                "take a while. Do you want to continue?" % len(new_items)
            )
            reply = QMessageBox.question(
                self, "Add objects", msg, QMessageBox.Yes, QMessageBox.No
            )

            if reply == QMessageBox.No:
                return False

        self.location_model.insertRows(new_items)
        msg = "%i new objects added to plot " % len(new_items)
        skipped_items = len(features) - len(new_items)
        if skipped_items > 0:
            msg += "(skipped %s already present objects)" % skipped_items

        statusbar_message(msg)
        return True

    def remove_objects_table(self):
        """
        removes selected objects from table
        :return:
        """
        selection_model = self.location_timeseries_table.selectionModel()
        # get unique rows in selected fields
        rows = set([index.row() for index in selection_model.selectedIndexes()])
        for row in reversed(sorted(rows)):
            self.location_model.removeRows(row, 1)


class GraphDockWidget(QDockWidget):
    """Main Dock Widget for showing 3Di results in Graphs"""

    closingWidget = pyqtSignal(int)

    def __init__(self, iface, nr, model: ThreeDiPluginModel):
        super().__init__()

        self.iface = iface
        self.nr = nr
        self.model = model

        self.setup_ui()

        parameter_config = self._get_active_parameter_config()

        # add graph widgets
        self.q_graph_widget = GraphWidget(
            self,
            self.model,
            parameter_config["q"],
            "Flowlines && pumps",
            QgsWkbTypes.LineString,
        )
        self.h_graph_widget = GraphWidget(
            self,
            self.model,
            parameter_config["h"],
            "Nodes",
            QgsWkbTypes.Point,
        )
        self.graphTabWidget.addTab(self.q_graph_widget, self.q_graph_widget.name)
        self.graphTabWidget.addTab(self.h_graph_widget, self.h_graph_widget.name)

        # add listeners
        self.addSelectedObjectButton.clicked.connect(self.add_objects)
        self.addFlowlinePumpButton.clicked.connect(self.add_flow_line_pump_button_clicked)
        self.addNodeButton.clicked.connect(self.add_node_button_clicked)

        # init current layer state and add listener
        self.selected_layer_changed(self.iface.mapCanvas().currentLayer)
        self.iface.currentLayerChanged.connect(self.selected_layer_changed)

        # add map tools
        self.add_flow_line_pump_button_map_tool = AddFlowlinePumpMapTool(canvas=self.iface.mapCanvas())
        self.add_flow_line_pump_button_map_tool.setButton(self.addFlowlinePumpButton)
        self.add_flow_line_pump_button_map_tool.setCursor(Qt.CrossCursor)
        self.add_node_button_map_tool = AddNodeMapTool(canvas=self.iface.mapCanvas())
        self.add_node_button_map_tool.setButton(self.addNodeButton)
        self.add_node_button_map_tool.setCursor(Qt.CrossCursor)

    def on_close(self):
        """
        unloading widget and remove all required stuff
        :return:
        """
        self.addSelectedObjectButton.clicked.disconnect(self.add_objects)
        self.iface.currentLayerChanged.disconnect(self.selected_layer_changed)
        # self.q_graph_widget.close()
        # self.h_graph_widget.close()

    def closeEvent(self, event):
        """
        overwrite of QDockWidget class to emit signal
        :param event: QEvent
        """
        self.on_close()
        self.closingWidget.emit(self.nr)
        event.accept()

    def _get_active_parameter_config(self):

        results = self.model.get_results(selected=True)

        if results:
            threedi_result = self.model.get_results(selected=True)[0].threedi_result  # TODO: ACTIVE
            available_subgrid_vars = threedi_result.available_subgrid_map_vars
            available_agg_vars = threedi_result.available_aggregation_vars
            if not available_agg_vars:
                messagebar_message(
                    "Warning", "No aggregation netCDF was found.", level=1, duration=5
                )
            parameter_config = generate_parameter_config(
                available_subgrid_vars, available_agg_vars
            )
        else:
            parameter_config = {"q": [], "h": []}

        return parameter_config

    def on_result_selection_change(self):

        parameter_config = self._get_active_parameter_config()
        self.q_graph_widget.set_parameter_list(parameter_config["q"])
        self.h_graph_widget.set_parameter_list(parameter_config["h"])

    def selected_layer_changed(self, active_layer: QgsMapLayer):
        # get active layer from canvas, instead of using active_layer.
        # Otherwise .dataProvider doesn't work
        current_layer = self.iface.mapCanvas().currentLayer()

        # Activate button if 3Di layers found
        self.addSelectedObjectButton.setEnabled(is_threedi_layer(current_layer))

    def add_objects(self):
        """
        Adds the currently selected layer to the node or flowline graph (checks names
        to determine which plot)
        """
        canvas = self.iface.mapCanvas()
        current_layer = canvas.currentLayer()
        if not current_layer:
            messagebar_message(TOOLBOX_MESSAGE_TITLE, "Please select a 3Di layer before adding a plot", Qgis.Warning, 5.0)
            return

        provider = current_layer.dataProvider()
        if provider.name() not in VALID_PROVIDERS:
            logger.error("Unsupported provider for adding graph plot")
            return

        if current_layer.name() not in list(LAYER_QH_TYPE_MAPPING.keys()):
            if not is_threedi_layer(current_layer):
                messagebar_message(TOOLBOX_MESSAGE_TITLE, "Please select a 3Di layer before adding a plot", Qgis.Warning, 5.0)
                return

        selected_features = current_layer.selectedFeatures()

        if current_layer.name() == "flowlines" or current_layer.objectName() == "flowline":
            self.q_graph_widget.add_objects(current_layer, selected_features)
            self.graphTabWidget.setCurrentIndex(
                self.graphTabWidget.indexOf(self.q_graph_widget)
            )
            self.q_graph_widget.graph_plot.plotItem.vb.menu.viewAll.triggered.emit()
            return
        elif current_layer.name() == "nodes" or current_layer.objectName() == "node":
            self.h_graph_widget.add_objects(current_layer, selected_features)
            self.graphTabWidget.setCurrentIndex(
                self.graphTabWidget.indexOf(self.h_graph_widget)
            )
            self.h_graph_widget.graph_plot.plotItem.vb.menu.viewAll.triggered.emit()
            return

        if LAYER_QH_TYPE_MAPPING[current_layer.name()] == "q":
            self.q_graph_widget.add_objects(current_layer, selected_features)
            self.graphTabWidget.setCurrentIndex(
                self.graphTabWidget.indexOf(self.q_graph_widget)
            )
            self.q_graph_widget.graph_plot.plotItem.vb.menu.viewAll.triggered.emit()
        else:
            self.h_graph_widget.add_objects(current_layer, selected_features)
            self.graphTabWidget.setCurrentIndex(
                self.graphTabWidget.indexOf(self.h_graph_widget)
            )
            self.h_graph_widget.graph_plot.plotItem.vb.menu.viewAll.triggered.emit()

    def on_btnAbsoluteState(self, state):
        """Toggle ``absolute`` state of the GraphPlots."""
        checked = state == Qt.Checked
        self.q_graph_widget.graph_plot.absolute = (
            self.h_graph_widget.graph_plot.absolute
        ) = checked

    def setup_ui(self):

        self.setObjectName("dock_widget")
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.dockWidgetContent = QWidget(self)
        self.dockWidgetContent.setObjectName("dockWidgetContent")

        self.mainVLayout = QVBoxLayout(self.dockWidgetContent)
        self.dockWidgetContent.setLayout(self.mainVLayout)

        self.buttonBarHLayout = QHBoxLayout(self)

        # add button to add objects to graphs
        self.addSelectedObjectButton = QPushButton(self.dockWidgetContent)
        self.addSelectedObjectButton.setObjectName("addSelectedObjectButton")
        self.absoluteCheckbox = QCheckBox("Absolute", parent=self.dockWidgetContent)
        self.absoluteCheckbox.setChecked(False)
        self.absoluteCheckbox.stateChanged.connect(self.on_btnAbsoluteState)
        self.buttonBarHLayout.addWidget(self.addSelectedObjectButton)
        self.buttonBarHLayout.addWidget(self.absoluteCheckbox)
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.buttonBarHLayout.addItem(spacerItem)
        self.mainVLayout.addItem(self.buttonBarHLayout)

        # add buttons for maptools to select objects for graphs
        self.addFlowlinePumpButton = QPushButton(text="Add flowlines/pumps", parent=self.dockWidgetContent)
        # self.addFlowlinePumpButton.setObjectName("addFlowlinePumpButton")
        self.addFlowlinePumpButton.setCheckable(True)
        self.buttonBarHLayout.addWidget(self.addFlowlinePumpButton)
        self.addNodeButton = QPushButton(text="Add nodes", parent=self.dockWidgetContent)
        # self.addNodeButton.setObjectName("addNodeButton")
        self.addNodeButton.setCheckable(True)
        self.buttonBarHLayout.addWidget(self.addNodeButton)

        # add tabWidget for graphWidgets
        self.graphTabWidget = QTabWidget(self.dockWidgetContent)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(6)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.graphTabWidget.sizePolicy().hasHeightForWidth()
        )
        self.graphTabWidget.setSizePolicy(sizePolicy)
        self.graphTabWidget.setObjectName("graphTabWidget")
        self.mainVLayout.addWidget(self.graphTabWidget)

        # add dockwidget
        self.setWidget(self.dockWidgetContent)
        self.setWindowTitle("3Di Result Plots %i" % self.nr)
        self.addSelectedObjectButton.setText("Add")
        QMetaObject.connectSlotsByName(self)

    def add_flow_line_pump_button_clicked(self):
        self.iface.mapCanvas().setMapTool(
            self.add_flow_line_pump_button_map_tool,
        )

    def add_node_button_clicked(self):
        self.iface.mapCanvas().setMapTool(
            self.add_node_button_map_tool,
        )


class BaseAddMapTool(QgsMapToolIdentify):

    def canvasReleaseEvent(self, event):
        x = event.pos().x()
        y = event.pos().y()
        feature_id = self.identify(x=int(x), y=int(y))[0].mFeature.id()
        print(self, feature_id)


class AddFlowlinePumpMapTool(BaseAddMapTool):
    pass


class AddNodeMapTool(BaseAddMapTool):
    pass
