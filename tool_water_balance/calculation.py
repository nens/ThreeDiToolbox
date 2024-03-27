from collections import defaultdict
from copy import deepcopy
import logging

import numpy as np
import numpy.ma as ma
from qgis.core import QgsCoordinateTransform
from qgis.core import QgsFeatureRequest
from qgis.core import QgsPointXY
from qgis.core import QgsProject
from threedigrid_builder.constants import LineType
from threedigrid_builder.constants import NodeType

from .config import AGG_CUMULATIVE_FLOW
from .config import AGG_FLOW
from .config import GRAPH_SERIES
from .config import INPUT_SERIES
from .config import TIME_UNITS_TO_SECONDS
from .utils import WrappedResult

NO_ENDPOINT_ID = -9999

LINE_TYPES_1D = {
    LineType.LINE_1D_EMBEDDED,
    LineType.LINE_1D_ISOLATED,
    LineType.LINE_1D_CONNECTED,
    LineType.LINE_1D_LONG_CRESTED,
    LineType.LINE_1D_SHORT_CRESTED,
    LineType.LINE_1D_DOUBLE_CONNECTED,
}
LINE_TYPES_1D2D = {
    LineType.LINE_1D2D_SINGLE_CONNECTED_CLOSED,
    LineType.LINE_1D2D_SINGLE_CONNECTED_OPEN_WATER,
    LineType.LINE_1D2D_DOUBLE_CONNECTED_CLOSED,
    LineType.LINE_1D2D_DOUBLE_CONNECTED_OPEN_WATER,
    LineType.LINE_1D2D_POSSIBLE_BREACH,
    LineType.LINE_1D2D_ACTIVE_BREACH,
    LineType.LINE_1D2D_GROUNDWATER,
    58,  # Also LINE_1D2D_GROUNDWATER?
}
NODE_TYPES_1D = {
    NodeType.NODE_1D_NO_STORAGE,
    NodeType.NODE_1D_STORAGE,
    NodeType.NODE_1D_BOUNDARIES,
}
NODE_TYPES_2D = {
    NodeType.NODE_2D_OPEN_WATER,
    NodeType.NODE_2D_BOUNDARIES,
}
NODE_TYPES_2D_GROUNDWATER = {
    NodeType.NODE_2D_GROUNDWATER_BOUNDARIES,
    NodeType.NODE_2D_GROUNDWATER,
}
NODE_TYPES_BOUNDARIES = {
    NodeType.NODE_1D_BOUNDARIES,
    NodeType.NODE_2D_BOUNDARIES,
}

logger = logging.getLogger(__name__)


class WaterBalanceCalculation(object):

    def __init__(self, result, polygon, mapcrs):
        self.wrapped_result = WrappedResult(result)
        self.polygon = polygon
        self.mapcrs = mapcrs

        logger.info("polygon of wb area: %s", self.polygon.asWkt())

        ga = self.wrapped_result.threedi_result.gridadmin

        # total nr of x-dir (horizontal in topview) 2d lines
        nr_2d_x_dir = ga.get_from_meta("liutot")
        # total nr of y-dir (vertical in topview) 2d lines
        nr_2d_y_dir = ga.get_from_meta("livtot")
        # total nr of 2d lines
        nr_2d = ga.get_from_meta("l2dtot")
        # total nr of groundwater lines
        start_gr = ga.get_from_meta("lgrtot")

        # get range of horizontal (in top view) surface water line ids
        x2d_surf_range_min = 1
        x2d_surf_range_max = nr_2d_x_dir
        self.x2d_surf_range = list(
            range(x2d_surf_range_min, x2d_surf_range_max + 1)
        )  # noqa

        # get range of vertical (in top view) surface water line ids
        y2d_surf_range_min = x2d_surf_range_max + 1
        y2d_surf_range_max = x2d_surf_range_max + nr_2d_y_dir
        self.y2d_surf_range = list(range(y2d_surf_range_min, y2d_surf_range_max + 1))

        # get range of vertical (in side view) line ids in the gridadmin.
        # These lines represent surface-groundwater (vertical) flow
        vert_flow_range_min = y2d_surf_range_max + 1
        vert_flow_range_max = y2d_surf_range_max + nr_2d
        self.vert_flow_range = list(range(vert_flow_range_min, vert_flow_range_max + 1))

        if ga.has_groundwater:
            # total nr of x-dir (horizontal in topview) 2d groundwater lines
            x_grndwtr_range_min = start_gr + 1
            x_grndwtr_range_max = start_gr + nr_2d_x_dir
            self.x_grndwtr_range = list(
                range(x_grndwtr_range_min, x_grndwtr_range_max + 1)
            )

            # total nr of y-dir (vertical in topview) 2d groundwater lines
            y_grndwtr_range_min = x_grndwtr_range_max + 1
            y_grndwtr_range_max = x_grndwtr_range_max + nr_2d
            self.y_grndwtr_range = list(
                range(y_grndwtr_range_min, y_grndwtr_range_max + 1)
            )

        line_selection, pump_selection = self._select_lines_and_pumps()
        point_selection = self._select_points()

        def features_to_ids(features):
            return [f["id"] for f in features]

        self.flowline_ids = {
            k: features_to_ids(v) for k, v in line_selection.items()
        }
        self.pump_ids = {
            k: features_to_ids(v) for k, v in pump_selection.items()
        }
        self.node_ids = {
            k: features_to_ids(v) for k, v in point_selection.items()
        }

        self.qgs_lines, self.qgs_points = self.convert_features(
            line_selection=line_selection,
            pump_selection=pump_selection,
            point_selection=point_selection,
        )

        self.time, self.flow = self._get_aggregated_flows()

    @property
    def label(self):
        return self.wrapped_result.parent_text + " | " + self.wrapped_result.text

    def filter_series(self, key, series):
        return [s for s in series if s[key] in self.wrapped_result]

    @property
    def result(self):
        return self.wrapped_result.result

    def _select_lines_and_pumps(self):
        """Returns a tuple of dictionaries with features by category:

        line_selection = {
            '1d_in': [...],
            '1d_out': [...],
            '1d_bound_in': [...],
            ...
        }

        pump_selection = {
            'in': [...],
            'out': [...],
        }

        returned value = (line_selection, pump_selection)
        """
        # TODO: implement model_part. One of the problems of not having
        # this implemented is that the on hover map highlight selects all
        # links, even when the 2D or 1D modelpart is selected in the combo box.

        # the '_out' and '_in' indicate the draw direction of the flow_line.
        # a flow line can have in 1 simulation both positive and negative
        # discharge (with extend to the draw direction). Later on, in
        # get_aggregated_flows() this numpy timeserie is clipped with
        # max=0 for flow in 1 direction and min=0 for flow in the opposite
        # direction.
        line_selection = {
            "1d_in": [],
            "1d_out": [],
            "1d_bound_in": [],
            "1d_bound_out": [],
            "2d_in": [],
            "2d_out": [],
            "2d_bound_in": [],
            "2d_bound_out": [],
            # 1d2d flow lines intersect polygon (1d is inside polygon)
            "1d__1d_2d_flow": [],
            # 1d2d flow lines intersect polygon (2d is inside polygon)
            "2d__1d_2d_flow": [],
            # 1d2d exchange lines are within polygon (both nodes inside)
            "1d_2d_exch": [],
            "2d_groundwater_in": [],
            "2d_groundwater_out": [],
            "2d_vertical_infiltration": [],
            # TODO: add 1d_2d_groundwater?
        }
        pump_selection = {"in": [], "out": []}

        lines = self.wrapped_result.lines
        points = self.wrapped_result.points
        pumps = self.wrapped_result.pumps

        # all links in and out
        # use bounding box and spatial index to prefilter lines
        request_filter = QgsFeatureRequest().setFilterRect(
            self.polygon.get().boundingBox()
        )
        for line in lines.getFeatures(request_filter):
            line_type = line.attribute('line_type')

            if line_type == LineType.LINE_2D_VERTICAL:
                geom = line.geometry().asPolyline()
                # 2d vertical infiltration line is handmade diagonal (drawn
                # from 2d point 15m towards south-west ). Thus, if at-least
                # its startpoint is within polygon then include the line
                if self.polygon.contains(QgsPointXY(geom[0])):
                    line_selection["2d_vertical_infiltration"].append(line)

            # test if lines are crossing boundary of polygon
            if line.geometry().crosses(self.polygon):
                geom = line.geometry().asPolyline()
                # check if flow is in or out by testing if startpoint
                # is inside polygon --> out
                outgoing = self.polygon.contains(QgsPointXY(geom[0]))
                # check if flow is in or out by testing if endpoint
                # is inside polygon --> in
                incoming = self.polygon.contains(QgsPointXY(geom[-1]))

                if incoming and outgoing:
                    # skip lines that do have start- and end vertex outside of
                    # polygon
                    pass
                elif outgoing:
                    if line_type in LINE_TYPES_1D:
                        line_selection["1d_out"].append(line)
                    elif line_type in LINE_TYPES_1D2D:
                        # draw direction of 1d_2d is always from 2d node to
                        # 1d node. So when 2d node is inside polygon (and 1d
                        # node is not) we define it as a '2d__1d_2d_flow' link
                        # because
                        line_selection["2d__1d_2d_flow"].append(line)
                elif incoming:
                    if line_type in LINE_TYPES_1D:
                        line_selection["1d_in"].append(line)
                    elif line_type in LINE_TYPES_1D2D:
                        # draw direction of 1d_2d is always from 2d node to
                        # 1d node. So when 1d node is inside polygon (and 2d
                        # node is not) we define it as a '1d__1d_2d_flow' link
                        line_selection["1d__1d_2d_flow"].append(line)

                if line_type == LineType.LINE_2D and not (incoming and outgoing):
                    # 2d lines are a separate story: discharge on a 2d
                    # link in the nc can be positive and negative during 1
                    # simulation - like you would expect - but we also have
                    # to account for 2d link direction. We have to determine
                    # two things:

                    # A) is 2d link a vertical or horizontal one. Why?
                    # vertical 2d lines (calc cells above each other):
                    # when positive discharge then flow is to north, negative
                    # discharge then flow southwards, while horizontal 2d lines
                    # (calc cells next to each other) yields positive discharge
                    # is flow to the east, negative is flow to west

                    # B) how the start and endpoint are located with
                    # reference to each other. Why? a positive discharge on
                    # a vertical link in the north of your polygon DECREASES
                    # the volume in the polygon, while a positive discharge on
                    # a vertical link in the south of your polygon INCREASES
                    # the volume in the polygon).

                    # so why not only determine (B)?
                    # because then a positive discharge on a diagonal 2d link -
                    # in topview e.g. left up to right down - can mean flow
                    # to east. But it can also mean flow to the north. If we
                    # know it is a vertical link we can be sure flow is to the
                    # north (thats why we need to know (A)

                    # TODO: after I made this code Martijn Siemerink adviced:
                    # 2d links drawing direction is always from south to north
                    # OR west to east, so it not required to get start- and
                    # endpoint of a 2d link

                    start_x = geom[0][0]
                    start_y = geom[0][1]
                    end_x = geom[-1][0]
                    end_y = geom[-1][1]

                    # horizontal line?
                    if line.id() in self.x2d_surf_range:
                        # startpoint in polygon?
                        if self.polygon.contains(QgsPointXY(geom[0])):
                            # directed to east?
                            # long coords increase going east, so:
                            if end_x > start_x:
                                # thus, positive q means flow to east.
                                # Startpoint is in polygon. Endpoint is
                                # located eastwards of startpoint, so positive
                                # q means flow goes OUT!! of polygon
                                line_selection["2d_out"].append(line)
                            else:
                                line_selection["2d_in"].append(line)
                        # endpoint in polygon?
                        elif self.polygon.contains(QgsPointXY(geom[-1])):
                            # directed to east?
                            # long coords increase going east
                            if end_x > start_x:
                                # positive q means flow to east. Endpoint is
                                # inside polygon and located eastwards of
                                # startpoint, so positive q means flow goes
                                # INTO!! polygon
                                line_selection["2d_in"].append(line)
                            else:
                                line_selection["2d_out"].append(line)

                    # vertical line?
                    if line.id() in self.y2d_surf_range:
                        # startpoint in polygon?
                        if self.polygon.contains(QgsPointXY(geom[0])):
                            # directed to north?
                            # lat coords increase going north, so:
                            if end_y > start_y:
                                # thus, positive q means flow to north.
                                # Startpoint is in polygon. Endpoint is
                                # located northwards of startpoint, so positive
                                # q means flow goes OUT!! of polygon
                                line_selection["2d_out"].append(line)
                            else:
                                line_selection["2d_in"].append(line)
                        # endpoint in polygon?
                        elif self.polygon.contains(QgsPointXY(geom[-1])):
                            # directed to north?
                            # lat coords increase going north, so:
                            if end_y > start_y:
                                # positive q means flow to north. Endpoint is
                                # inside polygon and located northwards of
                                # startpoint, so flow goes INTO!! polygon
                                line_selection["2d_in"].append(line)
                            else:
                                line_selection["2d_out"].append(line)

                if line_type == LineType.LINE_2D_GROUNDWATER and not (incoming and outgoing):

                    start_x = geom[0][0]
                    start_y = geom[0][1]
                    end_x = geom[-1][0]
                    end_y = geom[-1][1]

                    # horizontal line?
                    if line.id() in self.x_grndwtr_range:
                        # startpoint in polygon?
                        if self.polygon.contains(QgsPointXY(geom[0])):
                            if end_x > start_x:
                                line_selection["2d_groundwater_out"].append(line)
                            else:
                                line_selection["2d_groundwater_in"].append(line)
                        # endpoint in polygon?
                        elif self.polygon.contains(QgsPointXY(geom[-1])):
                            if end_x > start_x:
                                line_selection["2d_groundwater_in"].append(line)
                            else:
                                line_selection["2d_groundwater_out"].append(line)
                    # vertical line?
                    if line.id() in self.y_grndwtr_range:
                        # startpoint in polygon?
                        if self.polygon.contains(QgsPointXY(geom[0])):
                            if end_y > start_y:
                                line_selection["2d_groundwater_out"].append(line)
                            else:
                                line_selection["2d_groundwater_in"].append(line)
                        elif self.polygon.contains(QgsPointXY(geom[-1])):
                            if end_y > start_y:
                                line_selection["2d_groundwater_in"].append(line)
                            else:
                                line_selection["2d_groundwater_out"].append(line)

            elif line_type in LINE_TYPES_1D2D and line.geometry().within(self.polygon):
                line_selection["1d_2d_exch"].append(line)

        # find boundaries in polygon
        node_types_csv = ",".join(str(n.value) for n in NODE_TYPES_BOUNDARIES)
        request_filter = (
            QgsFeatureRequest()
            .setFilterRect(self.polygon.get().boundingBox())
            .setFilterExpression(f"node_type in ({node_types_csv})")
        )

        # all boundaries in polygon
        for bound in points.getFeatures(request_filter):
            if self.polygon.contains(QgsPointXY(bound.geometry().asPoint())):
                # find link connected to boundary
                request_filter_bound = QgsFeatureRequest().setFilterExpression(
                    f"calculation_node_id_start == {bound.id()} OR"
                    f"calculation_node_id_end == {bound.id()}"
                )
                bound_lines = lines.getFeatures(request_filter_bound)
                for bound_line in bound_lines:
                    if bound_line["calculation_node_id_start"] == bound["id"]:
                        if bound["node_type"] == NodeType.NODE_1D_BOUNDARIES:
                            line_selection["1d_bound_in"].append(bound_line)
                        else:  # 2d
                            line_selection["2d_bound_in"].append(bound_line)
                    else:  # out
                        if bound["node_type"] == NodeType.NODE_1D_BOUNDARIES:
                            line_selection["1d_bound_out"].append(bound_line)
                        else:  # 2d
                            line_selection["2d_bound_out"].append(bound_line)

        # pumps
        # use bounding box and spatial index to prefilter pumps
        if pumps is None:
            f_pumps = []
        else:
            request_filter = QgsFeatureRequest().setFilterRect(
                self.polygon.get().boundingBox()
            )
            f_pumps = pumps.getFeatures(request_filter)

        for pump in f_pumps:
            # test if lines are crossing boundary of polygon
            pump_geometry = pump.geometry()
            if pump_geometry.intersects(self.polygon):
                pump_end_node_id = pump["node_idx2"]
                linestring = pump_geometry.asPolyline()
                # check if flow is in or out by testing if startpoint
                # is inside polygon --> out
                startpoint = QgsPointXY(linestring[0])
                endpoint = QgsPointXY(linestring[-1])
                outgoing = self.polygon.contains(startpoint)
                # check if flow is in or out by testing if endpoint
                # is inside polygon --> in
                incoming = self.polygon.contains(endpoint) if not pump_end_node_id == NO_ENDPOINT_ID else False

                if incoming and outgoing:
                    # skip
                    pass
                elif outgoing:
                    pump_selection["out"].append(pump)
                elif incoming:
                    pump_selection["in"].append(pump)

        return line_selection, pump_selection

    def _select_points(self):
        """Returns a dictionary with features by category:

        {
            '1d': [..., ...],
            '2d': [..., ...],
            '2d_groundwater': [..., ...],
        }
        """

        point_selection = {"1d": [], "2d": [], "2d_groundwater": []}

        # use bounding box and spatial index to prefilter lines
        request_filter = QgsFeatureRequest().setFilterRect(
            self.polygon.get().boundingBox()
        )
        node_types = NODE_TYPES_1D | NODE_TYPES_2D | NODE_TYPES_2D_GROUNDWATER
        node_types_csv = ",".join(str(n.value) for n in node_types)
        request_filter.setFilterExpression(f"node_type in ({node_types_csv})")
        # todo: check if boundary nodes could not have rain, infiltration, etc.

        node_type_map = {}
        node_type_map.update({n.value: "1d" for n in NODE_TYPES_1D})
        node_type_map.update({n.value: "2d" for n in NODE_TYPES_2D})
        node_type_map.update({n.value: "2d_groundwater"
                              for n in NODE_TYPES_2D_GROUNDWATER})

        for point in self.wrapped_result.points.getFeatures(request_filter):
            # test if points are contained by polygon
            if self.polygon.contains(point.geometry()):
                point_selection[node_type_map[point['node_type']]].append(point)
        return point_selection

    def _get_aggregated_flows(self):
        """
        Returns a tuple (times, all_flows) defined as:

            times = array of timestamps
            all_flows = array with shape (np.size(times, 0), len(INPUT_SERIES))
        """
        # constants referenced in record array
        # shared by links and nodes
        TYPE_1D = "1d"
        TYPE_2D = "2d"
        TYPE_2D_GROUNDWATER = "2d_groundwater"
        # links only
        TYPE_1D_BOUND_IN = "1d_bound_in"
        TYPE_2D_BOUND_IN = "2d_bound_in"
        TYPE_1D__1D_2D_EXCH = "1d__1d_2d_exch"
        TYPE_2D__1D_2D_EXCH = "2d__1d_2d_exch"
        TYPE_1D__1D_2D_FLOW = "1d__1d_2d_flow"
        TYPE_2D__1D_2D_FLOW = "2d__1d_2d_flow"
        TYPE_2D_VERTICAL_INFILTRATION = "2d_vertical_infiltration"

        ALL_TYPES = [
            TYPE_1D,
            TYPE_2D,
            TYPE_2D_GROUNDWATER,
            TYPE_1D_BOUND_IN,
            TYPE_2D_BOUND_IN,
            TYPE_1D__1D_2D_EXCH,
            TYPE_2D__1D_2D_EXCH,
            TYPE_1D__1D_2D_FLOW,
            TYPE_2D__1D_2D_FLOW,
            TYPE_2D_VERTICAL_INFILTRATION,
        ]

        NTYPE_MAXLEN = 25
        assert (
            max(list(map(len, ALL_TYPES))) <= NTYPE_MAXLEN
        ), "NTYPE_MAXLEN insufficiently large for all values"
        NTYPE_DTYPE = "U%s" % NTYPE_MAXLEN

        # LINKS
        #######

        # create numpy table with flowlink information
        tlink = []  # id, 1d or 2d, in or out
        for idx in self.flowline_ids["2d_in"]:
            tlink.append((idx, TYPE_2D, 1))
        for idx in self.flowline_ids["2d_out"]:
            tlink.append((idx, TYPE_2D, -1))

        for idx in self.flowline_ids["2d_bound_in"]:
            tlink.append((idx, TYPE_2D_BOUND_IN, 1))
        for idx in self.flowline_ids["2d_bound_out"]:
            tlink.append((idx, TYPE_2D_BOUND_IN, -1))

        for idx in self.flowline_ids["1d_in"]:
            tlink.append((idx, TYPE_1D, 1))
        for idx in self.flowline_ids["1d_out"]:
            tlink.append((idx, TYPE_1D, -1))

        for idx in self.flowline_ids["1d_bound_in"]:
            tlink.append((idx, TYPE_1D_BOUND_IN, 1))
        for idx in self.flowline_ids["1d_bound_out"]:
            tlink.append((idx, TYPE_1D_BOUND_IN, -1))

        for idx in self.flowline_ids["2d_groundwater_in"]:
            tlink.append((idx, TYPE_2D_GROUNDWATER, 1))
        for idx in self.flowline_ids["2d_groundwater_out"]:
            tlink.append((idx, TYPE_2D_GROUNDWATER, -1))

        for idx in self.flowline_ids["2d_vertical_infiltration"]:
            tlink.append((idx, TYPE_2D_VERTICAL_INFILTRATION, 1))

        # 1d_2d flow intersects the polygon:
        # the in- or out flow for 1d2d is different than flows dirs above:
        #   - discharge from 1d to 2d is always positive in the .nc
        #   - discharge from 2d to 1d is always negative in the .nc
        # 1d__1d_2d_flow: 1d node is inside polygon, 2d node is outside.
        #   - positive discharge means flow outwards polygon
        #   - negative discharge means flow inwards polygon
        # 2d__1d_2d_flow: 1d node is outside polygon, 2d node is inside
        #   - positive discharge means flow inwards polygon
        #   - negative discharge means flow outwards polygon
        for idx in self.flowline_ids["1d__1d_2d_flow"]:
            tlink.append((idx, TYPE_1D__1D_2D_FLOW, -1))
        # 1d_2d_out: 1d node is outside polygon, 2d node is inside
        for idx in self.flowline_ids["2d__1d_2d_flow"]:
            tlink.append((idx, TYPE_2D__1D_2D_FLOW, 1))
        # 1d_2d within the polygon (from 1d perspective so everything flipped)
        for idx in self.flowline_ids["1d_2d_exch"]:
            tlink.append((idx, TYPE_1D__1D_2D_EXCH, -1))
        # 1d_2d within the polygon (from 2d perspective)
        for idx in self.flowline_ids["1d_2d_exch"]:
            tlink.append((idx, TYPE_2D__1D_2D_EXCH, 1))

        np_link = np.array(
            tlink, dtype=[("id", int), ("ntype", NTYPE_DTYPE), ("dir", int)]
        )

        # sort for faster reading of netcdf
        np_link.sort(axis=0)

        # create masks
        mask_2d = np_link["ntype"] != TYPE_2D
        mask_1d = np_link["ntype"] != TYPE_1D
        mask_2d_bound = np_link["ntype"] != TYPE_2D_BOUND_IN
        mask_1d_bound = np_link["ntype"] != TYPE_1D_BOUND_IN

        mask_1d__1d_2d_flow = np_link["ntype"] != TYPE_1D__1D_2D_FLOW
        mask_2d__1d_2d_flow = np_link["ntype"] != TYPE_2D__1D_2D_FLOW
        mask_1d__1d_2d_exch = np_link["ntype"] != TYPE_1D__1D_2D_EXCH
        mask_2d__1d_2d_exch = np_link["ntype"] != TYPE_2D__1D_2D_EXCH
        mask_2d_groundwater = np_link["ntype"] != TYPE_2D_GROUNDWATER
        mask_2d_vertical_infiltration = (
            np_link["ntype"] != TYPE_2D_VERTICAL_INFILTRATION
        )

        threedi_result = self.wrapped_result.threedi_result

        # get all flows through incoming and outgoing flows
        times = threedi_result.get_timestamps(parameter="q_cum")

        all_flows = np.zeros(shape=(len(times), len(INPUT_SERIES)))
        # total_location = np.zeros(shape=(np.size(np_link, 0), 2))

        # non-2d links
        pos_pref = 0
        neg_pref = 0

        if np_link.size > 0:
            for ts_idx, t in enumerate(times):
                # (1) inflow and outflow through 1d and 2d
                # vol = threedi_result.get_values_by_timestep_nr('q', ts_idx,
                # np_link['id']) * np_link['dir']  # * dt

                flow_pos = (
                    threedi_result.get_values_by_timestep_nr(
                        "q_cum_positive", ts_idx, np_link["id"]
                    )
                    * np_link["dir"]
                )
                flow_neg = (
                    threedi_result.get_values_by_timestep_nr(
                        "q_cum_negative", ts_idx, np_link["id"]
                    )
                    * np_link["dir"]
                    * -1
                )

                in_sum = flow_pos - pos_pref
                out_sum = flow_neg - neg_pref
                pos_pref = flow_pos
                neg_pref = flow_neg

                # 2d flow (2d_in)
                all_flows[ts_idx, 0] = (
                    ma.masked_array(in_sum, mask=mask_2d).clip(min=0).sum()
                    + ma.masked_array(out_sum, mask=mask_2d).clip(min=0).sum()
                )
                # 2d flow (2d_out)
                all_flows[ts_idx, 1] = (
                    ma.masked_array(in_sum, mask=mask_2d).clip(max=0).sum()
                    + ma.masked_array(out_sum, mask=mask_2d).clip(max=0).sum()
                )

                # 1d flow (1d_in)
                all_flows[ts_idx, 2] = (
                    ma.masked_array(in_sum, mask=mask_1d).clip(min=0).sum()
                    + ma.masked_array(out_sum, mask=mask_1d).clip(min=0).sum()
                )
                # 1d flow (1d_out)
                all_flows[ts_idx, 3] = (
                    ma.masked_array(in_sum, mask=mask_1d).clip(max=0).sum()
                    + ma.masked_array(out_sum, mask=mask_1d).clip(max=0).sum()
                )

                # 2d bound (2d_bound_in)
                all_flows[ts_idx, 4] = (
                    ma.masked_array(in_sum, mask=mask_2d_bound).clip(min=0).sum()
                    + ma.masked_array(out_sum, mask=mask_2d_bound).clip(min=0).sum()
                )
                # 2d bound (2d_bound_out)
                all_flows[ts_idx, 5] = (
                    ma.masked_array(in_sum, mask=mask_2d_bound).clip(max=0).sum()
                    + ma.masked_array(out_sum, mask=mask_2d_bound).clip(max=0).sum()
                )

                # 1d bound (1d_bound_in)
                all_flows[ts_idx, 6] = (
                    ma.masked_array(in_sum, mask=mask_1d_bound).clip(min=0).sum()
                    + ma.masked_array(out_sum, mask=mask_1d_bound).clip(min=0).sum()
                )
                # 1d bound (1d_bound_out)
                all_flows[ts_idx, 7] = (
                    ma.masked_array(in_sum, mask=mask_1d_bound).clip(max=0).sum()
                    + ma.masked_array(out_sum, mask=mask_1d_bound).clip(max=0).sum()
                )

                # 1d__1d_2d_flow_in
                all_flows[ts_idx, 8] = (
                    ma.masked_array(in_sum, mask=mask_1d__1d_2d_flow).clip(min=0).sum()
                    + ma.masked_array(out_sum, mask=mask_1d__1d_2d_flow)
                    .clip(min=0)
                    .sum()
                )
                # 1d__1d_2d_flow_out
                all_flows[ts_idx, 9] = (
                    ma.masked_array(in_sum, mask=mask_1d__1d_2d_flow).clip(max=0).sum()
                    + ma.masked_array(out_sum, mask=mask_1d__1d_2d_flow)
                    .clip(max=0)
                    .sum()
                )

                # 2d__1d_2d_flow_in
                all_flows[ts_idx, 30] = (
                    ma.masked_array(in_sum, mask=mask_2d__1d_2d_flow).clip(min=0).sum()
                    + ma.masked_array(out_sum, mask=mask_2d__1d_2d_flow)
                    .clip(min=0)
                    .sum()
                )
                # 2d__1d_2d_flow_out
                all_flows[ts_idx, 31] = (
                    ma.masked_array(in_sum, mask=mask_2d__1d_2d_flow).clip(max=0).sum()
                    + ma.masked_array(out_sum, mask=mask_2d__1d_2d_flow)
                    .clip(max=0)
                    .sum()
                )

                # 1d (1d__1d_2d_exch_in)
                all_flows[ts_idx, 10] = (
                    ma.masked_array(in_sum, mask=mask_1d__1d_2d_exch).clip(min=0).sum()
                    + ma.masked_array(out_sum, mask=mask_1d__1d_2d_exch)
                    .clip(min=0)
                    .sum()
                )
                # 1d (1d__1d_2d_exch_out)
                all_flows[ts_idx, 11] = (
                    ma.masked_array(in_sum, mask=mask_1d__1d_2d_exch).clip(max=0).sum()
                    + ma.masked_array(out_sum, mask=mask_1d__1d_2d_exch)
                    .clip(max=0)
                    .sum()
                )

                # 2d (2d__1d_2d_exch_in)
                all_flows[ts_idx, 32] = (
                    ma.masked_array(in_sum, mask=mask_2d__1d_2d_exch).clip(min=0).sum()
                    + ma.masked_array(out_sum, mask=mask_2d__1d_2d_exch)
                    .clip(min=0)
                    .sum()
                )
                # 2d (2d__1d_2d_exch_out)
                all_flows[ts_idx, 33] = (
                    ma.masked_array(in_sum, mask=mask_2d__1d_2d_exch).clip(max=0).sum()
                    + ma.masked_array(out_sum, mask=mask_2d__1d_2d_exch)
                    .clip(max=0)
                    .sum()
                )

                # 2d groundwater (2d_groundwater_in)
                all_flows[ts_idx, 23] = (
                    ma.masked_array(in_sum, mask=mask_2d_groundwater).clip(min=0).sum()
                    + ma.masked_array(out_sum, mask=mask_2d_groundwater)
                    .clip(min=0)
                    .sum()
                )
                # 2d groundwater (2d_groundwater_out)
                all_flows[ts_idx, 24] = (
                    ma.masked_array(in_sum, mask=mask_2d_groundwater).clip(max=0).sum()
                    + ma.masked_array(out_sum, mask=mask_2d_groundwater)
                    .clip(max=0)
                    .sum()
                )

                # NOTE: positive vertical infiltration is from surface to
                # groundwater node. We make this negative because it's
                # 'sink-like', and to make it in line with the
                # infiltration_rate_simple which also has a -1 multiplication
                # factor.
                # 2d_vertical_infiltration (2d_vertical_infiltration_pos)
                all_flows[ts_idx, 28] = (
                    -1
                    * ma.masked_array(in_sum, mask=mask_2d_vertical_infiltration)
                    .clip(min=0)
                    .sum()
                    + ma.masked_array(out_sum, mask=mask_2d_vertical_infiltration)
                    .clip(min=0)
                    .sum()
                )
                # 2d_vertical_infiltration (2d_vertical_infiltration_neg)
                all_flows[ts_idx, 29] = (
                    -1
                    * ma.masked_array(in_sum, mask=mask_2d_vertical_infiltration)
                    .clip(max=0)
                    .sum()
                    + ma.masked_array(out_sum, mask=mask_2d_vertical_infiltration)
                    .clip(max=0)
                    .sum()
                )

        # PUMPS
        #######

        tpump = []
        for idx in self.pump_ids["in"]:
            tpump.append((idx, 1))
        for idx in self.pump_ids["out"]:
            tpump.append((idx, -1))
        np_pump = np.array(tpump, dtype=[("id", int), ("dir", int)])
        np_pump.sort(axis=0)

        if np_pump.size > 0:
            # pumps
            pump_pref = 0
            for ts_idx, t in enumerate(times):
                # (2) inflow and outflow through pumps
                pump_flow = (
                    threedi_result.get_values_by_timestep_nr(
                        "q_pump_cum", ts_idx, np_pump["id"]
                    )
                    * np_pump["dir"]
                )

                flow_dt = pump_flow - pump_pref
                pump_pref = pump_flow

                in_sum = flow_dt.clip(min=0)
                out_sum = flow_dt.clip(max=0)

                all_flows[ts_idx, 12] = in_sum.sum()
                all_flows[ts_idx, 13] = out_sum.sum()

        # NODES
        #######

        tnode = []  # id, 1d or 2d, in or out
        for idx in self.node_ids["2d"]:
            tnode.append((idx, TYPE_2D))
        for idx in self.node_ids["1d"]:
            tnode.append((idx, TYPE_1D))
        for idx in self.node_ids["2d_groundwater"]:
            tnode.append((idx, TYPE_2D_GROUNDWATER))
        NTYPE_DTYPE
        np_node = np.array(tnode, dtype=[("id", int), ("ntype", NTYPE_DTYPE)])
        np_node.sort(axis=0)

        mask_2d_nodes = np_node["ntype"] != TYPE_2D
        mask_1d_nodes = np_node["ntype"] != TYPE_1D
        mask_2d_groundwater_nodes = np_node["ntype"] != TYPE_2D_GROUNDWATER

        np_2d_node = ma.masked_array(np_node["id"], mask=mask_2d_nodes).compressed()
        np_1d_node = ma.masked_array(np_node["id"], mask=mask_1d_nodes).compressed()
        np_2d_groundwater_node = ma.masked_array(
            np_node["id"], mask=mask_2d_groundwater_nodes
        ).compressed()

        for parameter, agg_method, node, pnr, factor in [
            ("rain", "_cum", np_2d_node, 14, 1),
            # TODO: in old model results this parameter is called
            # 'infiltration_rate', thus it is not backwards compatible right
            # now
            ("infiltration_rate_simple", "_cum", np_2d_node, 15, -1),
            # TODO: inefficient because we look up q_lat data twice
            ("q_lat", "_cum", np_2d_node, 16, 1),
            ("q_lat", "_cum", np_1d_node, 17, 1),
            ("leak", "_cum", np_2d_groundwater_node, 26, 1),
            ("rain", "_cum", np_1d_node, 27, 1),
            ("intercepted_volume", "_current", np_2d_node, 34, -1),
            ("q_sss", "_cum", np_2d_node, 35, 1),
        ]:

            if node.size > 0:
                if parameter + agg_method in threedi_result.available_vars:
                    values_pref = 0
                    for ts_idx, t in enumerate(times):
                        values = threedi_result.get_values_by_timestep_nr(
                            parameter + agg_method, ts_idx, node
                        ).sum()
                        values_dt = values - values_pref
                        values_pref = values
                        all_flows[ts_idx, pnr] = values_dt * factor
        t_pref = 0

        for ts_idx, t in enumerate(times):
            if ts_idx == 0:
                # just to make sure machine precision distortion
                # is reduced for the first timestamp (everything
                # should be 0
                all_flows[ts_idx] = all_flows[ts_idx] / (times[1] - t)
            else:
                all_flows[ts_idx] = all_flows[ts_idx] / (t - t_pref)
                t_pref = t

        if np_node.size > 0:
            # delta volume
            t_pref = 0
            for ts_idx, t in enumerate(times):
                # delta volume
                if ts_idx == 0:
                    # volume difference first timestep is always 0
                    all_flows[ts_idx, 18] = 0
                    all_flows[ts_idx, 19] = 0
                    all_flows[ts_idx, 25] = 0

                    vol_current = threedi_result.get_values_by_timestep_nr(
                        "vol_current", ts_idx, np_node["id"]
                    )
                    td_vol_pref = ma.masked_array(vol_current, mask=mask_2d_nodes).sum()
                    od_vol_pref = ma.masked_array(vol_current, mask=mask_1d_nodes).sum()
                    td_vol_pref_gw = ma.masked_array(
                        vol_current, mask=mask_2d_groundwater_nodes
                    ).sum()
                    t_pref = t
                else:
                    vol_current = threedi_result.get_values_by_timestep_nr(
                        "vol_current", ts_idx, np_node["id"]
                    )

                    td_vol = ma.masked_array(vol_current, mask=mask_2d_nodes).sum()
                    od_vol = ma.masked_array(vol_current, mask=mask_1d_nodes).sum()
                    td_vol_gw = ma.masked_array(
                        vol_current, mask=mask_2d_groundwater_nodes
                    ).sum()

                    dt = t - t_pref
                    all_flows[ts_idx, 18] = (td_vol - td_vol_pref) / dt
                    all_flows[ts_idx, 19] = (od_vol - od_vol_pref) / dt
                    all_flows[ts_idx, 25] = (td_vol_gw - td_vol_pref_gw) / dt

                    td_vol_pref = td_vol
                    od_vol_pref = od_vol
                    td_vol_pref_gw = td_vol_gw
                    t_pref = t
        all_flows = np.nan_to_num(all_flows)

        return times, all_flows

    def convert_features(self, line_selection, pump_selection, point_selection):
        """
        Return lines, points tuple of dicts, for the visualization
        """
        transform = QgsCoordinateTransform(
            self.wrapped_result.lines.crs(), self.mapcrs, QgsProject.instance(),
        )
        qgs_lines = defaultdict(list)
        for c, fl in line_selection.items():
            for f in fl:
                geom = f.geometry()
                geom.transform(transform)
                geom = geom.asPolyline()
                qgs_lines[c.rsplit('_in')[0].rsplit('_out')[0]].append(geom)
        qgs_points = defaultdict(list)
        for c, fl in pump_selection.items():
            for f in fl:
                geom = f.geometry()
                geom.transform(transform)
                geom = geom.asPoint()
                qgs_points["pumps_hoover"].append(geom)
        for c, fl in point_selection.items():
            for f in fl:
                geom = f.geometry()
                geom.transform(transform)
                geom = geom.asPoint()
                qgs_points[c].append(geom)
        return qgs_lines, qgs_points

    def get_graph_data(self, agg, time_units):
        """
        Return data corresponding to the graph series.
        """
        time = self.time
        flow = self.flow

        flow_index = dict(INPUT_SERIES)

        graph_data = deepcopy(GRAPH_SERIES)
        for idx, item in enumerate(graph_data):
            item["fill_color"] = [
                int(c) for c in item["def_fill_color"].split(",")
            ]
            item["pen_color"] = [
                int(c) for c in item["def_pen_color"].split(",")
            ]
            # determine the flow indices for this items series
            flow_indices = [
                flow_index[serie] for serie in item["series"]
            ]

            # populate with data from flow
            item["values"] = {}
            assert item["default_method"] in ("net", "gross")
            if item["default_method"] == "net":
                sum = flow[:, flow_indices].sum(axis=1)
                item["values"]["in"] = sum.clip(min=0)
                item["values"]["out"] = sum.clip(max=0)
            elif item["default_method"] == "gross":
                sum_pos = np.zeros(shape=(np.size(time, 0),))
                sum_neg = np.zeros(shape=(np.size(time, 0),))
                for nr in flow_indices:
                    sum_pos += flow[:, nr].clip(min=0)
                    sum_neg += flow[:, nr].clip(max=0)
                item["values"]["in"] = sum_pos
                item["values"]["out"] = sum_neg

            if agg == AGG_CUMULATIVE_FLOW:
                # aggregate the serie
                diff = np.append([0], np.diff(time))
                item["values"]["in"] = np.cumsum(
                    diff * item["values"]["in"], axis=0
                )
                item["values"]["out"] = np.cumsum(
                    diff * item["values"]["out"], axis=0
                )

        time = self.time / TIME_UNITS_TO_SECONDS[time_units]
        agg_label = {
            AGG_FLOW: ("Flow", "m³/s"),
            AGG_CUMULATIVE_FLOW: ("Cumulative flow", "m³"),
        }[agg]

        return {
            "time": time,
            "time_label": ("time", time_units),
            "values": {item["name"]: item for item in graph_data},
            "values_label": agg_label
        }
