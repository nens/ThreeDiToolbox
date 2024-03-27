from collections import namedtuple


#: namedtuple for NetCDF variable information
NcVar = namedtuple("NcVar", ["name", "verbose_name", "unit", "negative_possible"])

WATERLEVEL = NcVar("s1", "waterlevel", "m MSL", True)
DISCHARGE = NcVar("q", "discharge", "m3/s", True)
VELOCITY = NcVar("u1", "velocity", "m/s", True)
VOLUME = NcVar("vol", "volume", "m3", False)
DISCHARGE_PUMP = NcVar("q_pump", "discharge pump", "m3/s", False)
DISCHARGE_INTERFLOW = NcVar("qp", "discharge interflow", "m3/s", True)
DISCHARGE_LATERAL = NcVar("q_lat", "discharge lateral", "m3/s", True)
VELOCITY_INTERFLOW = NcVar("up1", "velocity interflow", "m/s", True)
RAIN_INTENSITY = NcVar("rain", "rain intensity", "m3/s", False)
WET_SURFACE_AREA = NcVar("su", "wet surface area", "m2", False)
INFILTRATION = NcVar("infiltration_rate", "infiltration rate", "m3/s", True)
INFILTRATION_RATE_SIMPLE = NcVar(
    "infiltration_rate_simple", "infiltration rate simple", "m3/s", False
)
WET_CROSS_SECTION_AREA = NcVar("au", "wet cross-sectional area", "m2", False)
LEAKAGE_RATE = NcVar("leak", "leakage rate", "m3/s", True)
INTERCEPTION = NcVar("intercepted_volume", "intercepted volume", "m3", False)
SOURCES_AND_SINKS = NcVar("q_sss", "sources and sinks", "m3/s", True)

# TODO: rename Line_types
_Q_TYPES = [
    DISCHARGE,
    DISCHARGE_INTERFLOW,
    DISCHARGE_PUMP,
    VELOCITY,
    VELOCITY_INTERFLOW,
    WET_CROSS_SECTION_AREA,
]
# TODO: rename node_types
_H_TYPES = [
    WATERLEVEL,
    VOLUME,
    RAIN_INTENSITY,
    WET_SURFACE_AREA,
    INFILTRATION,
    DISCHARGE_LATERAL,
    INFILTRATION_RATE_SIMPLE,
    LEAKAGE_RATE,
    INTERCEPTION,
    SOURCES_AND_SINKS,
]

Q_TYPES = [v.name for v in _Q_TYPES]
H_TYPES = [v.name for v in _H_TYPES]

# TODO: look at the name
SUBGRID_MAP_VARIABLES = _Q_TYPES + _H_TYPES  # just take all variables..

NEGATIVE_POSSIBLE = dict([(v.name, v.negative_possible) for v in SUBGRID_MAP_VARIABLES])

AGGREGATION_VARIABLES = [
    DISCHARGE,
    DISCHARGE_INTERFLOW,
    DISCHARGE_PUMP,
    VELOCITY,
    VELOCITY_INTERFLOW,
    WATERLEVEL,
    VOLUME,
    RAIN_INTENSITY,
    WET_SURFACE_AREA,
    INFILTRATION,
    INFILTRATION_RATE_SIMPLE,
    DISCHARGE_LATERAL,
    WET_CROSS_SECTION_AREA,
    LEAKAGE_RATE,
    INTERCEPTION,
    SOURCES_AND_SINKS,
]

AGGREGATION_OPTIONS = {
    "min",
    "max",
    "avg",
    "med",
    "cum",
    "cum_positive",
    "cum_negative",
    "current",
}

# Explanation: aggregation using the cumulative method integrates the variable
# over time. Therefore the units must be multiplied by time.
CUMULATIVE_AGGREGATION_UNITS = {
    "s1": "m MSL",
    "q": "m3",
    "u1": "m",
    "vol": "m3",
    "q_pump": "m3",
    "qp": "m3",
    "up1": "m",
    "q_lat": "m3",
    "vol1": "m3",
    "rain": "m3",
    "infiltration_rate": "m3",
    "infiltration_rate_simple": "m3",
    "leak": "m3",
    "su": "",
    "au": "",
    "intercepted_volume": "m3",
    "q_sss": "m3",
}

#: namedtuple for layer information (note: object_type should be normalized)
LayerInformation = namedtuple(
    "LayerInformation", ["layer_name", "object_type", "qh_type"]
)
layer_information = [
    LayerInformation("v2_connection_nodes", "connection_nodes", "h"),
    LayerInformation("v2_pipe_view", "pipe", "q"),
    LayerInformation("v2_channel", "channel", "q"),
    LayerInformation("v2_culvert_view", "culvert", "q"),
    LayerInformation("v2_manhole_view", "manhole", "h"),
    LayerInformation("v2_pumpstation", "pumpstation", "q"),
    LayerInformation("v2_pumpstation_view", "pumpstation", "q"),
    LayerInformation("v2_weir_view", "weir", "q"),
    LayerInformation("v2_orifice_view", "orifice", "q"),
    LayerInformation("sewerage_manhole", "manhole", "h"),
    LayerInformation("sewerage_pipe_view", "pipe", "q"),
    LayerInformation("sewerage_pumpstation", "pumpstation", "q"),
    LayerInformation("sewerage_pumpstation_view", "pumpstation", "q"),
    LayerInformation("sewerage_weir_view", "weir", "q"),
    LayerInformation("sewerage_orifice_view", "orifice", "q"),
    LayerInformation("flowlines", "flowline", "q"),
    LayerInformation("nodes", "node", "h"),
    LayerInformation("pumplines", "pumpline", "q"),
    LayerInformation("line_results", "flowline", "q"),
    LayerInformation("node_results", "node", "h"),
]

# TODO: QH is also defined above.
LAYER_OBJECT_TYPE_MAPPING = dict([(a[0], a[1]) for a in layer_information])
