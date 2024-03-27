import numpy as np
from typing import List, Tuple, Union

from osgeo import ogr

from shapely.geometry import Point, LineString, MultiLineString, MultiPoint
from threedigrid.admin.gridresultadmin import GridH5ResultAdmin
from threedigrid.admin.lines.models import Lines

from threedi_results_analysis.utils.threedi_result_aggregation.aggregation_classes import (
    Aggregation,
    AggregationSign,
)
from threedi_results_analysis.utils.threedi_result_aggregation.constants import (
    AGGREGATION_VARIABLES,
    AGGREGATION_METHODS,
)
from threedi_results_analysis.utils.threedi_result_aggregation.base import (
    prepare_timeseries,
    aggregate_prepared_timeseries,
)
from threedi_results_analysis.utils.threedi_result_aggregation.threedigrid_ogr import threedigrid_to_ogr


Q_NET_SUM = Aggregation(
    variable=AGGREGATION_VARIABLES.get_by_short_name("q"),
    method=AGGREGATION_METHODS.get_by_short_name("sum"),
    sign=AggregationSign("net", "Net"),
)


def intersected_segments(
    line: Union[LineString, MultiLineString], intersecting_line: LineString
) -> List[LineString]:
    """
    Returns the segments of `line` that are intersected by `intersecting_line`.

    If a line segment is intersected multiple times, it is returned multiple times.
    """
    if not line.intersects(intersecting_line):
        return []
    if type(line) == MultiLineString:
        lines = line.geoms
    elif type(line) == LineString:
        lines = [line]
    else:
        raise TypeError("line is not a LineString or MultiLinestring")
    for single_line in lines:
        line_segments = [
            LineString([single_line.coords[i], single_line.coords[i + 1]])
            for i in range(len(single_line.coords) - 1)
        ]
        intersection = single_line.intersection(intersecting_line)
        intersection_points = (
            intersection.geoms
            if type(intersection) == MultiPoint
            else [intersection]
        )
        result = []
        for line_segment in line_segments:
            for point in intersection_points:
                if point.distance(line_segment) < 10e-9:
                    result.append(line_segment)
    return result


def is_left_of_line(point: Point, line: LineString) -> Union[bool, None]:
    """
    Is `point` to the left of `line`?

    Returns None if `point` intersects `line`

    Based on:
    https://stackoverflow.com/questions/1560492/how-to-tell-whether-a-point-is-to-the-right-or-left-side-of-a-line

    :param point: the Point to analyse
    :param line: LineString with 2 vertices
    """
    assert len(line.coords) == 2
    if point.intersects(line):
        return None
    start, end = [Point(coord) for coord in line.coords]
    return (
        (end.x - start.x) * (point.y - start.y)
        - (end.y - start.y) * (point.x - start.x)
    ) > 0


def flowline_start_nodes_left_of_line(
    flowlines: Lines, gauge_line: LineString
) -> List[bool]:
    result = []
    for i in range(flowlines.count):
        line_coords = flowlines.line_coords[:, i]
        shapely_flowline = LineString(
            [
                Point((line_coords[0], line_coords[1])),
                Point((line_coords[2], line_coords[3])),
            ]
        )
        gauge_line_segments = intersected_segments(
            line=gauge_line, intersecting_line=shapely_flowline
        )
        if len(gauge_line_segments) == 0:
            continue
        elif len(gauge_line_segments) > 1:
            raise ValueError(
                f"Gauge line intersects flowline {flowlines.id[i]} multiple times"
            )
        else:
            gauge_line_segment = gauge_line_segments[0]
        shapely_flowline_start_point = Point(flowlines.line_coords[0:2, i])
        result.append(
            is_left_of_line(shapely_flowline_start_point, gauge_line_segment)
        )
    return result


def left_to_right_discharge(
    gr: GridH5ResultAdmin,
    gauge_line: LineString,
    start_time: float = None,
    end_time: float = None,
    subset: str = None,
    content_types: List[str] = None,
) -> Tuple[Lines, List[bool], np.array, np.array, float]:
    """
    Calculate the total net discharge from the left of a `gauge_line` to the right of that gauge line

    `content_types` can be specified to filter 1D line types (further filters the given subset). does not affect
    filtering of lines with `content_type` == ''

    :returns: tuple of: Lines that intersect `gauge_line`,
    List of boolean values indicating if these lines' drawing directions are left-to-right
    timeseries of total discharge in left -> right direction,
    sum of net discharge per flowline in left -> right direction,
    total left -> right discharge
    """
    intersecting_lines = gr.lines.filter(
        line_coords__intersects_bbox=gauge_line.bounds
    ).filter(line_coords__intersects_geometry=gauge_line)
    if subset:
        intersecting_lines = intersecting_lines.subset(subset)
    if content_types:
        # filtering on content_type only affects flowlines with a content_type (i.e. 1D flowlines)
        # therefore we append b''
        content_types.append("")
        # 1D/2D flowlines between an added calculation point and a 2D node should are not affected either
        # therefore we append v2_added_c
        content_types.append("v2_added_c")
        # convert to bytes because filtering with a mix of empty and non-empty strings does not work otherwise
        content_types = [s.encode("utf-8") for s in content_types]
        intersecting_lines = intersecting_lines.filter(
            content_type__in=content_types
        )
    ts, tintervals = prepare_timeseries(
        nodes_or_lines=intersecting_lines,
        start_time=start_time,
        end_time=end_time,
        aggregation=Q_NET_SUM,
    )
    agg_by_flowline = aggregate_prepared_timeseries(
        timeseries=ts,
        tintervals=tintervals,
        start_time=start_time,
        aggregation=Q_NET_SUM,
    )
    is_left_to_right = flowline_start_nodes_left_of_line(
        flowlines=intersecting_lines, gauge_line=gauge_line
    )
    direction = np.where(is_left_to_right, 1, -1)
    agg_by_flowline_left_to_right = agg_by_flowline * direction
    summed_vals = np.nansum(agg_by_flowline_left_to_right)
    ts_left_to_right = np.multiply(ts, direction)
    ts_values_gauge_line = np.sum(ts_left_to_right, axis=1)
    if not start_time:
        start_time = 0
    timesteps = np.cumsum(np.concatenate(([0], tintervals[:-1]))) + start_time
    ts_gauge_line = np.dstack([timesteps, ts_values_gauge_line]).squeeze()

    return (
        intersecting_lines,
        is_left_to_right,
        ts_gauge_line,
        agg_by_flowline_left_to_right,
        summed_vals,
    )


def left_to_right_discharge_ogr(
    gr: GridH5ResultAdmin,
    gauge_line: LineString,
    tgt_ds: ogr.DataSource,
    start_time: float = None,
    end_time: float = None,
    subset: str = None,
    content_types: List[str] = None,
    gauge_line_id: int = None,
) -> Tuple[np.array, float]:
    """
    Calculate the total net discharge from the left of a `gauge_line` to the right of that gauge line

    Writes the flowlines with attribute 'q_net_sum' to provided `tgt_ds`. Flowline geometries always have their start
    vertex left of the gauge line

    `content_types` can be specified to filter 1D line types (further filters the given subset). does not affect
    filtering of lines with `content_type` == ''

    :returns: total left -> right discharge
    """
    (
        intersecting_lines,
        is_left_to_right,
        ts_gauge_line,
        q_net_sum_left_to_right,
        summed_vals,
    ) = left_to_right_discharge(
        gr=gr,
        gauge_line=gauge_line,
        start_time=start_time,
        end_time=end_time,
        subset=subset,
        content_types=content_types,
    )
    gauge_line_ids = [gauge_line_id] * intersecting_lines.count
    attributes = {
        "gauge_line_id": gauge_line_ids,
        "q_net_sum": q_net_sum_left_to_right,
    }
    attr_data_types = {
        "gauge_line_id": ogr.OFTInteger,
        "q_net_sum": ogr.OFTReal,
    }
    threedigrid_to_ogr(
        threedigrid_src=intersecting_lines,
        tgt_ds=tgt_ds,
        attributes=attributes,
        attr_data_types=attr_data_types,
        include_all_threedigrid_attributes=True
    )
    ogr_lyr = tgt_ds.GetLayerByName("flowline")
    for i, feature in enumerate(ogr_lyr):
        if is_left_to_right[i]:
            geom = feature.GetGeometryRef()
            points = geom.GetPoints()
            points.reverse()
            reversed_geom = ogr.Geometry(ogr.wkbLineString)
            for point in points:
                reversed_geom.AddPoint(*point)
            feature.SetGeometryDirectly(reversed_geom)
            ogr_lyr.SetFeature(feature)

    return ts_gauge_line, summed_vals
