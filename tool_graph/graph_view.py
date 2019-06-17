from qgis.core import QgsCoordinateReferenceSystem
from qgis.core import QgsCoordinateTransform
from qgis.core import QgsDataSourceUri
from qgis.core import QgsFeatureRequest
from qgis.core import QgsProject
from qgis.core import QgsWkbTypes
from qgis.gui import QgsRubberBand
from qgis.gui import QgsVertexMarker
from qgis.PyQt.QtCore import pyqtSignal
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
from qgis.PyQt.QtWidgets import QTabWidget
from qgis.PyQt.QtWidgets import QVBoxLayout
from qgis.PyQt.QtWidgets import QWidget
from ThreeDiToolbox.datasource.result_constants import LAYER_QH_TYPE_MAPPING
from ThreeDiToolbox.datasource.threedi_results import normalized_object_type
from ThreeDiToolbox.tool_graph.graph_model import LocationTimeseriesModel
from ThreeDiToolbox.utils.user_messages import messagebar_message
from ThreeDiToolbox.utils.user_messages import statusbar_message
from ThreeDiToolbox.utils.utils import generate_parameter_config

import logging
import pyqtgraph as pg


logger = logging.getLogger(__name__)

pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")

# Layer providers that we can use for the graph
VALID_PROVIDERS = ["spatialite", "memory", "ogr"]
# providers which don't have a primary key
PROVIDERS_WITHOUT_PRIMARY_KEY = ["memory", "ogr"]


class GraphPlot(pg.PlotWidget):
    """Graph element"""

    def __init__(self, parent=None):
        """

        :param parent: Qt parent widget
        """

        super().__init__(parent)

        self.showGrid(True, True, 0.5)
        self.setLabel("bottom", "Time", "s")

        self.current_parameter = None
        self.location_model = None
        self.datasource_model = None
        self.parent = parent
        self.absolute = False
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

        if self.ds_model:
            self.ds_model.dataChanged.disconnect(self.ds_data_changed)
            self.ds_model.rowsInserted.disconnect(self.on_insert_ds)
            self.ds_model.rowsAboutToBeRemoved.disconnect(self.on_remove_ds)
            self.ds_model = None

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

    def set_ds_model(self, model):

        self.ds_model = model
        self.ds_model.dataChanged.connect(self.ds_data_changed)
        self.ds_model.rowsInserted.connect(self.on_insert_ds)
        self.ds_model.rowsAboutToBeRemoved.connect(self.on_remove_ds)

    def on_insert_ds(self, parent, start, end):
        """
        add list of items to graph. based on Qt addRows model trigger
        :param parent: parent of event (Qt parameter)
        :param start: first row nr
        :param end: last row nr
        """
        for i in range(start, end + 1):
            ds = self.ds_model.rows[i]
            if ds.active.value:
                for item in self.location_model.rows:
                    if item.active.value:
                        self.addItem(
                            item.plots(
                                self.current_parameter["parameters"],
                                i,
                                absolute=self.absolute,
                            )
                        )

    def on_remove_ds(self, index, start, end):
        """
        remove items from graph. based on Qt model removeRows
        trigger
        :param index: Qt Index (not used)
        :param start: first row nr
        :param end: last row nr
        """
        for i in range(start, end + 1):
            ds = self.ds_model.rows[i]
            if ds.active.value:
                for item in self.location_model.rows:
                    if item.active.value:
                        self.removeItem(
                            item.plots(self.current_parameter["parameters"], i)
                        )

    def ds_data_changed(self, index):
        """
        change graphs based on changes in locations. based on Qt
        data change trigger
        :param index: index of changed field
        """
        if self.ds_model.columns[index.column()].name == "active":

            for i in range(0, len(self.location_model.rows)):
                if self.location_model.rows[i].active.value:
                    if self.ds_model.rows[index.row()].active.value:
                        self.show_timeseries(i, index.row())
                    else:
                        self.hide_timeseries(i, index.row())

    def on_insert_locations(self, parent, start, end):
        """
        add list of items to graph. based on Qt addRows model trigger
        :param parent: parent of event (Qt parameter)
        :param start: first row nr
        :param end: last row nr
        """
        for i in range(start, end + 1):
            item = self.location_model.rows[i]
            for ds in self.ds_model.rows:
                if ds.active.value:
                    index = self.ds_model.rows.index(ds)
                    self.addItem(
                        item.plots(
                            self.current_parameter["parameters"],
                            index,
                            absolute=self.absolute,
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
        for i in range(start, end + 1):
            item = self.location_model.rows[i]
            if item.active.value:
                for ds in self.ds_model.rows:
                    if ds.active.value:
                        index = self.ds_model.rows.index(ds)
                        self.removeItem(
                            item.plots(self.current_parameter["parameters"], index)
                        )

    def location_data_changed(self, index):
        """
        change graphs based on changes in locations
        :param index: index of changed field
        """
        if self.location_model.columns[index.column()].name == "active":

            for i in range(0, len(self.ds_model.rows)):
                if self.ds_model.rows[i].active.value:
                    if self.location_model.rows[index.row()].active.value:
                        self.show_timeseries(index.row(), i)
                    else:
                        self.hide_timeseries(index.row(), i)

        elif self.location_model.columns[index.column()].name == "hover":
            item = self.location_model.rows[index.row()]
            if item.hover.value:
                for ds in self.ds_model.rows:
                    if ds.active.value:
                        index = self.ds_model.rows.index(ds)
                        item.plots(self.current_parameter["parameters"], index).setPen(
                            color=item.color.qvalue, width=5, style=ds.pattern.value
                        )
            else:
                for ds in self.ds_model.rows:
                    if ds.active.value:
                        index = self.ds_model.rows.index(ds)
                        item.plots(self.current_parameter["parameters"], index).setPen(
                            color=item.color.qvalue, width=2, style=ds.pattern.value
                        )

    def hide_timeseries(self, location_nr, ds_nr):
        """
        hide timeseries of location in graph
        :param row_nr: integer, row number of location
        """

        plot = self.location_model.rows[location_nr].plots(
            self.current_parameter["parameters"], ds_nr
        )
        self.removeItem(plot)

    def show_timeseries(self, location_nr, ds_nr):
        """
        show timeseries of location in graph
        :param row_nr: integer, row number of location
        """

        plot = self.location_model.rows[location_nr].plots(
            self.current_parameter["parameters"], ds_nr
        )
        self.addItem(plot)

    def set_parameter(self, parameter):
        """
        on selection of parameter (in combobox), change timeseries in graphs
        :param parameter: parameter indentification string
        """

        if self.current_parameter == parameter:
            return

        old_parameter = self.current_parameter
        self.current_parameter = parameter

        for item in self.location_model.rows:
            if item.active.value:
                for ds in self.ds_model.rows:
                    if ds.active.value:
                        index = self.ds_model.rows.index(ds)

                        self.removeItem(item.plots(old_parameter["parameters"], index))
                        self.addItem(
                            item.plots(self.current_parameter["parameters"], index)
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
        ts_datasources=None,
        parameter_config=[],
        name="",
        geometry_type=QgsWkbTypes.Point,
    ):
        super().__init__(parent)

        self.name = name
        self.ts_datasources = ts_datasources
        self.parent = parent
        self.geometry_type = geometry_type

        self.setup_ui()

        self.model = LocationTimeseriesModel(ts_datasources=self.ts_datasources)
        self.graph_plot.set_location_model(self.model)
        self.graph_plot.set_ds_model(self.ts_datasources)
        self.location_timeseries_table.setModel(self.model)

        # set listeners
        self.parameter_combo_box.currentIndexChanged.connect(self.parameter_change)
        self.remove_timeseries_button.clicked.connect(self.remove_objects_table)

        # init parameter selection
        self.set_parameter_list(parameter_config)

        if self.geometry_type == QgsWkbTypes.Point:
            self.marker = QgsVertexMarker(self.parent.iface.mapCanvas())
        else:
            self.marker = QgsRubberBand(self.parent.iface.mapCanvas())
            self.marker.setColor(Qt.red)
            self.marker.setWidth(2)

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

        pass
        # todo: selection generated errors and crash of Qgis. Implement method
        # with QgsRubberband and/ or QgsVertexMarker
        transform = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem(4326),
            QgsProject.instance().crs(),
            QgsProject.instance(),
        )

        layers = self.parent.iface.mapCanvas().layers()
        for lyr in layers:
            # Clear other layers
            # lyr.removeSelection()
            if lyr.name() == obj_type:
                # query layer for object
                filt = u'"id" = {0}'.format(obj_id)
                request = QgsFeatureRequest().setFilterExpression(filt)
                features = lyr.getFeatures(request)
                for feature in features:
                    if self.geometry_type == QgsWkbTypes.Point:
                        geom = feature.geometry()
                        geom.transform(transform)
                        self.marker.setCenter(geom.asPoint())
                        self.marker.setVisible(True)
                    else:
                        self.marker.setToGeometry(feature.geometry(), lyr)

    def unhighlight_all_features(self):
        """Remove the highlights from all layers"""

        if self.geometry_type == QgsWkbTypes.Point:
            self.marker.setVisible(False)
        else:
            self.marker.reset()
        pass
        # todo: selection generated errors and crash of Qgis. Implement method
        # with QgsRubberband and/ or QgsVertexMarker

    def setup_ui(self):
        """
        Create Qt widgets and elements
        """

        self.setObjectName(self.name)

        self.hLayout = QHBoxLayout(self)
        self.hLayout.setObjectName("hLayout")

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

        self.retranslateUi()

    def retranslateUi(self):
        """
        set translated widget text
        """
        self.remove_timeseries_button.setText("Delete")

    def parameter_change(self, nr):
        """
        set current selected parameter and trigger refresh of graphs
        :param nr: nr of selected option of combobox
        :return:
        """
        self.current_parameter = self.parameters[self.parameter_combo_box.currentText()]
        self.graph_plot.set_parameter(self.current_parameter)

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
        - get the '*display_name*' column if available;
        - if not: get the 'type' column if available;
        - if not: object_name = 'N/A'
        """
        object_name = None
        for column_nr, field in enumerate(layer.fields()):
            if "display_name" in field.name():
                object_name = feature[column_nr]
        if object_name is None:
            for column_nr, field in enumerate(layer.fields()):
                if field.name() == "type":
                    object_name = feature[column_nr]
                    break
                else:
                    object_name = "N/A"
                    logger.warning(
                        "Layer has no 'display_name', it's probably a result "
                        "layer, but putting a placeholder object name just "
                        "for safety."
                    )
        return object_name

    def get_new_items(self, layer, features, filename, existing_items):
        """
        get a list of new items (that have been selected by user) to be added
        to graph (if they do not already exist in the graph items
        :param layer: selected Qgis layer to be added
        :param features: selected Qgis features to be added
        :param filename: selected Qgis features to be added
        :param existing_items: selected Qgis features to be added
        :return: new_items (list)
        """
        new_items = []
        for feature in features:
            new_idx = self.get_feature_index(layer, feature)
            new_object_name = self.get_object_name(layer, feature)
            # check if object not already exist
            if (layer.name() + "_" + str(new_idx)) not in existing_items:
                item = {
                    "object_type": layer.name(),
                    "object_id": new_idx,
                    "object_name": new_object_name,
                    "file_path": filename,
                }
                new_items.append(item)
        return new_items

    def add_objects(self, layer, features):
        """
        :param layer: layer of features
        :param features: Qgis layer features to be added
        :return: boolean: new objects are added
        """

        # Get the active database as URI, conn_info is something like:
        # u"dbname='/home/jackieleng/git/threedi-turtle/var/models/
        # DS_152_1D_totaal_bergingsbak/results/
        # DS_152_1D_totaal_bergingsbak_result.sqlite'"
        conn_info = QgsDataSourceUri(
            layer.dataProvider().dataSourceUri()
        ).connectionInfo()
        try:
            filename = conn_info.split("'")[1]
        except IndexError:
            raise RuntimeError(
                "Active database (%s) doesn't look like an sqlite filename" % conn_info
            )

        # get attribute information from selected layers
        existing_items = [
            "%s_%s" % (item.object_type.value, str(item.object_id.value))
            for item in self.model.rows
        ]
        items = self.get_new_items(layer, features, filename, existing_items)

        if len(items) > 20:
            msg = (
                "%i new objects selected. Adding those to the plot can "
                "take a while. Do you want to continue?" % len(items)
            )
            reply = QMessageBox.question(
                self, "Add objects", msg, QMessageBox.Yes, QMessageBox.No
            )

            if reply == QMessageBox.No:
                return False

        self.model.insertRows(items)
        msg = "%i new objects added to plot " % len(items)
        skipped_items = len(features) - len(items)
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
            self.model.removeRows(row, 1)


class GraphDockWidget(QDockWidget):
    """Main Dock Widget for showing 3Di results in Graphs"""

    closingWidget = pyqtSignal(int)

    def __init__(
        self,
        iface,
        parent_widget=None,
        parent_class=None,
        nr=0,
        ts_datasources=None,
        root_tool=None,
    ):
        """Constructor"""
        super().__init__(parent_widget)

        self.iface = iface
        self.parent_class = parent_class
        self.nr = nr
        self.ts_datasources = ts_datasources
        self.root_tool = root_tool

        self.setup_ui(self)

        parameter_config = self._get_active_parameter_config()

        # add graph widgets
        self.q_graph_widget = GraphWidget(
            self,
            self.ts_datasources,
            parameter_config["q"],
            "Q graph",
            QgsWkbTypes.LineString,
        )
        self.h_graph_widget = GraphWidget(
            self,
            self.ts_datasources,
            parameter_config["h"],
            "H graph",
            QgsWkbTypes.Point,
        )
        self.graphTabWidget.addTab(self.q_graph_widget, self.q_graph_widget.name)
        self.graphTabWidget.addTab(self.h_graph_widget, self.h_graph_widget.name)

        # add listeners
        self.addSelectedObjectButton.clicked.connect(self.add_objects)
        # init current layer state and add listener
        self.selected_layer_changed(self.iface.mapCanvas().currentLayer)
        self.iface.currentLayerChanged.connect(self.selected_layer_changed)
        self.root_tool.timeslider_widget.datasource_changed.connect(
            self.on_active_ts_datasource_change
        )

    def on_close(self):
        """
        unloading widget and remove all required stuff
        :return:
        """
        self.addSelectedObjectButton.clicked.disconnect(self.add_objects)
        self.iface.currentLayerChanged.disconnect(self.selected_layer_changed)
        self.root_tool.timeslider_widget.datasource_changed.disconnect(
            self.on_active_ts_datasource_change
        )

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

        active_ts_datasource = self.root_tool.timeslider_widget.active_ts_datasource

        if active_ts_datasource is not None:
            # TODO: just taking the first datasource, not sure if correct:
            threedi_result = active_ts_datasource.threedi_result()
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
            parameter_config = {"q": {}, "h": {}}

        return parameter_config

    def on_active_ts_datasource_change(self):

        parameter_config = self._get_active_parameter_config()
        self.q_graph_widget.set_parameter_list(parameter_config["q"])
        self.h_graph_widget.set_parameter_list(parameter_config["h"])

    def selected_layer_changed(self, active_layer):

        tdi_layer = False

        # get active layer from canvas, otherwise .dataProvider doesn't work
        canvas = self.iface.mapCanvas()
        current_layer = canvas.currentLayer()

        if current_layer:
            provider = current_layer.dataProvider()
            valid_object_type = normalized_object_type(current_layer.name())

            if provider.name() in VALID_PROVIDERS and valid_object_type:
                tdi_layer = True
            elif current_layer.name() in ("flowlines", "nodes"):
                tdi_layer = True

        # activate button if 3Di layers found
        self.addSelectedObjectButton.setEnabled(tdi_layer)

    def add_objects(self):
        canvas = self.iface.mapCanvas()
        current_layer = canvas.currentLayer()
        if not current_layer:
            # todo: feedback select layer first
            return

        provider = current_layer.dataProvider()
        if provider.name() not in VALID_PROVIDERS:
            return

        if current_layer.name() not in list(LAYER_QH_TYPE_MAPPING.keys()):
            if current_layer.name() not in ("flowlines", "nodes"):
                # todo: feedback layer not supported
                return

        selected_features = current_layer.selectedFeatures()

        if current_layer.name() == "flowlines":
            self.q_graph_widget.add_objects(current_layer, selected_features)
            self.graphTabWidget.setCurrentIndex(
                self.graphTabWidget.indexOf(self.q_graph_widget)
            )
            return
        elif current_layer.name() == "nodes":
            self.h_graph_widget.add_objects(current_layer, selected_features)
            self.graphTabWidget.setCurrentIndex(
                self.graphTabWidget.indexOf(self.h_graph_widget)
            )
            return

        if LAYER_QH_TYPE_MAPPING[current_layer.name()] == "q":
            self.q_graph_widget.add_objects(current_layer, selected_features)
            self.graphTabWidget.setCurrentIndex(
                self.graphTabWidget.indexOf(self.q_graph_widget)
            )
        else:
            self.h_graph_widget.add_objects(current_layer, selected_features)
            self.graphTabWidget.setCurrentIndex(
                self.graphTabWidget.indexOf(self.h_graph_widget)
            )

    def on_btnstate(self, state):
        """Toggle ``absolute`` state of the GraphPlots"""
        checked = state == Qt.Checked
        self.q_graph_widget.graph_plot.absolute = (
            self.h_graph_widget.graph_plot.absolute
        ) = checked

    def setup_ui(self, dock_widget):
        """
        initiate main Qt building blocks of interface
        :param dock_widget: QDockWidget instance
        """

        dock_widget.setObjectName("dock_widget")
        dock_widget.setAttribute(Qt.WA_DeleteOnClose)

        self.dockWidgetContent = QWidget(self)
        self.dockWidgetContent.setObjectName("dockWidgetContent")

        self.mainVLayout = QVBoxLayout(self.dockWidgetContent)
        self.dockWidgetContent.setLayout(self.mainVLayout)

        # add button to add objects to graphs
        self.buttonBarHLayout = QHBoxLayout(self)
        self.addSelectedObjectButton = QPushButton(self.dockWidgetContent)
        self.addSelectedObjectButton.setObjectName("addSelectedObjectButton")
        self.checkbox = QCheckBox("Absolute", parent=self.dockWidgetContent)
        self.checkbox.setChecked(False)
        self.checkbox.stateChanged.connect(self.on_btnstate)
        self.buttonBarHLayout.addWidget(self.addSelectedObjectButton)
        self.buttonBarHLayout.addWidget(self.checkbox)
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.buttonBarHLayout.addItem(spacerItem)
        self.mainVLayout.addItem(self.buttonBarHLayout)

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
        dock_widget.setWidget(self.dockWidgetContent)
        self.retranslate_ui(dock_widget)
        QMetaObject.connectSlotsByName(dock_widget)

    def retranslate_ui(self, DockWidget):
        DockWidget.setWindowTitle("3Di result plots %i" % self.nr)
        self.addSelectedObjectButton.setText("Add")
