from threedi_results_analysis.utils.threedi_result_aggregation.base import Aggregation
from threedi_results_analysis.utils.threedi_result_aggregation.constants import (
    AGGREGATION_VARIABLES,
    AGGREGATION_METHODS,
)
from .style import (
    Style,
    STYLE_SINGLE_COLUMN_GRADUATED_NODE,
    STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    STYLE_CHANGE_WL,
    STYLE_VECTOR,
    STYLE_TIMESTEP_REDUCTION_ANALYSIS,
    STYLE_BALANCE,
    STYLE_WATER_ON_STREET_DURATION_NODE,
    STYLE_MANHOLE_WATER_DEPTH_0D1D_NODE,
    STYLE_MANHOLE_WATER_DEPTH_1D2D_NODE,
    STYLE_MANHOLE_MIN_FREEBOARD_0D1D,
    STYLE_MANHOLE_MIN_FREEBOARD_1D2D,
    STYLE_SINGLE_COLUMN_GRADUATED_PUMP,
    STYLE_SINGLE_COLUMN_GRADUATED_PUMP_LINESTRING,
)


class Preset:
    def __init__(
        self,
        name: str,
        description: str = "",
        aggregations=None,
        resample_point_layer: bool = False,

        flowlines_style: Style = None,
        cells_style: Style = None,
        nodes_style: Style = None,
        pumps_style: Style = None,
        pumps_linestring_style: Style = None,

        flowlines_style_param_values: dict = None,
        cells_style_param_values: dict = None,
        nodes_style_param_values: dict = None,
        pumps_style_param_values: dict = None,
        pumps_linestring_style_param_values: dict = None,

        flowlines_layer_name: str = None,
        cells_layer_name: str = None,
        nodes_layer_name: str = None,
        pumps_layer_name: str = None,
        pumps_linestring_layer_name: str = None,
        raster_layer_name: str = None,

        only_manholes: bool = False,
    ):
        if aggregations is None:
            aggregations = list()
        self.name = name
        self.description = description
        self.__aggregations = aggregations
        self.resample_point_layer = resample_point_layer

        self.flowlines_style = flowlines_style
        self.cells_style = cells_style
        self.nodes_style = nodes_style
        self.pumps_style = pumps_style
        self.pumps_linestring_style = pumps_linestring_style

        self.flowlines_style_param_values = flowlines_style_param_values
        self.cells_style_param_values = cells_style_param_values
        self.nodes_style_param_values = nodes_style_param_values
        self.pumps_style_param_values = pumps_style_param_values
        self.pumps_linestring_style_param_values = pumps_linestring_style_param_values

        self.flowlines_layer_name = flowlines_layer_name
        self.cells_layer_name = cells_layer_name
        self.nodes_layer_name = nodes_layer_name
        self.pumps_layer_name = pumps_layer_name
        self.pumps_linestring_layer_name = pumps_linestring_layer_name
        self.raster_layer_name = raster_layer_name

        self.only_manholes = only_manholes

    def add_aggregation(self, aggregation: Aggregation):
        self.__aggregations.append(aggregation)

    def aggregations(self):
        return self.__aggregations


# No preset selected
NO_PRESET = Preset(name="(no preset selected)", aggregations=[])

# Maximum water level
max_wl_aggregations = [
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("s1"),
        method=AGGREGATION_METHODS.get_by_short_name("max"),
    )
]

MAX_WL_PRESETS = Preset(
    name="Maximum water level",
    description="Calculates the maximum water level for nodes and cells within the chosen "
    "time filter.",
    aggregations=max_wl_aggregations,
    nodes_style=STYLE_SINGLE_COLUMN_GRADUATED_NODE,
    cells_style=STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    nodes_style_param_values={"column": "s1_max"},
    cells_style_param_values={"column": "s1_max"},
    nodes_layer_name="Maximum water level (nodes)",
    cells_layer_name="Maximum water level (cells)",
    raster_layer_name="Maximum water level (raster)",
)

# Change in water level
change_wl_aggregations = [
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("s1"),
        method=AGGREGATION_METHODS.get_by_short_name("first"),
    ),
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("s1"),
        method=AGGREGATION_METHODS.get_by_short_name("last"),
    ),
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("s1"),
        method=AGGREGATION_METHODS.get_by_short_name("min"),
    ),
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("s1"),
        method=AGGREGATION_METHODS.get_by_short_name("max"),
    ),
]

CHANGE_WL_PRESETS = Preset(
    name="Change in water level",
    description="Calculates the difference in water level (last - first). In the styling "
    "NULL values (when the cell is dry) are replaced by the cell's lowest "
    "pixel elevation (bottom_level).",
    aggregations=change_wl_aggregations,
    cells_style=STYLE_CHANGE_WL,
    cells_style_param_values={"first": "s1_first", "last": "s1_last"},
    cells_layer_name="Change in water level (cells)",
    raster_layer_name="Change in water level (raster)",
)

# Flow pattern
flow_pattern_aggregations = [
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("q_out_x"),
        method=AGGREGATION_METHODS.get_by_short_name("sum"),
    ),
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("q_out_y"),
        method=AGGREGATION_METHODS.get_by_short_name("sum"),
    ),
]

FLOW_PATTERN_PRESETS = Preset(
    name="Flow pattern",
    description="Generates a flow pattern map. The aggregation calculates total outflow per "
    "node in x and y directions, resampled to grid_space. In the styling that is "
    "applied, the shade of blue and the rotation of the arrows are based on the "
    "resultant of these two.\n\n"
    "To save the output to disk, save to GeoPackage (Export > Save features as),"
    "copy the styling to the new layer (Styles > Copy Style / Paste Style). Then "
    "save the styling as default in the GeoPackage (Properties > Style > Save as "
    "Default > Save default style to Datasource Database). ",
    aggregations=flow_pattern_aggregations,
    resample_point_layer=True,
    nodes_style=STYLE_VECTOR,
    nodes_style_param_values={"x": "q_out_x_sum", "y": "q_out_y_sum"},
    nodes_layer_name="Flow pattern (nodes)",
    raster_layer_name="Flow pattern (raster)",
)

# Timestep reduction analysis
ts_reduction_analysis_aggregations = [
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("ts_max"),
        method=AGGREGATION_METHODS.get_by_short_name("below_thres"),
        threshold=1.0,
    ),
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("ts_max"),
        method=AGGREGATION_METHODS.get_by_short_name("below_thres"),
        threshold=3.0,
    ),
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("ts_max"),
        method=AGGREGATION_METHODS.get_by_short_name("below_thres"),
        threshold=5.0,
    ),
]
TS_REDUCTION_ANALYSIS_PRESETS = Preset(
    name="Timestep reduction analysis",
    description="Timestep reduction analysis calculates the % of time that the flow "
    "through each flowline limits the calculation timestep to below 1, "
    "3, "
    "or 5 seconds. \n\n"
    "The styling highlights the flowlines that have a timestep of \n"
    "    < 1 s for 10% of the time and/or\n"
    "    < 3 s for 50% of the time and/or\n"
    "    < 5 s for 80% of the time;"
    "\n\n"
    "Replacing these flowlines with orifices may speed up the "
    "simulation "
    "without large impact on the results. Import the highlighted lines "
    "from the aggregation result into your 3Di spatialite as "
    "'ts_reducers' and use this query to replace line elements ("
    "example "
    "for v2_pipe):\n\n"
    "-- Add orifice:\n"
    "INSERT INTO v2_orifice(display_name, code, crest_level, sewerage, "
    "cross_section_definition_id, friction_value, friction_type, "
    "discharge_coefficient_positive, discharge_coefficient_negative, "
    "zoom_category, crest_type, connection_node_start_id, "
    "connection_node_end_id)\n"
    "SELECT display_name, code, max(invert_level_start_point, "
    "invert_level_end_point) AS crest_level, TRUE AS sewerage, "
    "cross_section_definition_id, friction_value, friction_type, "
    "1 AS discharge_coefficient_positive, "
    "1 AS discharge_coefficient_negative, zoom_category, "
    "4 AS crest_type, "
    "connection_node_start_id, connection_node_end_id\n"
    "FROM v2_pipe\n"
    "WHERE id IN (SELECT spatialite_id FROM ts_reducers WHERE "
    "content_type='v2_pipe');\n\n"
    "-- Remove pipe\n"
    "DELETE FROM v2_pipe WHERE id IN (SELECT spatialite_id FROM "
    "ts_reducers WHERE content_type='v2_pipe');",
    aggregations=ts_reduction_analysis_aggregations,
    flowlines_style=STYLE_TIMESTEP_REDUCTION_ANALYSIS,
    flowlines_style_param_values={
        "col1": "ts_max_below_thres_1_0",
        "col2": "ts_max_below_thres_3_0",
        "col3": "ts_max_below_thres_5_0",
    },
    flowlines_layer_name="Timestep reduction analysis (flowlines)",
    raster_layer_name="Timestep reduction analysis (raster)",
)

# Source or sink (mm)
source_sink_mm_aggregations = [
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("rain_depth"),
        method=AGGREGATION_METHODS.get_by_short_name("sum"),
    ),
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name(
            "infiltration_rate_simple_mm"
        ),
        method=AGGREGATION_METHODS.get_by_short_name("sum"),
    ),
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name(
            "intercepted_volume_mm"
        ),
        method=AGGREGATION_METHODS.get_by_short_name("last"),
    ),
]
SOURCE_SINK_MM_PRESETS = Preset(
    name="Source or sink (mm)",
    description="Calculate by how many mm a node or cell is a net source or sink."
    "A positive results indicates a source, negative result a sink.",
    aggregations=source_sink_mm_aggregations,
    cells_style=STYLE_BALANCE,
    cells_style_param_values={
        "positive_col1": "rain_depth_sum",
        "positive_col2": "",
        "positive_col3": "",
        "negative_col1": "infiltration_rate_simple_mm_sum",
        "negative_col2": "intercepted_volume_mm_last",
        "negative_col3": "",
    },
    cells_layer_name="Source or sink (cells)",
    raster_layer_name="Source or sink (raster)",
)

# Change in water level
water_on_street_aggregations_0d1d = [
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("s1"),
        method=AGGREGATION_METHODS.get_by_short_name("time_above_threshold"),
        threshold="drain_level",
    ),
]

water_on_street_aggregations_1d2d = [
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("s1"),
        method=AGGREGATION_METHODS.get_by_short_name("time_above_threshold"),
        threshold="exchange_level_1d2d",
    ),
]

WATER_ON_STREET_DURATION_0D1D_PRESET = Preset(
    name="Manhole: Water on street duration (0D1D)",
    description="Time [s] that the water level in manholes exceeds the drain level.\n\n"
                "In 3Di models without 2D, this is the level at which water flows onto the street (i.e., where the "
                "storage area changes from what is specified at the connection node to what is specified as manhole "
                "storage area in the global settings).\n\n"
                "⚠ Do not use this preset for 3Di models with 2D. In such models, the drain level defined at the "
                "manhole is not always the level at which water flows onto the street. If the drain level is lower "
                "than the bottom level (lowest pixel) of the 2D cell the manhole is in, the water must rise to the "
                "2D cell's bottom level before it can flow onto the street.",
    aggregations=water_on_street_aggregations_0d1d,
    nodes_style=STYLE_WATER_ON_STREET_DURATION_NODE,
    nodes_style_param_values={"column": "s1_time_above_threshold_drain_level"},
    nodes_layer_name="Manhole: Water on street duration (0D1D)",
    only_manholes=True,
)

WATER_ON_STREET_DURATION_1D2D_PRESET = Preset(
    name="Manhole: Water on street duration (1D2D)",
    description="Time [s] that the water level in manholes exceeds the 1D2D exchange level.\n\n"
                "In 3Di models with 2D, this is the level at which water flows onto the street. The exchange level is "
                "the maximum of two values: the drain level specified for the manhole, or the bottom level (lowest "
                "pixel) of the 2D cell the manhole is in.\n\n"
                "⚠ Manholes that have no connection to the 2D domain do not have an exchange level. The 'water on "
                "street duration' is always 0 for these manholes.\n\n"
                "⚠ Do not use this preset for 3Di models without 2D. In such models, none of the manholes have a "
                "connection to the 2D domain, so the 'water on street duration' will be 0 for all manholes.",
    aggregations=water_on_street_aggregations_1d2d,
    nodes_style=STYLE_WATER_ON_STREET_DURATION_NODE,
    nodes_style_param_values={"column": "s1_time_above_threshold_exchange_level_1d2d"},
    nodes_layer_name="Manhole: Water on street duration (1D2D)",
    only_manholes=True,
)

# Manhole: Max water depth on street
max_depth_on_street_aggregations = [
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("s1"),
        method=AGGREGATION_METHODS.get_by_short_name("max")
    ),
]

MAX_DEPTH_ON_STREET_0D1D_PRESETS = Preset(
    name="Manhole: Max water depth on street (0D1D)",
    description="Maximum water depth on manholes, calculated as maximum water level - drain level\n\n"
                "In 3Di models without 2D, this is the level at which water flows onto the street (i.e., where the "
                "storage area changes from what is specified at the connection node to what is specified as manhole "
                "storage area in the global settings).\n\n"
                "⚠ Do not use this preset for 3Di models with 2D. In such models, the drain level defined at the "
                "manhole is not always the level at which water flows onto the street. If the drain level is lower "
                "than the bottom level (lowest pixel) of the 2D cell the manhole is in, the water must rise to the "
                "2D cell's bottom level before it can flow onto the street.",
    aggregations=max_depth_on_street_aggregations,
    nodes_style=STYLE_MANHOLE_WATER_DEPTH_0D1D_NODE,
    nodes_style_param_values={"value": "s1_max"},
    nodes_layer_name="Manhole: Max water depth on street (0D1D)",
    only_manholes=True
)

MAX_DEPTH_ON_STREET_1D2D_PRESETS = Preset(
    name="Manhole: Max water depth on street (1D2D)",
    description="Maximum water depth on manholes, calculated as maximum water level - 1D2D exchange level. \n\n"
                "In 3Di models with 2D, this is the level at which water flows onto the street. The exchange level is "
                "the maximum of two values: the drain level specified for the manhole, or the bottom level (lowest "
                "pixel) of the 2D cell the manhole is in.\n\n"
                "⚠ Manholes that have no connection to the 2D domain do not have an exchange level. The 'water depth "
                "on street' is NULL for these manholes.\n\n"
                "⚠ Do not use this preset for 3Di models without 2D. In such models, none of the manholes have a "
                "connection to the 2D domain, so the 'water depth on street' will be NULL for all manholes.",
    aggregations=max_depth_on_street_aggregations,
    nodes_style=STYLE_MANHOLE_WATER_DEPTH_1D2D_NODE,
    nodes_style_param_values={"value": "s1_max"},
    nodes_layer_name="Manhole: Max water depth on street (1D2D)",
    only_manholes=True
)


# Manhole: Minimum freeboard
max_depth_on_street_aggregations = [
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("s1"),
        method=AGGREGATION_METHODS.get_by_short_name("max")
    ),
]

MIN_FREEBOARD_0D1D_PRESETS = Preset(
    name="Manhole: Minimum freeboard (0D1D)",
    description="Minimum freeboard for manholes, "
                "i.e. the difference between the maximum water level and the manhole drain level.\n\n"
                "In 3Di models without 2D, this is the level at which water flows onto the street (i.e., where the "
                "storage area changes from what is specified at the connection node to what is specified as manhole "
                "storage area in the global settings).\n\n"
                "⚠ Do not use this preset for 3Di models with 2D. In such models, the drain level defined at the "
                "manhole is not always the level at which water flows onto the street. If the drain level is lower "
                "than the bottom level (lowest pixel) of the 2D cell the manhole is in, the water must rise to the "
                "2D cell's bottom level before it can flow onto the street.",
    aggregations=max_depth_on_street_aggregations,
    nodes_style=STYLE_MANHOLE_MIN_FREEBOARD_0D1D,
    nodes_style_param_values={"value": "s1_max"},
    nodes_layer_name="Manhole: Minimum freeboard (0D1D)",
    only_manholes=True
)

MIN_FREEBOARD_1D2D_PRESETS = Preset(
    name="Manhole: Minimum freeboard (1D2D)",
    description="Minimum freeboard for manholes, "
                "i.e. the difference between the maximum water level and the 1D2D exchange level.\n\n"
                "In 3Di models with 2D, this is the level at which water flows onto the street. The exchange level is "
                "the maximum of two values: the drain level specified for the manhole, or the bottom level (lowest "
                "pixel) of the 2D cell the manhole is in.\n\n"
                "⚠ Manholes that have no connection to the 2D domain do not have an exchange level. The 'minimum "
                "freeboard' is always NULL for these manholes.\n\n"
                "⚠ Do not use this preset for 3Di models without 2D. In such models, none of the manholes have a "
                "connection to the 2D domain, so the 'minimum freeboard' will be NULL for all manholes.",
    aggregations=max_depth_on_street_aggregations,
    nodes_style=STYLE_MANHOLE_MIN_FREEBOARD_1D2D,
    nodes_style_param_values={"value": "s1_max"},
    nodes_layer_name="Manhole: Minimum freeboard (1D2D)",
    only_manholes=True
)

# Pump: Total pumped volume
total_pumped_volume_aggregations = [
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("q_pump"),
        method=AGGREGATION_METHODS.get_by_short_name("sum")
    ),
]

TOTAL_PUMPED_VOLUME_PRESETS = Preset(
    name="Pump: Total pumped volume",
    description="Total volume pumped by each pump in the selected time period.",
    aggregations=total_pumped_volume_aggregations,

    pumps_style=STYLE_SINGLE_COLUMN_GRADUATED_PUMP,
    pumps_style_param_values={"column": "q_pump_sum"},
    pumps_layer_name="Pump (point): Total pumped volume [m3]",

    pumps_linestring_style=STYLE_SINGLE_COLUMN_GRADUATED_PUMP_LINESTRING,
    pumps_linestring_style_param_values={"column": "q_pump_sum"},
    pumps_linestring_layer_name="Pump (line): Total pumped volume [m3]",
)

# Pump: time at max capacity
pump_time_at_max_capacity_aggregations = [
    Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("q_pump"),
        method=AGGREGATION_METHODS.get_by_short_name("on_thres"),
        threshold="capacity"
    ),
]

PUMP_TIME_AT_MAX_CAPACITY_PRESETS = Preset(
    name="Pump: % of time at max capacity",
    description="Percentage of time that each pump is pumping at its maximum capacity in the selected time period.\n\n"
                "Note that both the pump implicit factor and the output time step will affect the result.",
    aggregations=pump_time_at_max_capacity_aggregations,

    pumps_style=STYLE_SINGLE_COLUMN_GRADUATED_PUMP,
    pumps_style_param_values={"column": "q_pump_on_thres_capacity"},
    pumps_layer_name="Pump (point): % of time at max capacity",

    pumps_linestring_style=STYLE_SINGLE_COLUMN_GRADUATED_PUMP_LINESTRING,
    pumps_linestring_style_param_values={"column": "q_pump_on_thres_capacity"},
    pumps_linestring_layer_name="Pump (line): % of time at max capacity",
)

PRESETS = [
    NO_PRESET,
    MAX_WL_PRESETS,
    CHANGE_WL_PRESETS,
    SOURCE_SINK_MM_PRESETS,
    FLOW_PATTERN_PRESETS,
    TS_REDUCTION_ANALYSIS_PRESETS,
    MAX_DEPTH_ON_STREET_0D1D_PRESETS,
    MAX_DEPTH_ON_STREET_1D2D_PRESETS,
    MIN_FREEBOARD_0D1D_PRESETS,
    MIN_FREEBOARD_1D2D_PRESETS,
    WATER_ON_STREET_DURATION_0D1D_PRESET,
    WATER_ON_STREET_DURATION_1D2D_PRESET,
    TOTAL_PUMPED_VOLUME_PRESETS,
    PUMP_TIME_AT_MAX_CAPACITY_PRESETS,
]
