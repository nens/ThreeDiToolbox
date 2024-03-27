# Qt linestyles, linecolors etc
# http://pyqt.sourceforge.net/Docs/PyQt4/qpen.html

# QColor constructed from the given CMYK color values:
# c (cyan), m (magenta), y (yellow), k (black), and a (alpha-channel,
# i.e. transparency (0=totally transparant)).
# all numbers are integers between 0-256

FILL_TRANSP = ",150"
PEN_TRANSP = ",180"
FILL_TRANSP_VOL_CHANGE = ",0"

# serie_name, index, modelpart for bars, modelpart for graph
INPUT_SERIES = [
    ("2d_in", 0),
    ("2d_out", 1),
    ("1d_in", 2),
    ("1d_out", 3),
    ("2d_bound_in", 4),
    ("2d_bound_out", 5),
    ("1d_bound_in", 6),
    ("1d_bound_out", 7),
    ("1d__1d_2d_flow_in", 8),
    ("1d__1d_2d_flow_out", 9),
    ("1d__1d_2d_exch_in", 10),
    ("1d__1d_2d_exch_out", 11),
    ("pump_in", 12),
    ("pump_out", 13),
    ("rain", 14),
    ("infiltration_rate_simple", 15),
    ("lat_2d", 16),
    ("lat_1d", 17),
    ("d_2d_vol", 18),
    ("d_1d_vol", 19),
    ("error_2d", 20),
    ("error_1d", 21),
    ("error_1d_2d", 22),
    ("2d_groundwater_in", 23),
    ("2d_groundwater_out", 24),
    ("d_2d_groundwater_vol", 25),
    ("leak", 26),
    ("inflow", 27),
    ("2d_vertical_infiltration_pos", 28),
    ("2d_vertical_infiltration_neg", 29),
    ("2d__1d_2d_flow_in", 30),
    ("2d__1d_2d_flow_out", 31),
    ("2d__1d_2d_exch_in", 32),
    ("2d__1d_2d_exch_out", 33),
    ("intercepted_volume", 34),
    ("q_sss", 35),
]

# graph series settings
GRAPH_SERIES = [
    {
        "name": "2D flow",
        "default_method": "gross",
        "order": 1,
        "def_fill_color": "63,81,181" + FILL_TRANSP,
        "def_pen_color": "63,81,181" + PEN_TRANSP,
        "series": ["2d_in", "2d_out"],
    },
    {
        "name": "2D boundary flow",
        "default_method": "gross",
        "order": 2,
        "def_fill_color": "156,39,176" + FILL_TRANSP,
        "def_pen_color": "156,39,176" + PEN_TRANSP,
        "series": ["2d_bound_in", "2d_bound_out"],
    },
    {
        "name": "1D flow",
        "default_method": "gross",
        "order": 3,
        "def_fill_color": "0,188,212" + FILL_TRANSP,
        "def_pen_color": "0,188,212" + PEN_TRANSP,
        "series": ["1d_in", "1d_out"],
    },
    {
        "name": "1D boundary flow",
        "default_method": "gross",
        "order": 4,
        "def_fill_color": "156,39,176" + FILL_TRANSP,
        "def_pen_color": "156,39,176" + PEN_TRANSP,
        "series": ["1d_bound_in", "1d_bound_out"],
    },
    {
        "name": "2D flow to 1D (domain exchange)",
        "default_method": "gross",
        "order": 5,
        "def_fill_color": "240,210,50" + FILL_TRANSP,
        "def_pen_color": "240,210,50" + PEN_TRANSP,
        "series": ["1d__1d_2d_exch_in", "1d__1d_2d_exch_out"],
    },
    {
        "name": "2D flow to 1D",
        "default_method": "gross",
        "order": 5,
        "def_fill_color": "100,220,5" + FILL_TRANSP,
        "def_pen_color": "100,220,5" + PEN_TRANSP,
        "series": [
            "1d__1d_2d_flow_in",
            "1d__1d_2d_flow_out",
            "2d__1d_2d_flow_in",
            "2d__1d_2d_flow_out",
        ],
    },
    {
        "name": "pumps",
        "default_method": "gross",
        "order": 6,
        "def_fill_color": "255,235,59" + FILL_TRANSP,
        "def_pen_color": "255,235,59" + PEN_TRANSP,
        "series": ["pump_in", "pump_out"],
    },
    {
        "name": "rain on 2D",
        "default_method": "net",
        "order": 7,
        "def_fill_color": "0,150,136" + FILL_TRANSP,
        "def_pen_color": "0,150,136" + PEN_TRANSP,
        "series": ["rain"],
    },
    {
        "name": "lateral flow to 1D",
        "default_method": "net",
        "order": 8,
        "def_fill_color": "76,175,80" + FILL_TRANSP,
        "def_pen_color": "76,175,80" + PEN_TRANSP,
        "series": ["lat_1d"],
    },
    {
        "name": "lateral flow to 2D",
        "default_method": "net",
        "order": 9,
        "def_fill_color": "176,175,80" + FILL_TRANSP,
        "def_pen_color": "176,175,80" + PEN_TRANSP,
        "series": ["lat_2d"],
    },
    {
        "name": "constant infiltration",
        "default_method": "net",
        "order": 10,
        "def_fill_color": "121,85,72" + FILL_TRANSP,
        "def_pen_color": "121,85,72" + PEN_TRANSP,
        "series": ["infiltration_rate_simple"],
    },
    {
        "name": "volume change 2D",
        "default_method": "net",
        "order": 11,
        "def_fill_color": "244,67,54" + FILL_TRANSP_VOL_CHANGE,
        "def_pen_color": "244,67,54" + PEN_TRANSP,
        "series": ["d_2d_vol"],
    },
    {
        "name": "volume change 1D",
        "default_method": "net",
        "order": 12,
        "def_fill_color": "255,152,0" + FILL_TRANSP_VOL_CHANGE,
        "def_pen_color": "255,152,0" + PEN_TRANSP,
        "series": ["d_1d_vol"],
    },
    {
        "name": "groundwater flow",
        "default_method": "gross",
        "order": 2.5,
        "def_fill_color": "0,0,128" + FILL_TRANSP,
        "def_pen_color": "0,0,128" + PEN_TRANSP,
        "series": ["2d_groundwater_in", "2d_groundwater_out"],
    },
    {
        "name": "volume change groundwater",
        "default_method": "net",
        "order": 11.5,
        "def_fill_color": "100,149,237" + FILL_TRANSP_VOL_CHANGE,
        "def_pen_color": "100,149,237" + PEN_TRANSP,
        "series": ["d_2d_groundwater_vol"],
    },
    {
        "name": "leakage",
        "default_method": "net",
        "order": 10.5,
        "def_fill_color": "221,160,221" + FILL_TRANSP,
        "def_pen_color": "221,160,221" + PEN_TRANSP,
        "series": ["leak"],
    },
    {
        "name": "in/exfiltration (domain exchange)",
        "default_method": "gross",
        "order": 10.6,
        "def_fill_color": "121,160,191" + FILL_TRANSP,
        "def_pen_color": "121,160,191" + PEN_TRANSP,
        "series": [
            "2d_vertical_infiltration_pos",
            "2d_vertical_infiltration_neg",
        ],
    },
    {
        "name": "interception",
        "default_method": "net",
        "order": 10.7,
        "def_fill_color": "181,60,221" + FILL_TRANSP,
        "def_pen_color": "181,60,221" + PEN_TRANSP,
        "series": ["intercepted_volume"],
    },
    {
        "name": "0D rainfall runoff on 1D",
        "default_method": "net",
        "order": 7.1,
        "def_fill_color": "50,130,136" + FILL_TRANSP,
        "def_pen_color": "50,130,136" + PEN_TRANSP,
        "series": ["inflow"],
    },
    {
        "name": "surface sources and sinks",
        "default_method": "net",
        "order": 7.2,
        "def_fill_color": "204,255,51" + FILL_TRANSP,
        "def_pen_color": "204,255,51" + PEN_TRANSP,
        "series": ["q_sss"],
    },
]

# uniqueness test
_series = [serie for item in GRAPH_SERIES for serie in item["series"]]
assert len(set(_series)) == len(_series)

# barchart in/out series
BC_IO_SERIES = [
    {
        # 'label_name': '1D: 1D-2D flow',
        "label_name": "1D: 2D flow to 1D",
        "in": ["1d__1d_2d_flow_in"],
        "out": ["1d__1d_2d_flow_out"],
        "type": "1d",
    },
    {
        # 'label_name': '2D: 1D-2D flow',
        "label_name": "2D: 2D flow to 1D",
        "in": ["2d__1d_2d_flow_in"],
        "out": ["2d__1d_2d_flow_out"],
        "type": "2d",
    },
    {
        # 'label_name': '1D-2D flow (all domains)',
        "label_name": "2D flow to 1D (all domains)",
        # does this make sense?
        "in": ["1d__1d_2d_flow_in", "2d__1d_2d_flow_in"],
        "out": ["1d__1d_2d_flow_out", "2d__1d_2d_flow_out"],
        "type": "NETVOL",
    },
    {
        # 'label_name': '1D: 1D-2D exchange',
        "label_name": "1D: 2D flow to 1D (domain exchange)",
        "in": ["1d__1d_2d_exch_in"],
        "out": ["1d__1d_2d_exch_out"],
        "type": "1d",
    },
    {
        # 'label_name': '2D: 1D-2D exchange',
        "label_name": "2D: 2D flow to 1D (domain exchange)",
        "in": ["2d__1d_2d_exch_in"],
        "out": ["2d__1d_2d_exch_out"],
        "type": "2d",
    },
    {
        "label_name": "net change in storage",
        "in": ["d_2d_vol"],
        "out": ["d_2d_vol"],
        "type": "2d",
    },
    {
        "label_name": "net change in storage",
        "in": ["d_1d_vol"],
        "out": ["d_1d_vol"],
        "type": "1d",
    },
    {
        "label_name": "net change in storage",
        "in": ["d_2d_groundwater_vol"],
        "out": ["d_2d_groundwater_vol"],
        "type": "2d_groundwater",
    },
    {
        "label_name": "leakage",
        "in": ["leak"],
        "out": ["leak"],
        "type": "2d_groundwater",
    },
    {
        "label_name": "constant infiltration",
        "in": ["infiltration_rate_simple"],
        "out": ["infiltration_rate_simple"],
        "type": "2d",
    },
    {"label_name": "2D flow", "in": ["2d_in"], "out": ["2d_out"], "type": "2d"},
    {"label_name": "1D flow", "in": ["1d_in"], "out": ["1d_out"], "type": "1d"},
    {
        "label_name": "groundwater flow",
        "in": ["2d_groundwater_in"],
        "out": ["2d_groundwater_out"],
        "type": "2d_groundwater",
    },
    {
        "label_name": "lateral flow to 2D",
        "in": ["lat_2d"],
        "out": ["lat_2d"],
        "type": "2d",
    },
    {
        "label_name": "lateral flow to 1D",
        "in": ["lat_1d"],
        "out": ["lat_1d"],
        "type": "1d",
    },
    {
        "label_name": "2D boundary flow",
        "in": ["2d_bound_in"],
        "out": ["2d_bound_out"],
        "type": "2d",
    },
    {
        "label_name": "1D boundary flow",
        "in": ["1d_bound_in"],
        "out": ["1d_bound_out"],
        "type": "1d",
    },
    {
        "label_name": "0D rainfall runoff on 1D",
        "in": ["inflow"],
        "out": ["inflow"],
        "type": "1d",
    },
    {
        "label_name": "in/exfiltration (domain exchange)",
        # NOTE: for the argument why pos is out and neg is in, see the
        # comment in ``WaterBalanceCalculation.get_aggregated_flows``
        "in": ["2d_vertical_infiltration_neg"],
        "out": ["2d_vertical_infiltration_pos"],
        "type": "2d_vert",
    },
    {
        "label_name": "change in storage",
        "in": ["d_2d_vol", "d_2d_groundwater_vol", "d_1d_vol"],
        "out": ["d_2d_vol", "d_2d_groundwater_vol", "d_1d_vol"],
        "type": "NETVOL",
    },
    {"label_name": "pump", "in": ["pump_in"], "out": ["pump_out"], "type": "1d"},
    {"label_name": "rain on 2D", "in": ["rain"], "out": ["rain"], "type": "2d"},
    {
        "label_name": "interception",
        "in": ["intercepted_volume"],
        "out": ["intercepted_volume"],
        "type": "2d",
    },
    {
        "label_name": "surface sources and sinks",
        "in": ["q_sss"],
        "out": ["q_sss"],
        "type": "2d",
    },
]

TIME_UNITS_TO_SECONDS = {"hrs": 3600, "mins": 60, "s": 1}

AGG_CUMULATIVE_FLOW = "m³ cumulative"
AGG_FLOW = "m³/s"
