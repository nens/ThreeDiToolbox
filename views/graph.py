# -*- coding: utf-8 -*-
import pyqtgraph as pg
from PyQt4.QtCore import Qt, QSize, QEvent, pyqtSignal, QMetaObject
from PyQt4.QtGui import (
    QTableView, QWidget, QVBoxLayout, QHBoxLayout,
    QSizePolicy, QPushButton, QSpacerItem, QApplication, QTabWidget,
    QDockWidget, QComboBox, QMessageBox, QCheckBox)

from qgis.core import (QgsDataSourceURI, QgsFeatureRequest, QGis,
                       QgsCoordinateTransform, QgsCoordinateReferenceSystem)
from qgis.gui import (QgsVertexMarker, QgsRubberBand)

from ..datasource.netcdf import (
    layer_qh_type_mapping, normalized_object_type)
from ..models.graph import LocationTimeseriesModel
from ..utils.user_messages import log, statusbar_message, messagebar_message
from ..datasource.netcdf import (
    SUBGRID_MAP_VARIABLES, Q_TYPES, H_TYPES, AGGREGATION_VARIABLES,
    )
from ..datasource.netcdf import (
    CUMULATIVE_AGGREGATION_UNITS)


def parse_aggvarname(aggvarname):
    """Parse a combined agg var name.

    >>> parse_aggvarname('s1_max')
    ('s1', 'max')
    >>> parse_aggvarname('s1_cum_negative')
    ('s1', 'cum_negative')
    >>> parse_aggvarname('infiltration_rate_cum_positive')
    ('infiltration_rate', 'cum_positive')
    """
    # Aggregation methods unfortunately can contain underscores; for now only
    # these two cases are known.
    # TODO: improve this, e.g., make more generic, because extra cases will
    # need to be added later
    if (aggvarname.endswith('cum_positive') or
            aggvarname.endswith('cum_negative')):
        varname, agg_method, sign = aggvarname.rsplit('_', 2)
        return varname, "_".join([agg_method, sign])

    # Works only for aggregation methods without underscores
    varname, agg_method = aggvarname.rsplit('_', 1)  # maxsplit = 1
    return varname, agg_method


def generate_parameter_config(subgrid_map_vars, agg_vars):
    """Dynamically create the parameter config.

    Args:
        subgrid_map_vars: available vars from subgrid_map.nc
        agg_vars: available vars from aggregation netCDF
    """
    subgrid_map_vars_mapping = {
        var: (lbl, unit) for (var, lbl, unit) in SUBGRID_MAP_VARIABLES}
    agg_vars_mapping = {
        var: (lbl, unit) for (var, lbl, unit) in AGGREGATION_VARIABLES}
    config = {'q': [], 'h': []}

    verbose_agg_method = {
        'min': 'minimum',
        'max': 'maximum',
        'cum': 'net cumulative',
        'avg': 'average',
        'med': 'median',
        'cum_positive': 'positive cumulative',
        'cum_negative': 'negative cumulative',
        }

    for varname in subgrid_map_vars:
        varinfo = subgrid_map_vars_mapping[varname]
        d = {'name': varinfo[0].capitalize(), 'unit': varinfo[1],
             'parameters': varname}
        if varname in Q_TYPES:
            config['q'].append(d)
        elif varname in H_TYPES:
            config['h'].append(d)

    for aggvarname in agg_vars:
        _varname, _agg_method = parse_aggvarname(aggvarname)
        varinfo = agg_vars_mapping[_varname]
        try:
            agg_method_display_name = verbose_agg_method[_agg_method]
        except KeyError:
            log("Unknown agg method: %s" % _agg_method, level='CRITICAL')
            agg_method_display_name = _agg_method

        # Adjust the unit for cumulative method
        if _agg_method.startswith('cum'):
            unit = CUMULATIVE_AGGREGATION_UNITS[_varname]
        else:
            unit = varinfo[1]

        d = {'name': '%s %s' % (agg_method_display_name.capitalize(),
                                varinfo[0]),
             'unit': unit, 'parameters': aggvarname}
        if _varname in Q_TYPES:
            config['q'].append(d)
        elif _varname in H_TYPES:
            config['h'].append(d)
    return config


pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

# Layer providers that we can use for the graph
VALID_PROVIDERS = ['spatialite', 'memory']


try:
    _encoding = QApplication.UnicodeUTF8

    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig)


class GraphPlot(pg.PlotWidget):
    """Graph element"""

    def __init__(self, parent=None):
        """

        :param parent: Qt parent widget
        """

        super(GraphPlot, self).__init__(parent)

        self.showGrid(True, True, 0.5)
        self.setLabel("bottom", "Tijd", "s")

        self.current_parameter = None
        self.location_model = None
        self.datasource_model = None
        self.parent = parent
        self.absolute = False

    def on_close(self):
        """
        unloading widget and remove all required stuff
        :return:
        """
        if self.location_model:
            self.location_model.dataChanged.disconnect(
                                            self.location_data_changed)
            self.location_model.rowsInserted.disconnect(
                                            self.on_insert_locations)
            self.location_model.rowsAboutToBeRemoved.disconnect(
                                            self.on_remove_locations)
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
        self.location_model.rowsAboutToBeRemoved.connect(
                self.on_remove_locations)

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
        for i in range(start, end+1):
            ds = self.ds_model.rows[i]
            if ds.active.value:
                for item in self.location_model.rows:
                    if item.active.value:
                        self.addItem(item.plots(
                            self.current_parameter['parameters'], i,
                            absolute=self.absolute))

    def on_remove_ds(self, index, start, end):
        """
        remove items from graph. based on Qt model removeRows
        trigger
        :param index: Qt Index (not used)
        :param start: first row nr
        :param end: last row nr
        """
        for i in range(start, end+1):
            ds = self.ds_model.rows[i]
            if ds.active.value:
                for item in self.location_model.rows:
                    if item.active.value:
                        self.removeItem(item.plots(
                                self.current_parameter['parameters'], i))

    def ds_data_changed(self, index):
        """
        change graphs based on changes in locations. based on Qt
        data change trigger
        :param index: index of changed field
        """
        if self.ds_model.columns[index.column()].name == 'active':

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
        for i in range(start, end+1):
            item = self.location_model.rows[i]
            for ds in self.ds_model.rows:
                if ds.active.value:
                    index = self.ds_model.rows.index(ds)
                    self.addItem(item.plots(
                        self.current_parameter['parameters'], index,
                        absolute=self.absolute))

    def on_remove_locations(self, index, start, end):
        """
        remove items from graph. based on Qt model removeRows
        trigger
        :param index: Qt Index (not used)
        :param start: first row nr
        :param end: last row nr
        """
        for i in range(start, end+1):
            item = self.location_model.rows[i]
            if item.active.value:
                for ds in self.ds_model.rows:
                    if ds.active.value:
                        index = self.ds_model.rows.index(ds)
                        self.removeItem(item.plots(
                                self.current_parameter['parameters'], index))

    def location_data_changed(self, index):
        """
        change graphs based on changes in locations
        :param index: index of changed field
        """
        if self.location_model.columns[index.column()].name == 'active':

            for i in range(0, len(self.ds_model.rows)):
                if self.ds_model.rows[i].active.value:
                    if self.location_model.rows[index.row()].active.value:
                        self.show_timeseries(index.row(), i)
                    else:
                        self.hide_timeseries(index.row(), i)

        elif self.location_model.columns[index.column()].name == 'hover':
            item = self.location_model.rows[index.row()]
            if item.hover.value:
                for ds in self.ds_model.rows:
                    if ds.active.value:
                        index = self.ds_model.rows.index(ds)
                        item.plots(self.current_parameter['parameters'],
                                   index).setPen(color=item.color.qvalue,
                                                 width=5,
                                                 style=ds.pattern.value)
            else:
                for ds in self.ds_model.rows:
                    if ds.active.value:
                        index = self.ds_model.rows.index(ds)
                        item.plots(self.current_parameter['parameters'],
                                   index).setPen(color=item.color.qvalue,
                                                 width=2,
                                                 style=ds.pattern.value)

    def hide_timeseries(self, location_nr, ds_nr):
        """
        hide timeseries of location in graph
        :param row_nr: integer, row number of location
        """

        plot = self.location_model.rows[location_nr].plots(
                    self.current_parameter['parameters'], ds_nr)
        self.removeItem(plot)

    def show_timeseries(self, location_nr, ds_nr):
        """
        show timeseries of location in graph
        :param row_nr: integer, row number of location
        """

        plot = self.location_model.rows[location_nr].plots(
                self.current_parameter['parameters'], ds_nr)
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

                        self.removeItem(item.plots(
                                old_parameter['parameters'], index))
                        self.addItem(item.plots(
                                self.current_parameter['parameters'], index))

        self.setLabel("left",
                      self.current_parameter['name'],
                      self.current_parameter['unit'])


class LocationTimeseriesTable(QTableView):

    hoverExitRow = pyqtSignal(int)
    hoverExitAllRows = pyqtSignal()  # exit the whole widget
    hoverEnterRow = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super(LocationTimeseriesTable, self).__init__(parent)
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
                        log("Hover row index %s out of range" %
                            self._last_hovered_row, level='WARNING')
                    # self.hoverExitRow.emit(self._last_hovered_row)
                # self.hoverEnterRow.emit(row)
                if row is not None:
                    try:
                        self.hover_enter(row)
                    except IndexError:
                        log("Hover row index %s out of range" % row,
                            level='WARNING')
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
        super(LocationTimeseriesTable, self).setModel(model)

        self.model = model

        self.resizeColumnsToContents()
        for col_nr in range(0, model.columnCount()):
            width = model.columns[col_nr].column_width
            if width:
                self.setColumnWidth(col_nr, width)
            if not model.columns[col_nr].show:
                self.setColumnHidden(col_nr, True)


class GraphWidget(QWidget):

    def __init__(self, parent=None, ts_datasource=None,
                 parameter_config=[], name="", geometry_type=QGis.WKBPoint):
        super(GraphWidget, self).__init__(parent)

        self.name = name
        self.ts_datasource = ts_datasource
        self.parent = parent
        self.geometry_type = geometry_type

        self.setup_ui()

        self.model = LocationTimeseriesModel(datasource=self.ts_datasource)
        self.graph_plot.set_location_model(self.model)
        self.graph_plot.set_ds_model(self.ts_datasource)
        self.location_timeseries_table.setModel(self.model)

        # set listeners
        self.parameter_combo_box.currentIndexChanged.connect(
                self.parameter_change)
        self.remove_timeseries_button.clicked.connect(self.remove_objects_table)

        # init parameter selection
        self.set_parameter_list(parameter_config)

        if self.geometry_type == QGis.WKBPoint:
            self.marker = QgsVertexMarker(self.parent.iface.mapCanvas())
        else:
            self.marker = QgsRubberBand(self.parent.iface.mapCanvas())
            self.marker.setColor(Qt.red)
            self.marker.setWidth(2)


    def set_parameter_list(self, parameter_config):

        # reset
        nr_old_parameters = self.parameter_combo_box.count()

        self.parameters = dict([(p['name'], p) for p in parameter_config])

        self.parameter_combo_box.insertItems(0, [p['name'] for p in parameter_config])

        # todo: find best matching parameter based on previous selection
        if nr_old_parameters > 0:
            self.parameter_combo_box.setCurrentIndex(0)

        nr_parameters_tot = self.parameter_combo_box.count()
        for i in reversed(range(nr_parameters_tot - nr_old_parameters, nr_parameters_tot)):
            self.parameter_combo_box.removeItem(i)

        # self.graph_plot.set_parameter(self.current_parameter)



    def on_close(self):
        """
        unloading widget and remove all required stuff
        :return:
        """
        self.parameter_combo_box.currentIndexChanged.disconnect(
                self.parameter_change)
        self.remove_timeseries_button.clicked.disconnect(
                self.remove_objects_table)

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
            self.parent.iface.mapCanvas().mapRenderer().destinationCrs())

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
                    if self.geometry_type == QGis.WKBPoint:
                        geom = feature.geometry()
                        geom.transform(transform)
                        self.marker.setCenter(geom.asPoint())
                        self.marker.setVisible(True)
                    else:
                        self.marker.setToGeometry(feature.geometry(), lyr)

    def unhighlight_all_features(self):
        """Remove the highlights from all layers"""

        if self.geometry_type == QGis.WKBPoint:
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
        sizePolicy.setHeightForWidth(
                self.graph_plot.sizePolicy().hasHeightForWidth())
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
        self.location_timeseries_table.hoverEnterRow.connect(
            self.highlight_feature)
        self.location_timeseries_table.hoverExitAllRows.connect(
            self.unhighlight_all_features)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
                self.location_timeseries_table.sizePolicy().hasHeightForWidth())
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
                self.remove_timeseries_button.sizePolicy().hasHeightForWidth())
        self.remove_timeseries_button.setSizePolicy(sizePolicy)
        self.remove_timeseries_button.setObjectName("remove_timeseries_button")
        self.hLayoutButtons.addWidget(self.remove_timeseries_button)
        self.hLayoutButtons.addItem(
                QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.retranslateUi()

    def retranslateUi(self):
        """
        set translated widget text
        """
        self.remove_timeseries_button.setText(
                _translate("DockWidget", "Verwijder", None))

    def parameter_change(self, nr):
        """
        set current selected parameter and trigger refresh of graphs
        :param nr: nr of selected option of combobox
        :return:
        """
        self.current_parameter = \
                self.parameters[self.parameter_combo_box.currentText()]
        self.graph_plot.set_parameter(self.current_parameter)

    def add_objects(self, layer, features):
        """

        :param layer: layer of features
        :param features: Qgis layer features to be added
        :return: boolean: new objects are added
        """

        # Get the active database as URI, connInfo is something like:
        # u"dbname='/home/jackieleng/git/threedi-turtle/var/models/
        # DS_152_1D_totaal_bergingsbak/results/
        # DS_152_1D_totaal_bergingsbak_result.sqlite'"
        connInfo = QgsDataSourceURI(
            layer.dataProvider().dataSourceUri()).connectionInfo()
        try:
            filename = connInfo.split("'")[1]
        except IndexError:
            filename = 'nofilename'

        # get attribute information from selected layers
        items = []
        existing_items = ["%s_%s" % (item.object_type.value,
                                   str(item.object_id.value))
                for item in self.model.rows]
        for feature in features:
            idx = feature.id()
            if layer.dataProvider().description() == u'Memory provider':
                idx = feature['id']


            try:
                object_name = feature['display_name']
            except KeyError:
                # TODO: need a more generic way, i.e., this needs to be fixed
                # in the views themselved:
                log("Guessing the object_name now because it's a v2 model",
                    level='WARNING')
                try:
                    object_name = feature[2]
                except KeyError:
                    log("It's probably a memory layer, but putting a dummy "
                        "name just for safety.")
                    object_name = 'dummy'

            # check if object not already exist
            if (layer.name() + '_' + str(idx)) not in existing_items:
                item = {
                    'object_type': layer.name(),
                    'object_id': idx,
                    'object_name': object_name,
                    'file_path': filename
                }
                items.append(item)

        if len(items) > 20:
            msg = "%i nieuwe objecten zijn geselecteerd. Toevoegen aan de " \
                  "grafiek kan enkele tijd duren. Wilt u doorgaan?" % len(items)
            reply = QMessageBox.question(self, 'Objecten toevoegen',
                     msg, QMessageBox.Yes, QMessageBox.No)

            if reply == QMessageBox.No:
                return False

        self.model.insertRows(items)
        msg = "%i nieuwe objecten toegevoegd aan grafiek " % len(items)
        skipped_items = len(features) - len(items)
        if skipped_items > 0:
            msg += "(%i al aanwezige objecten overgeslagen)" % skipped_items

        statusbar_message(msg)
        return True

    def remove_objects_table(self):
        """
        removes selected objects from table
        :return:
        """
        selection_model = self.location_timeseries_table.selectionModel()
        #get unique rows in selected fields
        rows = set([index.row() for index in selection_model.selectedIndexes()])
        for row in reversed(sorted(rows)):
            self.model.removeRows(row, 1)


class GraphDockWidget(QDockWidget):
    """Main Dock Widget for showing 3Di results in Graphs"""

    closingWidget = pyqtSignal(int)

    def __init__(self, iface, parent_widget=None,
                 parent_class=None, nr=0, ts_datasource=None, root_tool=None):
        """Constructor"""
        super(GraphDockWidget, self).__init__(parent_widget)

        self.iface = iface
        self.parent_class = parent_class
        self.nr = nr
        self.ts_datasource = ts_datasource
        self.root_tool = root_tool

        self.setup_ui(self)

        parameter_config = self._get_active_parameter_config()

        # add graph widgets
        self.q_graph_widget = GraphWidget(self, self.ts_datasource,
                                          parameter_config['q'], "Q graph",
                                          QGis.WKBLineString)
        self.h_graph_widget = GraphWidget(self, self.ts_datasource,
                                          parameter_config['h'], "H graph",
                                          QGis.WKBPoint)
        self.graphTabWidget.addTab(self.q_graph_widget,
                                   self.q_graph_widget.name)
        self.graphTabWidget.addTab(self.h_graph_widget,
                                   self.h_graph_widget.name)

        # add listeners
        self.addSelectedObjectButton.clicked.connect(self.add_objects)
        # init current layer state and add listener
        self.selected_layer_changed(self.iface.mapCanvas().currentLayer)
        self.iface.currentLayerChanged.connect(self.selected_layer_changed)
        self.root_tool.timeslider_widget.datasource_changed.connect(self.on_active_datasource_change)

    def on_close(self):
        """
        unloading widget and remove all required stuff
        :return:
        """
        self.addSelectedObjectButton.clicked.disconnect(self.add_objects)
        self.iface.currentLayerChanged.disconnect(self.selected_layer_changed)
        self.root_tool.timeslider_widget.datasource_changed.disconnect(self.on_active_datasource_change)

        #self.q_graph_widget.close()
        #self.h_graph_widget.close()

    def closeEvent(self, event):
        """
        overwrite of QDockWidget class to emit signal
        :param event: QEvent
        """
        self.on_close()
        self.closingWidget.emit(self.nr)
        event.accept()

    def _get_active_parameter_config(self):

        active_ds = self.root_tool.timeslider_widget.active_datasource

        if active_ds is not None:
            # TODO: just taking the first datasource, not sure if correct:
            ds = active_ds.datasource()
            available_subgrid_vars = ds.available_subgrid_map_vars
            available_agg_vars = ds.available_aggregation_vars
            if not available_agg_vars:
                messagebar_message(
                    "Warning", "No aggregation netCDF was found.", level=1,
                    duration=5)
            parameter_config = generate_parameter_config(
                available_subgrid_vars, available_agg_vars)
        else:
            parameter_config = {'q': {}, 'h': {}}

        return parameter_config

    def on_active_datasource_change(self):

        parameter_config = self._get_active_parameter_config()
        self.q_graph_widget.set_parameter_list(parameter_config['q'])
        self.h_graph_widget.set_parameter_list(parameter_config['h'])

    def selected_layer_changed(self, active_layer):

        tdi_layer = False

        #get active layer from canvas, otherwise .dataProvider doesn't work
        canvas = self.iface.mapCanvas()
        current_layer = canvas.currentLayer()

        if current_layer:
            provider = current_layer.dataProvider()
            valid_object_type = normalized_object_type(current_layer.name())

            if provider.name() in VALID_PROVIDERS and valid_object_type:
                tdi_layer = True
            elif current_layer.name() in ('flowlines', 'nodes'):
                tdi_layer = True

        #activate button if 3Di layers found
        self.addSelectedObjectButton.setEnabled(tdi_layer)

    def add_objects(self):
        canvas = self.iface.mapCanvas()
        current_layer = canvas.currentLayer()
        if not current_layer:
            #todo: feedback select layer first
            return

        provider = current_layer.dataProvider()
        if provider.name() not in VALID_PROVIDERS:
            return

        if current_layer.name() not in layer_qh_type_mapping.keys():
            if current_layer.name() not in ('flowlines', 'nodes'):
                #todo: feedback layer not supported
                return

        selected_features = current_layer.selectedFeatures()

        if current_layer.name() == 'flowlines':
            self.q_graph_widget.add_objects(current_layer, selected_features)
            self.graphTabWidget.setCurrentIndex(
                    self.graphTabWidget.indexOf(self.q_graph_widget))
            return
        elif current_layer.name() == 'nodes':
            self.h_graph_widget.add_objects(current_layer, selected_features)
            self.graphTabWidget.setCurrentIndex(
                self.graphTabWidget.indexOf(self.h_graph_widget))
            return

        if layer_qh_type_mapping[current_layer.name()] == 'q':
            self.q_graph_widget.add_objects(current_layer, selected_features)
            self.graphTabWidget.setCurrentIndex(
                    self.graphTabWidget.indexOf(self.q_graph_widget))
        else:
            self.h_graph_widget.add_objects(current_layer, selected_features)
            self.graphTabWidget.setCurrentIndex(
                    self.graphTabWidget.indexOf(self.h_graph_widget))

    def on_btnstate(self, state):
        """Toggle ``absolute`` state of the GraphPlots"""
        checked = (state == Qt.Checked)
        self.q_graph_widget.graph_plot.absolute = \
            self.h_graph_widget.graph_plot.absolute = checked

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
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding,
                                 QSizePolicy.Minimum)
        self.buttonBarHLayout.addItem(spacerItem)
        self.mainVLayout.addItem(self.buttonBarHLayout)

        # add tabWidget for graphWidgets
        self.graphTabWidget = QTabWidget(self.dockWidgetContent)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(6)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
                self.graphTabWidget.sizePolicy().hasHeightForWidth())
        self.graphTabWidget.setSizePolicy(sizePolicy)
        self.graphTabWidget.setObjectName("graphTabWidget")
        self.mainVLayout.addWidget(self.graphTabWidget)

        # add dockwidget
        dock_widget.setWidget(self.dockWidgetContent)
        self.retranslate_ui(dock_widget)
        QMetaObject.connectSlotsByName(dock_widget)

    def retranslate_ui(self, DockWidget):
        DockWidget.setWindowTitle(_translate(
            "DockWidget", "3Di resultaat grafieken %i" % self.nr, None))
        self.addSelectedObjectButton.setText(_translate(
            "DockWidget", "Voeg toe", None))
