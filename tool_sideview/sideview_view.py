from collections import Counter
from functools import reduce
from qgis.analysis import QgsVectorLayerDirector
from qgis.core import QgsDataSourceUri
from qgis.core import QgsFeatureRequest
from qgis.core import QgsPointXY
from qgis.core import QgsProject
from qgis.core import QgsVectorLayer
from qgis.core import Qgis
from qgis.core import QgsDateTimeRange
from qgis.core import NULL
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot
from qgis.PyQt.QtCore import QMetaObject
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.PyQt.QtWidgets import QHBoxLayout
from qgis.PyQt.QtWidgets import QPushButton
from qgis.PyQt.QtWidgets import QSizePolicy
from qgis.PyQt.QtWidgets import QSpacerItem
from qgis.PyQt.QtWidgets import QVBoxLayout
from qgis.PyQt.QtWidgets import QWidget
from threedi_results_analysis.tool_sideview.route import Route, RouteMapTool, CustomDistancePropeter
from threedi_results_analysis.tool_sideview.sideview_visualisation import SideViewMapVisualisation
from threedi_results_analysis.tool_sideview.utils import haversine
from threedi_results_analysis.tool_sideview.utils import split_line_at_points
from threedi_results_analysis.tool_sideview.utils import LineType
from threedi_results_analysis.utils.user_messages import statusbar_message
from threedi_results_analysis.utils.user_messages import messagebar_message
from threedi_results_analysis.utils.user_messages import StatusProgressBar
from threedi_results_analysis.utils.utils import python_value
from threedi_results_analysis.tool_sideview.sideview_graph_generator import SideViewGraphGenerator
from qgis.utils import iface
from bisect import bisect
import logging
import numpy as np
import os
from datetime import datetime as Datetime
import pyqtgraph as pg

logger = logging.getLogger(__name__)

parameter_config = {
    "q": [
        {"name": "Discharge", "unit": "m3/s", "parameters": ["q"]},
        {"name": "Velocity", "unit": "m/s", "parameters": ["u1"]},
    ],
    "h": [
        {"name": "Waterlevel", "unit": "mNAP", "parameters": ["s1"]},
        {"name": "Volume", "unit": "m3", "parameters": ["vol"]},
    ],
}


INTERPOLATION_PHYSICAL = 0  # interpolation based on all profiles
# interpolation as the 3Di calculation core is
# performing the interpolation. for bottom
# level use profiles close to
# calculation points. For height (profile) first
# get heigth on centerpoints at links
INTERPOLATION_CALCULATION = 1


class SideViewPlotWidget(pg.PlotWidget):
    """Side view plot element"""

    profile_route_updated = pyqtSignal()
    profile_hovered = pyqtSignal(float)

    def __init__(
        self,
        parent=None,
        point_dict=None,
        model=None,
    ):
        """

        :param parent: Qt parent widget
        """
        super().__init__(parent)

        self.model = model

        self.node_dict = point_dict

        self.sideview_nodes = []

        self.showGrid(True, True, 0.5)
        self.setLabel("bottom", "Distance", "m")
        self.setLabel("left", "Height", "mNAP")

        pen = pg.mkPen(color=QColor(200, 200, 200), width=1)
        self.bottom_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)
        self.upper_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)

        pen = pg.mkPen(color=QColor(100, 100, 100), width=2)
        self.sewer_bottom_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)
        self.sewer_upper_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)

        pen = pg.mkPen(color=QColor(50, 50, 50), width=2)
        self.channel_bottom_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)
        self.channel_upper_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)

        pen = pg.mkPen(color=QColor(150, 75, 0), width=4)
        self.culvert_bottom_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)
        self.culvert_upper_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)

        pen = pg.mkPen(color=QColor(200, 30, 30), width=4)
        self.weir_bottom_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)
        self.weir_upper_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)

        pen = pg.mkPen(color=QColor(0, 255, 0), width=1)
        self.orifice_bottom_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)
        self.orifice_upper_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)

        pen = pg.mkPen(color=QColor(200, 200, 0), width=4)
        self.pump_bottom_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)
        self.pump_upper_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)

        # Required for fill in bottom of graph
        self.absolute_bottom = pg.PlotDataItem(np.array([(0.0, -10000), (10000, -10000)]), pen=pen)
        self.bottom_fill = pg.FillBetweenItem(
            self.bottom_plot, self.absolute_bottom, pg.mkBrush(200, 200, 200)
        )

        pen = pg.mkPen(color=QColor(0, 255, 255), width=2)
        self.water_level_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)
        self.water_fill = pg.FillBetweenItem(
            self.water_level_plot, self.absolute_bottom, pg.mkBrush(0, 255, 255)
        )

        self.addItem(self.water_fill)
        self.addItem(self.bottom_fill)

        self.addItem(self.bottom_plot)
        self.addItem(self.upper_plot)
        self.addItem(self.sewer_bottom_plot)
        self.addItem(self.sewer_upper_plot)
        self.addItem(self.channel_bottom_plot)
        self.addItem(self.channel_upper_plot)
        self.addItem(self.culvert_bottom_plot)
        self.addItem(self.culvert_upper_plot)
        self.addItem(self.weir_bottom_plot)
        self.addItem(self.weir_upper_plot)
        self.addItem(self.orifice_bottom_plot)
        self.addItem(self.orifice_upper_plot)
        self.addItem(self.pump_bottom_plot)
        self.addItem(self.pump_upper_plot)

        self.addItem(self.water_level_plot)

        # Add some fills
        self.orifice_fill = pg.FillBetweenItem(
            self.orifice_upper_plot, self.orifice_bottom_plot, pg.mkBrush(0, 255, 0)
        )
        self.addItem(self.orifice_fill)

        # set listeners to signals
        self.profile_route_updated.connect(self.update_water_level_cache)

        # set code for hovering
        self.vb = self.plotItem.vb
        self.proxy = pg.SignalProxy(
            self.scene().sigMouseMoved, rateLimit=10, slot=self.mouse_hover
        )
        # self.scene().sigMouseMoved.connect(self.mouse_hover)

    def mouse_hover(self, evt):
        mouse_point_x = self.plotItem.vb.mapSceneToView(evt[0]).x()
        self.profile_hovered.emit(mouse_point_x)

    def set_sideprofile(self, route_path):

        self.sideview_nodes = []
        bottom_line = []
        upper_line = []

        first_node = True

        for route_part in route_path:
            logger.error("ROUTE PATH")

            for count, (begin_dist, end_dist, distance, direction, feature) in enumerate(route_part):

                begin_dist = float(begin_dist)
                end_dist = float(end_dist)

                if direction == 1:
                    begin_node_id = feature["start_node_id"]
                    end_node_id = feature["end_node_id"]
                else:
                    end_node_id = feature["start_node_id"]
                    begin_node_id = feature["end_node_id"]

                begin_node = self.node_dict[begin_node_id]
                end_node = self.node_dict[end_node_id]

                # 1. add point structure (manhole)
                logger.info(f"node type {begin_node['type']}, manhole: {begin_node['is_manhole']}")
                logger.info(f"Adding node {begin_node_id} with length: {begin_node['length']}, height: {begin_node['height']} and level: {begin_node['level']}")

                if first_node:  # Add closing vertical line at beginning
                    bottom_line.append(
                        (
                            begin_dist - 0.5 * begin_node["length"],
                            begin_node["level"] + begin_node["height"],
                            LineType.PIPE,
                        )
                    )

                bottom_line.append(
                    (
                        begin_dist - 0.5 * begin_node["length"],
                        begin_node["level"],
                        LineType.PIPE,
                    )
                )
                bottom_line.append(
                    (
                        begin_dist + 0.5 * begin_node["length"],
                        begin_node["level"],
                        LineType.PIPE,
                    )
                )

                upper_line.append(
                    (
                        begin_dist - 0.5 * begin_node["length"],
                        begin_node["level"] + begin_node["height"],
                        LineType.PIPE,
                    )
                )
                upper_line.append(
                    (
                        begin_dist + 0.5 * begin_node["length"],
                        begin_node["level"] + begin_node["height"],
                        LineType.PIPE,
                    )
                )

                # 2 contours based on structure or pipe
                ltype = feature["type"]
                if (ltype == LineType.PIPE) or (ltype == LineType.CULVERT) or (ltype == LineType.ORIFICE) or (ltype == LineType.WEIR) or (ltype == LineType.CHANNEL):
                    if direction == 1:
                        begin_level = feature["start_level"]
                        end_level = feature["end_level"]
                        begin_height = feature["start_height"]
                        end_height = feature["end_height"]
                    else:
                        begin_level = feature["end_level"]
                        end_level = feature["start_level"]
                        begin_height = feature["end_height"]
                        end_height = feature["start_height"]

                    logger.info(f"Adding line {feature['id']} with length: {feature['real_length']}, start_height: {feature['start_height']}, end_height: {feature['end_height']}, start_level: {feature['start_level']} and end_level {feature['end_level']}")

                    bottom_line.append(
                        (
                            begin_dist + 0.5 * begin_node["length"],
                            begin_level,
                            ltype,
                        )
                    )
                    bottom_line.append(
                        (
                            end_dist - 0.5 * end_node["length"],
                            end_level,
                            ltype
                        )
                    )

                    # upper line
                    upper_line.append(
                        (
                            begin_dist + 0.5 * begin_node["length"],
                            begin_level + begin_height,
                            ltype,
                        )
                    )
                    upper_line.append(
                        (
                            end_dist - 0.5 * end_node["length"],
                            end_level + end_height,
                            ltype,
                        )
                    )
                else:
                    logger.error(f"Unknown line type: {ltype}")

                # 3 Add closing point/manhole (if last segment)
                if count == (len(route_part)-1):
                    bottom_line.append(
                        (
                            end_dist - 0.5 * end_node["length"],
                            end_node["level"],
                            LineType.PIPE,
                        )
                    )
                    bottom_line.append(
                        (
                            end_dist + 0.5 * end_node["length"],
                            end_node["level"],
                            LineType.PIPE,
                        )
                    )
                    upper_line.append(
                        (
                            end_dist - 0.5 * end_node["length"],
                            end_node["level"] + end_node["height"],
                            LineType.PIPE,
                        )
                    )
                    upper_line.append(
                        (
                            end_dist + 0.5 * end_node["length"],
                            end_node["level"] + end_node["height"],
                            LineType.PIPE,
                        )
                    )

                # store node information for water level line
                if first_node:
                    self.sideview_nodes.append(
                        {"distance": begin_dist, "id": begin_node_id}
                    )
                    first_node = False

                self.sideview_nodes.append(
                    {"distance": end_dist, "id": end_node_id}
                )

        if len(route_path) > 0:
            # Draw data into graph
            # split lines into seperate parts for the different line types
            # (channel, structure, etc.)

            # determine max and min x value to draw absolute bottom line
            x_min = min([point[0] for point in bottom_line])
            x_max = max([point[0] for point in bottom_line])
            self.absolute_bottom.setData(np.array([(x_min, -10000), (x_max, -10000)], dtype=float), connect="finite")

            tables = {
                LineType.PIPE: [],
                LineType.CHANNEL: [],
                LineType.CULVERT: [],
                LineType.PUMP: [],
                LineType.WEIR: [],
                LineType.ORIFICE: [],
            }
            last_type = None
            for point in bottom_line:
                ptype = point[2]

                if ptype != last_type:
                    if last_type is not None:
                        # add nan point to make gap in line
                        tables[ptype].append((point[0], np.nan))
                    last_type = ptype
                tables[ptype].append((point[0], point[1]))

            ts_table = np.array([(b[0], b[1]) for b in bottom_line], dtype=float)
            self.bottom_plot.setData(ts_table, connect="finite")

            self.sewer_bottom_plot.setData(np.array(tables[LineType.PIPE], dtype=float), connect="finite")
            self.channel_bottom_plot.setData(np.array(tables[LineType.CHANNEL], dtype=float), connect="finite")
            self.culvert_bottom_plot.setData(np.array(tables[LineType.CULVERT], dtype=float), connect="finite")
            self.weir_bottom_plot.setData(np.array(tables[LineType.WEIR], dtype=float), connect="finite")
            self.orifice_bottom_plot.setData(np.array(tables[LineType.ORIFICE], dtype=float), connect="finite")
            self.pump_bottom_plot.setData(np.array(tables[LineType.PUMP], dtype=float), connect="finite")

            tables = {
                LineType.PIPE: [],
                LineType.CHANNEL: [],
                LineType.CULVERT: [],
                LineType.PUMP: [],
                LineType.WEIR: [],
                LineType.ORIFICE: [],
            }
            last_type = None
            for point in upper_line:
                ptype = point[2]

                if ptype != last_type:
                    if last_type is not None:
                        tables[ptype].append((point[0], np.nan))
                    last_type = ptype
                tables[ptype].append((point[0], point[1]))

            ts_table = np.array([(b[0], b[1]) for b in upper_line], dtype=float)
            self.upper_plot.setData(ts_table, connect="finite")

            self.sewer_upper_plot.setData(np.array(tables[LineType.PIPE], dtype=float), connect="finite")
            self.channel_upper_plot.setData(np.array(tables[LineType.CHANNEL], dtype=float), connect="finite")
            self.culvert_upper_plot.setData(np.array(tables[LineType.CULVERT], dtype=float), connect="finite")
            self.weir_upper_plot.setData(np.array(tables[LineType.WEIR], dtype=float), connect="finite")
            self.orifice_upper_plot.setData(np.array(tables[LineType.ORIFICE], dtype=float), connect="finite")
            self.pump_upper_plot.setData(np.array(tables[LineType.PUMP], dtype=float), connect="finite")

            # reset water level line
            ts_table = np.array(np.array([(0.0, np.nan)]), dtype=float)
            self.water_level_plot.setData(ts_table)

            # Only let specific set of plots determine range
            self.autoRange(items=[self.bottom_plot, self.upper_plot, self.water_level_plot])

            self.profile_route_updated.emit()
        else:
            # reset sideview
            ts_table = np.array(np.array([(0.0, np.nan)]), dtype=float)
            self.bottom_plot.setData(ts_table)
            self.upper_plot.setData(ts_table)
            self.sewer_bottom_plot.setData(ts_table)
            self.sewer_upper_plot.setData(ts_table)
            self.channel_bottom_plot.setData(ts_table)
            self.channel_upper_plot.setData(ts_table)
            self.culvert_bottom_plot.setData(ts_table)
            self.culvert_upper_plot.setData(ts_table)
            self.weir_bottom_plot.setData(ts_table)
            self.weir_upper_plot.setData(ts_table)
            self.orifice_bottom_plot.setData(ts_table)
            self.orifice_upper_plot.setData(ts_table)
            self.pump_bottom_plot.setData(ts_table)
            self.pump_upper_plot.setData(ts_table)

            self.water_level_plot.setData(ts_table)

            # Node list used to draw results
            self.sideview_nodes = []

    def update_water_level_cache(self):
        ds_item = self.model.get_results(False)[0]  # TODO: PLOT MULTIPLE RESULTS?
        if ds_item:
            logger.info("Updating water level cache")
            ds = ds_item.threedi_result
            for node in self.sideview_nodes:
                node["timeseries"] = ds.get_timeseries("s1", node_id=int(node["id"]), fill_value=np.NaN)

            tc = iface.mapCanvas().temporalController()
            self.update_waterlevel(tc.dateTimeRangeForFrameNumber(tc.currentFrameNumber()))
        else:
            # reset water level line
            logger.error("No DS_ITEM!")
            self.water_level_plot.setData(np.array(np.array([(0.0, np.nan)]), dtype=float))

    @pyqtSlot(QgsDateTimeRange)
    def update_waterlevel(self, qgs_dt_range: QgsDateTimeRange):

        result_item = self.model.get_results(False)[0]  # TODO: PLOT MULTIPLE RESULTS?
        if not result_item:
            return

        threedi_result = result_item.threedi_result
        # TODO: refactor the following to an util function and check (first datetime yields idx 1)
        current_datetime = qgs_dt_range.begin().toPyDateTime()
        begin_datetime = Datetime.fromisoformat(threedi_result.dt_timestamps[0])
        end_datetime = Datetime.fromisoformat(threedi_result.dt_timestamps[-1])
        current_datetime = max(begin_datetime, min(current_datetime, end_datetime))
        current_delta = (current_datetime - begin_datetime)
        current_seconds = current_delta.total_seconds()
        parameter_timestamps = threedi_result.get_timestamps("s1")
        timestamp_nr = bisect(parameter_timestamps, current_seconds)
        timestamp_nr = min(timestamp_nr, parameter_timestamps.size - 1)

        # timestamp_nr = 1
        logger.info(f"Drawing result for nr {timestamp_nr}")

        water_level_line = []
        for node in self.sideview_nodes:
            water_level = node["timeseries"][timestamp_nr][1]
            water_level_line.append((node["distance"], water_level))
            # logger.error(f"Node shape {node['timeseries'].shape}, distance {node['distance']} and level {water_level}")

        ts_table = np.array(water_level_line, dtype=float)
        self.water_level_plot.setData(ts_table)

    def on_close(self):
        """
        unloading widget and remove all required stuff
        :return:
        """
        self.profile_route_updated.disconnect(self.update_water_level_cache)

    def closeEvent(self, event):
        """
        overwrite of QDockWidget class to emit signal
        :param event: QEvent
        """
        self.on_close()
        event.accept()


class SideViewDockWidget(QDockWidget):
    """Main Dock Widget for showing 3Di results in Graphs"""

    # todo:
    # detecteer dichtsbijzijnde punt in plaats van willekeurige binnen gebied
    # let op CRS van vreschillende lagen en CRS changes

    closingWidget = pyqtSignal(int)

    def __init__(
        self, iface, nr, model, datasources, parent=None
    ):
        super().__init__(parent)

        self.iface = iface
        self.nr = nr
        self.model = model

        # setup ui
        self.setup_ui()

        # add listeners
        self.select_sideview_button.clicked.connect(self.toggle_route_tool)
        self.reset_sideview_button.clicked.connect(self.reset_sideview)

        # init class attributes
        self.route_tool_active = False

        # create point and line layer out of spatialite layers
        # if self.model.number_of_results() > 0:
        #     line, node, cell, pump = self.model.get_results(checked_only=False)[0].get_result_layers()
        # else:  # is this case possible?
        #     line = None # noqa

        # logger.error(datasources.model_spatialite_filepath)
        # (
        #     self.point_dict,
        #     self.channel_profiles,
        # ) = self.create_combined_layers(
        #     datasources.model_spatialite_filepath, line
        # )

        progress_bar = StatusProgressBar(100, "3Di Sideview")
        progress_bar.set_value(0, "Creating flowline graph")
        self.graph_layer = SideViewGraphGenerator.generate_layer(self.model.get_results(checked_only=False)[0].parent().path, progress_bar)
        self.point_dict = SideViewGraphGenerator.generate_node_info(self.model.get_results(checked_only=False)[0].parent().path)
        del progress_bar

        QgsProject.instance().addMapLayer(self.graph_layer)

        self.side_view_plot_widget = SideViewPlotWidget(
            self,
            self.point_dict,
            self.model,
        )
        self.main_vlayout.addWidget(self.side_view_plot_widget)

        self.active_sideview = self.side_view_plot_widget

        # Init route graph
        self.route = Route(
            self.graph_layer,
            QgsVectorLayerDirector(self.graph_layer, -1, "", "", "", QgsVectorLayerDirector.DirectionBoth),
            id_field="id",
            weight_properter=CustomDistancePropeter(),
            distance_properter=CustomDistancePropeter(),
        )

        # link route map tool
        self.route_tool = RouteMapTool(
            self.iface.mapCanvas(), self.graph_layer, self.on_route_point_select
        )

        self.route_tool.deactivated.connect(self.unset_route_tool)

        self.map_visualisation = SideViewMapVisualisation(
            self.iface, self.graph_layer.crs()
        )

        # connect graph hover to point visualisation on map
        self.active_sideview.profile_hovered.connect(self.map_visualisation.hover_graph)

        # add tree layer to map (for fun and testing purposes)
        self.vl_tree_layer = self.route.get_virtual_tree_layer()

        self.vl_tree_layer.loadNamedStyle(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "layer_styles",
                "tree.qml",
            )
        )

        QgsProject.instance().addMapLayer(self.vl_tree_layer)

    @pyqtSlot(QgsDateTimeRange)
    def update_waterlevel(self, qgs_dt_range: QgsDateTimeRange):
        self.side_view_plot_widget.update_waterlevel(qgs_dt_range)

    def create_combined_layers(self, spatialite_path, model_line_layer):

        def get_layer(spatialite_path, table_name, geom_column=""):
            uri2 = QgsDataSourceUri()
            uri2.setDatabase(spatialite_path)
            uri2.setDataSource("", table_name, geom_column)

            return QgsVectorLayer(uri2.uri(), table_name, "spatialite")

        profile_layer = get_layer(spatialite_path, "v2_cross_section_definition")
        profiles = {}
        for profile in profile_layer.getFeatures():
            # todo: add support for other definitions
            rel_bottom_level = 0.0
            open = False
            height_was_none = False

            if profile["shape"] in (1, 2, 3):

                height = python_value(profile["height"], func=float)
                # grid['cross_sections']['width_1d'] in netcdf?
                width = python_value(profile["width"], func=float)
                if profile["shape"] == 1:
                    # rectangle
                    if height is None:
                        # square
                        height_was_none = True
                        if width is not None:
                            height = width
                elif profile["shape"] == 2:
                    # round
                    height = width
            elif profile["shape"] in (5, 6):
                # tabulated and tabulated interpolated
                height_list = profile["height"].split(" ")
                # The calculation core automagically move the lowest point of
                # a profile to 0, so this is not correct:
                # rel_bottom_level = float(height_list[0])
                # height = float(height_list[-1]) - rel_bottom_level
                # but this:
                rel_bottom_level = 0.0
                # todo: catch and warn of values are incorrect
                height = float(height_list[-1]) - float(height_list[0])

                if float(profile["width"].split(" ")[-1]) > 0.01:
                    open = True

            profiles[profile["id"]] = {
                "height": height,
                "rel_bottom_level": rel_bottom_level,
                "open": open,
                "height_was_none": height_was_none,
            }

        connection_node_layer = get_layer(spatialite_path, "v2_connection_nodes", "the_geom")
        manhole_layer = get_layer(spatialite_path, "v2_manhole")
        boundary_layer = get_layer(spatialite_path, "v2_1d_boundary_conditions")

        points = {}
        for cn in connection_node_layer.getFeatures():
            points[cn["id"]] = {
                "point": cn.geometry().asPoint(),
                "type": LineType.CONNECTION_NODE,
                "surface_level": None,
                "drain_level": None,
                "bottom_level": None,
                "length": 0.0,
            }

        for manhole in manhole_layer.getFeatures():
            p = points[manhole["connection_node_id"]]
            p["type"] = LineType.MANHOLE
            p["surface_level"] = python_value(manhole["surface_level"])
            p["drain_level"] = python_value(manhole["drain_level"], p["surface_level"])
            p["bottom_level"] = python_value(manhole["bottom_level"])
            p["length"] = python_value(manhole["width"], 0.0)

        for bound in boundary_layer.getFeatures():
            p = points[bound["connection_node_id"]]
            p["type"] = LineType.BOUNDARY
            p["surface_level"] = None
            p["drain_level"] = None
            p["bottom_level"] = None
            p["length"] = 0.0

        # This dict is being returned:
        channel_profiles = {}

        cross_section_location_layer = get_layer(spatialite_path, "v2_cross_section_location", "the_geom")
        channel_layer = get_layer(spatialite_path, "v2_channel", "the_geom")

        channel_calc_points = {}
        channel_cs_locations = {}

        for cs in cross_section_location_layer.getFeatures():

            ids = cs["channel_id"]
            if ids not in channel_cs_locations:
                channel_cs_locations[ids] = []

            channel_cs_locations[ids].append(cs)

        if model_line_layer is not None:
            # create indexed sets of calculation points
            request = QgsFeatureRequest().setFilterExpression(u"type='v2_channel'")
            for line in model_line_layer.getFeatures(request):
                ids = line["spatialite_id"]
                if ids not in channel_calc_points:
                    channel_calc_points[ids] = []
                channel_calc_points[ids].append(line)

        for channel in channel_layer.getFeatures():
            channel_profiles[channel["id"]] = []
            # prepare profile information of channel
            if channel["id"] in channel_cs_locations:
                crs_points = channel_cs_locations[channel["id"]]
            else:
                crs_points = []

            profile_channel_parts = split_line_at_points(
                channel.geometry(),
                crs_points,
                point_feature_id_field="id",
                start_node_id=None,
                end_node_id=None,
            )

            # split on cross section locations
            for i, part in enumerate(profile_channel_parts):

                if part["start_point_id"] is not None:
                    start_id = "crs_" + str(part["start_point_id"])
                else:
                    start_id = channel["connection_node_start_id"]

                if part["end_point_id"] is not None:
                    end_id = "crs_" + str(part["end_point_id"])
                else:
                    end_id = channel["connection_node_end_id"]

                channel_part = {
                    "id": "subch_" + str(channel["id"]) + "_" + str(i),
                    "type": LineType.CHANNEL,
                    "start_node": start_id,
                    "end_node": end_id,
                    "real_length": part["length"],
                    "sub_channel_nr": i,
                    "channel_id": channel["id"],
                    "start_channel_distance": part["distance_at_line"],
                }

                # use cross sections part for only as info for drawing
                # sideview
                channel_profiles[channel["id"]].append(channel_part)

            for p in crs_points:
                def_id = p["definition_id"]
                try:
                    crs_def = profiles[def_id]
                except KeyError:
                    # Skip point if its `definitition_id` is not present in the profiles
                    continue
                level = p["reference_level"] + crs_def["rel_bottom_level"]
                height = crs_def["height"]
                bank_level = p["bank_level"]

                points["crs_" + str(p["id"])] = {
                    "point": p.geometry().asPoint(),
                    "type": LineType.CROSS_SECTION,
                    "surface_level": bank_level,
                    "drain_level": bank_level,
                    "bottom_level": level,
                    "height": height,
                    "length": 0.0,
                }

            if model_line_layer is not None:
                # create channel part for each sub link (taking calculation
                # nodes into account)

                cpoints_idx = []
                cpoints = {}
                # get calculation points on line
                for line in channel_calc_points[channel["id"]]:
                    cpoints_idx.append(line["start_node_idx"])
                    cpoints[line["start_node_idx"]] = line.geometry().asPolyline()[0]
                    cpoints_idx.append(line["end_node_idx"])
                    cpoints[line["end_node_idx"]] = line.geometry().asPolyline()[-1]

                # all calculation nodes (points in between, must be a
                # startpoint as well as an endpoint, so 2 occurances)
                cpoint_count = dict(Counter(cpoints_idx))
                calc_points = [
                    key for key, value in list(cpoint_count.items()) if value == 2
                ]

                calculation_points = [
                    {"id": key, "geom": value}
                    for key, value in list(cpoints.items())
                    if key in calc_points
                ]

                channel_parts = split_line_at_points(
                    channel.geometry(),
                    calculation_points,
                    point_feature_id_field="id",
                    start_node_id=None,
                    end_node_id=None,
                )

                for i, part in enumerate(channel_parts):
                    if i == 0:
                        start_node_id = channel["connection_node_start_id"]
                    else:
                        start_node_id = "calc_" + str(part["start_point_id"])

                    if i == len(channel_parts) - 1:
                        end_node_id = channel["connection_node_end_id"]
                    else:
                        end_node_id = "calc_" + str(part["end_point_id"])

                    channel_part = {
                        "id": "subch_" + str(channel["id"]) + "_" + str(i),
                        "type": LineType.CHANNEL,
                        "start_node": start_node_id,
                        "end_node": end_node_id,
                        "start_node_idx": part["start_point_id"],
                        "end_node_idx": part["end_point_id"],
                        "real_length": part["length"],
                        "sub_channel_nr": i,
                        "channel_id": channel["id"],
                        "start_channel_distance": part["distance_at_line"],
                        "geom": part["geom"],
                    }

                for p in calculation_points:
                    points["calc_" + str(p["id"])] = {
                        "point": p["geom"],
                        "type": LineType.CALCULATION_NODE,
                        "surface_level": None,
                        "drain_level": None,
                        "bottom_level": None,
                        "height": None,
                        "length": 0.0,
                    }

        # We need to make sure that all ids are strings
        points = {str(point_id): point for point_id, point in points.items()}
        #  make point dict permanent
        self.point_dict = points
        return points, channel_profiles

    def unset_route_tool(self):
        if self.route_tool_active:
            self.route_tool_active = False
            self.iface.mapCanvas().unsetMapTool(self.route_tool)

    def toggle_route_tool(self):
        if self.route_tool_active:
            self.route_tool_active = False
            self.iface.mapCanvas().unsetMapTool(self.route_tool)
        else:
            self.route_tool_active = True
            self.iface.mapCanvas().setMapTool(self.route_tool)

    def on_route_point_select(self, selected_features, clicked_coordinate):
        """Select and add the closest point from the list of selected features.

        Args:
            selected_features: list of features selected by click
            clicked_coordinate: (lon, lat) (transformed) of the click
        """

        def haversine_clicked(coordinate):
            """Calculate the distance w.r.t. the clicked location."""
            lon1, lat1 = clicked_coordinate
            lon2, lat2 = coordinate.x(), coordinate.y()
            return haversine(lon1, lat1, lon2, lat2)

        selected_coordinates = reduce(
            lambda accum, f: accum
            + [f.geometry().vertexAt(0), f.geometry().vertexAt(1)],
            selected_features,
            [],
        )

        if len(selected_coordinates) == 0:
            return

        closest_point = min(selected_coordinates, key=haversine_clicked)
        next_point = QgsPointXY(closest_point)

        success, msg = self.route.add_point(next_point)

        if not success:
            statusbar_message(msg)

        # values_valid = self.validate_path_nodes_values(self.route.path, "surface_level")
        # As we are no longer using surface level, this validation can be skipped
        values_valid = True

        if values_valid:
            self.active_sideview.set_sideprofile(self.route.path)
            self.map_visualisation.set_sideview_route(self.route)
        else:
            self.reset_sideview()

    def validate_path_nodes_values(self, profile, *attributes):
        nodes = {}
        invalid_values = [None, NULL]
        for route_part in profile:
            for begin_dist, end_dist, distance, direction, feature in route_part:
                start_node_id = str(feature["start_node"])
                end_node_id = str(feature["end_node"])
                start_node = self.point_dict[start_node_id]
                end_node = self.point_dict[end_node_id]
                nodes[start_node_id] = start_node
                nodes[end_node_id] = end_node

        for node_id, node in nodes.items():
            if node["type"] == LineType.MANHOLE:
                for attr in attributes:
                    if node[attr] in invalid_values:
                        error_msg = f"Manhole with 'connection_node_id' {node_id} is missing '{attr}' value."
                        messagebar_message("Missing values", error_msg, level=Qgis.Warning, duration=5)
                        return False
        return True

    def reset_sideview(self):
        self.route.reset()
        self.map_visualisation.reset()

        self.active_sideview.set_sideprofile([])

    def on_close(self):
        """
        unloading widget and remove all required stuff
        :return:
        """
        self.select_sideview_button.clicked.disconnect(self.toggle_route_tool)
        self.reset_sideview_button.clicked.disconnect(self.reset_sideview)

        self.route_tool.deactivated.disconnect(self.unset_route_tool)

        self.unset_route_tool()

        self.active_sideview.profile_hovered.disconnect(
            self.map_visualisation.hover_graph
        )
        self.map_visualisation.close()

        self.side_view_plot_widget.on_close()

        # todo: find out how to unload layer from memory (done automic if
        # there are no references?)
        QgsProject.instance().removeMapLayer(self.vl_tree_layer.id())
        QgsProject.instance().removeMapLayer(self.graph_layer.id())

    def closeEvent(self, event):
        """
        overwrite of QDockWidget class to emit signal
        :param event: QEvent
        """
        self.on_close()
        self.closingWidget.emit(self.nr)
        event.accept()

    def setup_ui(self):
        """
        initiate main Qt building blocks of interface
        :param dock_widget: QDockWidget instance
        """

        self.setObjectName("dock_widget")
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.dock_widget_content = QWidget(self)
        self.dock_widget_content.setObjectName("dockWidgetContent")

        self.main_vlayout = QVBoxLayout(self)
        self.dock_widget_content.setLayout(self.main_vlayout)

        # add button to add objects to graphs
        self.button_bar_hlayout = QHBoxLayout(self)

        # add title to graph
        self.setWindowTitle(f"3Di Sideview Plot {self.nr}")

        self.select_sideview_button = QPushButton("Choose sideview trajectory", self.dock_widget_content)
        self.select_sideview_button.setObjectName("SelectedSideview")
        self.button_bar_hlayout.addWidget(self.select_sideview_button)

        self.reset_sideview_button = QPushButton("Reset sideview trajectory", self.dock_widget_content)
        self.reset_sideview_button.setObjectName("ResetSideview")
        self.button_bar_hlayout.addWidget(self.reset_sideview_button)

        spacer_item = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.button_bar_hlayout.addItem(spacer_item)
        self.main_vlayout.addItem(self.button_bar_hlayout)

        # add dockwidget
        self.setWidget(self.dock_widget_content)
        QMetaObject.connectSlotsByName(self)
