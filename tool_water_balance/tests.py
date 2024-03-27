from pathlib import Path
from qgis.core import QgsCoordinateReferenceSystem
from qgis.core import QgsCoordinateTransform
from qgis.core import QgsGeometry
from qgis.core import QgsPointXY
from qgis.core import QgsProject
from threedi_results_analysis.tests.test_init import TEST_DATA_DIR
from threedi_results_analysis.tests.utilities import ensure_qgis_app_is_initialized

from .tools import WaterBalanceCalculation
from .tools import WaterBalanceCalculationManager
from .views.widgets import INPUT_SERIES
from .views.widgets import WaterBalanceWidget
from .views.widgets import BarManager

import mock
import numpy as np
import pytest


TESTMODEL_DIR = TEST_DATA_DIR / "testmodel" / "v2_bergermeer"
MODEL_SQLITE_PATH = TESTMODEL_DIR / "v2_bergermeer.sqlite"
assert Path.is_dir(TESTMODEL_DIR), "testmodel dir not found"
assert Path.is_file(MODEL_SQLITE_PATH), "modelspatialite not found"


# links_expected consists of (lines, pumps)
LINKS_EXPECTED = (
    {
        "1d_in": [29136],
        "1d_out": [],
        "1d_bound_in": [],
        "1d_bound_out": [],
        "2d_in": [
            3710,
            6573,
            10314,
            1557,
            8964,
            8900,
            8901,
            3689,
            3690,
            4879,
        ],
        "2d_out": [
            10369,
            5348,
            4895,
            3730,
            10347,
        ],
        "2d_bound_in": [],
        "2d_bound_out": [],
        "1d__1d_2d_flow": [],
        "2d__1d_2d_flow": [],
        "1d_2d_exch": [30649, 31654],
        "2d_groundwater_in": [
            22984,
            17968,
            25375,
            26725,
            20121,
            25311,
            25312,
            20100,
            20101,
            21290,
        ],
        "2d_groundwater_out": [
            26780,
            21306,
            20141,
            21759,
            26758,
        ],
        "2d_vertical_infiltration": [
            14931,
            11591,
            12517,
            12503,
            12504,
            11592,
        ],
    },
    {"in": [], "out": []},
)

NODES_EXPECTED = {
    "1d": [11553, 12961],
    "2d": [554, 555, 1466, 1467, 1480, 3894],
    "2d_groundwater": [5928, 5929, 6840, 6841, 6854, 9268],
}

TIMESTEPS_EXPECTED = np.array(
    [
        0.0,
        300.46375545,
        602.91879098,
        918.32741104,
        1204.65442229,
        1504.12043258,
        1801.25668355,
    ]
)


def _helper_round_numpy(one_array):
    """round numpy values to certain decimal precision so that we can test it more easily"""
    DECIMAL_PRECISION = 6
    return np.around(one_array, decimals=DECIMAL_PRECISION)


def _helper_get_input_series_id(input_serie_name):
    id_found = [
        id[1] for id in INPUT_SERIES if id[0] == input_serie_name
    ]
    assert len(id_found) == 1
    return id_found[0]


def _helper_calculate_agg_flow(aggregated_flows, input_serie_id):
    timesteps = aggregated_flows[0]
    all_time_series = aggregated_flows[1]
    cum_flow = 0
    prev_t = 0
    for timestep_index, time in enumerate(timesteps):
        dt = time - prev_t
        prev_t = time
        flow = all_time_series[timestep_index, input_serie_id] * dt
        cum_flow += flow
    return cum_flow


@pytest.fixture
def wb_polygon():
    """WaterBalancePolyon is to select links, nodes, pumps from model schematisation"""
    polygon_points = [
        QgsPointXY(4.70635793604164299, 52.64214387449186461),
        QgsPointXY(4.70644905107772882, 52.64329192394655621),
        QgsPointXY(4.70765176955406783, 52.64332836996099019),
        QgsPointXY(4.70806178721645541, 52.6419889789305202),
        QgsPointXY(4.70725997489889636, 52.64173385682948236),
        QgsPointXY(4.70635793604164299, 52.64214387449186461),
    ]
    polygon = QgsGeometry.fromPolygonXY([polygon_points])
    tr = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem(
            4326, QgsCoordinateReferenceSystem.PostgisCrsId
        ),
        QgsCoordinateReferenceSystem(
            28992, QgsCoordinateReferenceSystem.PostgisCrsId
        ),
        QgsProject.instance(),
    )
    polygon.transform(tr)
    assert polygon.isGeosValid(), "polygon is GeoInvalid. WaterBalance tests will fail"
    return polygon


@pytest.fixture()
def wb_calculation(three_di_result_item, wb_polygon):
    three_di_result_item
    ensure_qgis_app_is_initialized()
    mapcrs = QgsCoordinateReferenceSystem(
        4326, QgsCoordinateReferenceSystem.PostgisCrsId
    )
    wb_calculation = WaterBalanceCalculation(
        result=three_di_result_item,
        polygon=wb_polygon,
        mapcrs=mapcrs,
    )
    return wb_calculation


def test_get_incoming_and_outcoming_link_ids(wb_calculation):
    links = wb_calculation.flowline_ids, wb_calculation.pump_ids
    assert links == LINKS_EXPECTED


def test_get_nodes(wb_calculation):
    nodes = wb_calculation.node_ids
    assert nodes == NODES_EXPECTED


def test_time_steps_get_aggregated_flows(wb_calculation):
    """test A) number of timesteps, B) wheter we get a time series for each link,
    pump and node"""
    time = wb_calculation.time
    flow = wb_calculation.flow

    assert (
        _helper_round_numpy(time) == _helper_round_numpy(TIMESTEPS_EXPECTED)
    ).all(), (
        "aggregation timesteps array is not what we expected (even when "
        "we round numbers)"
    )
    assert len(time) == len(flow), (
        "Number of time_steps is not equal to number of values in time_series"
    )

    assert len(INPUT_SERIES) == flow.shape[1], (
        "For all INPUT_SERIES elements " "a time series should be calculated"
    )


def test_get_aggregated_flows_2d_and_1d(wb_calculation):
    aggregated_flows = wb_calculation.time, wb_calculation.flow

    EXPECTED_CUMM_2D_IN = 719.93930714
    ID = _helper_get_input_series_id("2d_in")
    cumm_flow = _helper_calculate_agg_flow(aggregated_flows, ID)
    assert _helper_round_numpy(cumm_flow) == _helper_round_numpy(EXPECTED_CUMM_2D_IN)

    EXPECTED_CUMM_2D_OUT = -12690.85412108924
    ID = _helper_get_input_series_id("2d_out")
    cumm_flow = _helper_calculate_agg_flow(aggregated_flows, ID)
    assert _helper_round_numpy(cumm_flow) == _helper_round_numpy(EXPECTED_CUMM_2D_OUT)

    EXPECTED_CUMM_1D_IN = 7.1771299119876979e-09
    ID = _helper_get_input_series_id("1d_in")
    cumm_flow = _helper_calculate_agg_flow(aggregated_flows, ID)
    assert _helper_round_numpy(cumm_flow) == _helper_round_numpy(EXPECTED_CUMM_1D_IN)

    EXPECTED_CUMM_1D_OUT = -2832.9581887459126
    ID = _helper_get_input_series_id("1d_out")
    cumm_flow = _helper_calculate_agg_flow(aggregated_flows, ID)
    assert _helper_round_numpy(cumm_flow) == _helper_round_numpy(EXPECTED_CUMM_1D_OUT)


@pytest.fixture()
@mock.patch(
    "threedi_results_analysis.tool_water_balance.views.widgets.SelectPolygonTool"
)
def wb_widget(pt, wb_calculation):
    ensure_qgis_app_is_initialized()
    manager = WaterBalanceCalculationManager
    iface = mock.Mock()
    wb_widget = WaterBalanceWidget(
        "3Di water balance", iface=iface, manager=manager,
    )
    wb_widget.calc = wb_calculation
    return wb_widget


def test_wb_widget_get_io_series_net(wb_widget):
    io_series_net = wb_widget._get_io_series_net()
    expected = [
        {
            "label_name": "2D flow to 1D (all domains)",
            "in": ["1d__1d_2d_flow_in", "2d__1d_2d_flow_in"],
            "out": ["1d__1d_2d_flow_out", "2d__1d_2d_flow_out"],
            "type": "NETVOL",
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
    assert io_series_net == expected


def test_barmanger_2d_groundwater(wb_widget):
    io_series_2d_groundwater = wb_widget._get_io_series_2d_groundwater()
    bm_2d_groundwater = BarManager(io_series_2d_groundwater)
    expected_labels = [
        "groundwater flow",
        "in/exfiltration (domain exchange)",
        "leakage",
        "net change in storage",
    ]
    assert bm_2d_groundwater.xlabels == expected_labels


def helper_get_flows_and_dvol(domain=None):
    STORAGE_CHANGE_LABELS = ["net change in storage", "change in storage"]
    sum_inflow = 0
    sum_outflow = 0
    d_vol = 0
    for idx, label in enumerate(domain.xlabels):
        inflow = domain.end_balance_in[idx]
        outflow = domain.end_balance_out[idx]
        if label in STORAGE_CHANGE_LABELS:
            d_vol += inflow + outflow
        else:
            sum_inflow += inflow
            sum_outflow += outflow
    return sum_inflow, sum_outflow, d_vol


def test_water_balance_closure(wb_calculation, wb_widget, wb_polygon):
    # The netto inflows and outflows of the three sub-domains (1d, 2d,
    # 2d_groundwater) must equal the netto inflow and outflow"""
    time = wb_calculation.time
    flow = wb_calculation.flow
    t1 = min(time)
    t2 = max(time)

    io_series_net = wb_widget._get_io_series_net()
    io_series_2d = wb_widget._get_io_series_2d()
    io_series_2d_groundwater = wb_widget._get_io_series_2d_groundwater()
    io_series_1d = wb_widget._get_io_series_1d()

    bm_net = BarManager(io_series_net)
    bm_2d = BarManager(io_series_2d)
    bm_2d_groundwater = BarManager(io_series_2d_groundwater)
    bm_1d = BarManager(io_series_1d)

    # netto domain
    bm_net.calc_balance(time, flow, t1, t2, net=True)
    sum_inflow, sum_outflow, d_vol_net = helper_get_flows_and_dvol(domain=bm_net)
    assert _helper_round_numpy(d_vol_net) == _helper_round_numpy(
        sum([sum_inflow, sum_outflow])
    )

    # 1d domain
    bm_1d.calc_balance(time, flow, t1, t2)
    sum_inflow, sum_outflow, d_vol_1d = helper_get_flows_and_dvol(domain=bm_1d)
    assert _helper_round_numpy(d_vol_1d) == _helper_round_numpy(
        sum([sum_inflow, sum_outflow])
    )

    # 2d domain
    bm_2d.calc_balance(time, flow, t1, t2)
    sum_inflow, sum_outflow, d_vol_2d = helper_get_flows_and_dvol(domain=bm_2d)
    assert _helper_round_numpy(d_vol_2d) == _helper_round_numpy(
        sum([sum_inflow, sum_outflow])
    )

    # 2d_groundwater domain
    bm_2d_groundwater.calc_balance(
        time, flow, t1, t2, invert=["in/exfiltration (domain exchange)"]
    )
    sum_inflow, sum_outflow, d_vol_2d_gr = helper_get_flows_and_dvol(
        domain=bm_2d_groundwater
    )
    assert _helper_round_numpy(d_vol_2d_gr) == _helper_round_numpy(
        sum([sum_inflow, sum_outflow])
    )

    # the sum of volume changes in the 3 sub-domains must equal volume change
    # of the netto domain
    assert _helper_round_numpy(
        sum([d_vol_1d, d_vol_2d, d_vol_2d_gr])
    ) == _helper_round_numpy(d_vol_net)
