from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Iterator, Dict

from shapely.geometry import LineString

try:
    from .leak_detector import LeakDetector, Edge, highest
except ImportError:
    from leak_detector import LeakDetector, Edge, highest

from threedi_results_analysis.utils.threedi_result_aggregation.base import (
    water_levels_at_cross_section,
    prepare_timeseries,
    aggregate_prepared_timeseries
)
from threedi_results_analysis.utils.threedi_result_aggregation.aggregation_classes import (
    Aggregation,
    AggregationSign,
)
from threedi_results_analysis.utils.threedi_result_aggregation.constants import (
    AGGREGATION_VARIABLES,
    AGGREGATION_METHODS,
)

import numpy as np
from osgeo import gdal
from threedigrid.admin.gridadmin import GridH5Admin
from threedigrid.admin.gridresultadmin import GridH5ResultAdmin

OLD = "OLD"
NEW = "NEW"


class LeakDetectorWithDischargeThreshold(LeakDetector):
    # TODO: re-implement result_edges() and result_obstacles()
    Q_NET_SUM = Aggregation(
        variable=AGGREGATION_VARIABLES.get_by_short_name("q"),
        method=AGGREGATION_METHODS.get_by_short_name("sum"),
        sign=AggregationSign("net", "Net"),
    )

    def __init__(
            self,
            grid_result_admin: GridH5ResultAdmin,
            dem: gdal.Dataset,
            flowline_ids: List[int],
            min_obstacle_height: float,
            min_discharge: float,
            search_precision: float = None,
            min_peak_prominence: float = None,
            obstacles: List[Tuple[LineString, float]] = None,
            feedback=None,
            start_time: float = None,
            end_time: float = None
    ):
        """
        Initialize LeakDetector with GridH5ResultAdmin instead of GridH5Admin
        and set start_time and end_time
        """
        self.grid_result_admin = grid_result_admin
        self.min_discharge = min_discharge
        self.start_time = start_time
        self.end_time = end_time
        if feedback:
            feedback.pushInfo(f"{datetime.now()}")
            feedback.setProgressText("Calculate cumulative discharges...")
        all_2d_open_water_flowlines = grid_result_admin.lines.subset('2D_OPEN_WATER').filter(id__in=flowline_ids)
        discharges, self.tintervals = prepare_timeseries(
            threedigrid_object=all_2d_open_water_flowlines,
            aggregation=self.Q_NET_SUM
        )
        q_net_sum = aggregate_prepared_timeseries(
            timeseries=discharges,
            tintervals=self.tintervals,
            start_time=self.start_time,
            aggregation=self.Q_NET_SUM,
        )
        relevant_flowline_ids = all_2d_open_water_flowlines.id[
            np.abs(q_net_sum) > self.min_discharge
        ]

        super().__init__(
            gridadmin=grid_result_admin,
            dem=dem,
            flowline_ids=relevant_flowline_ids,
            min_obstacle_height=min_obstacle_height,
            search_precision=search_precision,
            min_peak_prominence=min_peak_prominence,
            obstacles=obstacles,
            feedback=feedback
        )

        # convert edges to EdgeWithDischargeThreshold
        self._edge_dict = {
            line_nodes: EdgeWithDischargeThreshold.from_edge(edge=edge, ld=self)
            for line_nodes, edge in self._edge_by_line_nodes.items()
        }  # {line_nodes: Edge}
        self.edges = list(self._edge_dict.values())
        discharges = dict(zip(all_2d_open_water_flowlines.id, discharges.T))
        cumulative_discharges = dict(zip(all_2d_open_water_flowlines.id, q_net_sum))
        for edge in self.edges:
            edge.discharges = discharges[edge.flowline_id]
            edge.discharge_without_obstacle = cumulative_discharges[edge.flowline_id]

        # attributes set in calculate_water_levels_at_cross_section
        self.water_levels = None
        self.tintervals = None

    def run(self, feedback=None):
        super().run(feedback)
        self.calculate_water_levels_at_cross_section(feedback)
        self.calculate_discharge_reduction(feedback)

    def calculate_water_levels_at_cross_section(self, feedback=None):
        # get water_level_at_cross_section timeseries and time intervals
        if feedback:
            feedback.pushInfo(f"{datetime.now()}")
            feedback.setProgressText("Calculate water levels at cell edges...")
        water_levels, self.tintervals = water_levels_at_cross_section(
            gr=self.grid_result_admin,
            flowline_ids=list(self.flowlines.id),
            aggregation_sign=AggregationSign(short_name="net", long_name="Net")
        )
        water_levels_dict = self.bind_to_flowline_ids(water_levels.T)
        for edge in self.edges:
            edge.water_levels_at_cross_section = water_levels_dict[edge.flowline_id]

    def calculate_discharge_reduction(self, feedback=None):
        """
        Calculate cumulative discharge reduction [m3] for flowlines for which an obstacle is identified.
        Resulting {flowline_id: discharge_reduction} dict is stored in `self.discharge_reduction`
        """

        # select discharge timeseries for flowlines for which cumulative discharge exceeds threshold from previously
        # retrieved discharge timeseries
        if feedback:
            feedback.pushInfo(f"{datetime.now()}")
            feedback.setProgressText("Calculate discharge reduction...")

        for i, edge in enumerate(self.edges):
            if feedback:
                feedback.setProgress(100 * i / len(self.edges))
            if edge.obstacles:  # skip if no obstacle has been identified
                edge.calculate_discharge_reduction()

    def flowlines_with_high_discharge_reduction(self) -> List[int]:
        """Return a list of ids of flowlines for which the discharge reduction exceeds the threshold"""
        return [
            edge.flowline_id
            for edge in self.edges
            if edge.discharge_reduction or float("-inf") > self.min_discharge
        ]

    def results(self, geometry: str, flowline_ids: List[int] = None) -> Iterator[Dict]:
        """
        Return all edges that have an obstacle and a discharge reduction that exceeds `min_discharge`
        Returns results for all edges if flowline_ids is not specified, or results for specific flowlines only
        """
        if flowline_ids:
            relevant_flowline_ids = list(set(flowline_ids) & set(self.flowlines_with_high_discharge_reduction()))
        else:
            relevant_flowline_ids = self.flowlines_with_high_discharge_reduction()
        for result in super().results(geometry=geometry, flowline_ids=relevant_flowline_ids):
            yield result


class EdgeWithDischargeThreshold(Edge):
    def __init__(
            self,
            ld: LeakDetectorWithDischargeThreshold,
            cell_ids: Tuple[int],
            flowline_id: int,
    ):
        super().__init__(
            ld=ld,
            cell_ids=cell_ids,
            flowline_id=flowline_id,
        )
        self.discharges = None
        self.water_levels_at_cross_section = None
        self.discharge_without_obstacle = None
        self.discharge_with_obstacle = None
        self.discharge_reduction = None

        # new attributes
        self.new_obstacle_crest_level = None

    @classmethod
    def from_edge(cls, edge: Edge, ld: LeakDetectorWithDischargeThreshold):
        result_edge = cls(
            ld=ld,
            cell_ids=edge.cell_ids,
            flowline_id=edge.flowline_id
        )
        result_edge.obstacles = edge.obstacles

        # attributes set in calculate_geometries()
        result_edge.flowline_geometry = edge.flowline_geometry
        result_edge.geometry = edge.geometry
        result_edge.start_coord = edge.start_coord
        result_edge.end_coord = edge.end_coord

        # attributes set in calculate_exchange_level()
        if edge.exchange_levels is not None:
            result_edge.exchange_level = edge.exchange_level
            result_edge.exchange_levels = edge.exchange_levels
        else:
            # force to read from DEM because we neede exchange_levels for further calculations
            result_edge.calculate_exchange_levels()
        return result_edge

    def as_dict(self, geometry: str):
        result = super().as_dict(geometry=geometry)
        result["discharge_without_obstacle"] = self.discharge_without_obstacle
        result["discharge_with_obstacle"] = self.discharge_with_obstacle
        result["discharge_reduction"] = self.discharge_reduction
        return result

    def _get_obstacle_crest_level(self, which_obstacle: str):
        if which_obstacle == OLD:
            obstacle_crest_level = self.exchange_level
        elif which_obstacle == NEW:
            obstacle_crest_level = highest(self.obstacles).crest_level if self.obstacles else None
        else:
            raise ValueError(f"Value of argument 'which_obstacle' must be 'OLD' or 'NEW', not {which_obstacle}")
        obstacle_crest_level = np.min(self.exchange_levels) if obstacle_crest_level is None else obstacle_crest_level
        return obstacle_crest_level

    def wet_cross_sectional_area(self, water_level: float, which_obstacle: str):
        """
        Calculate the wet cross-sectional area from a 1D array of exchange levels (bed level values) and a water level.
        obstacle_crest_level may be specified to overrule exchange levels that are lower
        """
        obstacle_crest_level = self._get_obstacle_crest_level(which_obstacle)
        bed_levels = np.maximum(self.exchange_levels, obstacle_crest_level)
        water_depths = np.maximum(water_level - np.minimum(water_level, bed_levels), 0)
        return np.nansum(water_depths * self.ld.dem.RasterXSize)

    def wetted_perimeter(self, water_level: float, which_obstacle: str):
        """
        Calculate the wetted perimeter of a 2D cross-section; only the horizontal wet surface are taken into account
        """
        obstacle_crest_level = self._get_obstacle_crest_level(which_obstacle)
        return np.nansum(
            (
                np.maximum(self.exchange_levels, obstacle_crest_level) < water_level
            ) * self.ld.dem.RasterXSize
        )

    def discharge_reduction_factor(self, water_level: float):
        """
        reduction = Q_new/Q_old
        Based on:
         A: wet cross-sectional area
         v: flow velocity
         P: wetted perimeter

         Q = A*v (discharge)
         R = A/P (hydraulic radius)
         v = C*sqrt(R*i) (Chezy)
        So:
         Q = A * C * sqrt((A/P)*i)

        Assuming C and i are constant, we can ignore them when dividing Q_new by Q_old:
         reduction = (A_new * sqrt(A_new/P_new)) / (A_old * sqrt(A_old/P_old))
        """
        old_wet_cross_sectional_area = self.wet_cross_sectional_area(water_level=water_level, which_obstacle=OLD)
        new_wet_cross_sectional_area = self.wet_cross_sectional_area(water_level=water_level, which_obstacle=NEW)
        if old_wet_cross_sectional_area == 0 or new_wet_cross_sectional_area == 0:
            return 0
        old_wetted_perimeter = self.wetted_perimeter(water_level=water_level, which_obstacle=OLD)
        new_wetted_perimeter = self.wetted_perimeter(water_level=water_level, which_obstacle=NEW)
        result = np.sqrt(new_wet_cross_sectional_area / new_wetted_perimeter) / np.sqrt(old_wet_cross_sectional_area / old_wetted_perimeter)
        return result

    def discharge_reduction_factors(self, water_levels: np.array):
        """Vectorized version of `discharge_reduction_factor`"""
        v_discharge_reduction_factors = np.vectorize(self.discharge_reduction_factor, otypes=[float])
        return v_discharge_reduction_factors(water_levels)

    def calculate_discharge_reduction(self):
        """
        Calculate the difference in net cumulative discharge when an obstacle is applied to a flowline's cross-section
        """
        if self.obstacles:
            discharge_reduction_factors = self.discharge_reduction_factors(self.water_levels_at_cross_section)
            self.discharge_with_obstacle = np.nansum(self.discharges * discharge_reduction_factors * self.ld.tintervals)
            self.discharge_reduction = abs(self.discharge_with_obstacle - self.discharge_without_obstacle)


if __name__ == "__main__":
    DATA_DIR = Path(r"C:\Users\leendert.vanwolfswin\OneDrive - Nelen & Schuurmans\Documents 1\3Di\fuerthen_de - "
                    r"fuerthen_fuerthen (1)")
    RESULTS_DIR = DATA_DIR / "revision 14" / "results" / "sim_65948_fuerthen_40_mm_in_een_uur"
    DEM_FILENAME = DATA_DIR / "work in progress" / "schematisation" / "rasters" / "dem.tif"
    DEM_DATASOURCE = gdal.Open(str(DEM_FILENAME), gdal.GA_ReadOnly)
    GRIDADMIN_FILENAME = RESULTS_DIR / 'gridadmin.h5'
    RESULTS_FILENAME = RESULTS_DIR / 'results_3di.nc'
    GRIDADMIN = GridH5Admin(GRIDADMIN_FILENAME)
    GRIDRESULTADMIN = GridH5ResultAdmin(str(GRIDADMIN_FILENAME), str(RESULTS_FILENAME))
    MIN_PEAK_PROMINENCE = 0.05
    SEARCH_PRECISION = 0.001
    MIN_OBSTACLE_HEIGHT = 0.05

    # flowline_ids = [5972, 5973, 5974]

    leak_detector = LeakDetectorWithDischargeThreshold(
        grid_result_admin=GRIDRESULTADMIN,
        dem=DEM_DATASOURCE,
        flowline_ids=list(GRIDRESULTADMIN.lines.id),
        min_obstacle_height=MIN_OBSTACLE_HEIGHT,
        search_precision=SEARCH_PRECISION,
        min_peak_prominence=MIN_PEAK_PROMINENCE,
        min_discharge=1000
    )

    class MockFeedback:
        def setProgress(self, progress):
            pass

        def isCanceled(self):
            return False

    leak_detector.run()
    leak_detector.calculate_discharge_reduction()
    print([i for i in leak_detector.results(geometry="EDGE")])
    print([i for i in leak_detector.results(geometry="OBSTACLE")])
