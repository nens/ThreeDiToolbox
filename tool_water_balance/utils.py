
from qgis.core import QgsCoordinateTransform
from qgis.core import QgsGeometry
from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import QMessageBox

from itertools import zip_longest
from logging import getLogger

import numpy as np

logger = getLogger(__name__)


class PolygonWithCRS:
    def __init__(self, polygon, crs):
        self.polygon = polygon
        self.crs = crs

    def transformed(self, crs):
        polygon = QgsGeometry(self.polygon)
        qct = QgsCoordinateTransform(self.crs, crs, QgsProject.instance())
        polygon.transform(qct)
        return polygon


class WrappedResult:
    def __init__(self, result):
        self.result = result

    def _get_layer_by_name(self, layer_name):
        layer_id = self.result.parent().layer_ids[layer_name]
        return QgsProject.instance().mapLayer(layer_id)

    @property
    def lines(self):
        return self._get_layer_by_name('flowline')

    @property
    def points(self):
        return self._get_layer_by_name('node')

    @property
    def pumps(self):
        return None  # TODO

    @property
    def text(self):
        return self.result.text()

    @property
    def parent_text(self):
        return self.result.parent().text()

    @property
    def threedi_result(self):
        return self.result.threedi_result

    def has_required_vars(self):
        if self.threedi_result.aggregate_result_admin is None:
            self._pop_up_no_agg_found()
            return False

        missing_agg_vars = self._get_missing_agg_vars(self.threedi_result)
        if missing_agg_vars:
            self._pop_up_missing_agg_vars(missing_agg_vars)
            return False
        return True

    def has_synchronized_timestamps(self):
        threedi_result = self.threedi_result
        t_q_cum = threedi_result.get_timestamps(parameter="q_cum")
        t_vol_c = threedi_result.get_timestamps(parameter="vol_current")
        if not (t_q_cum == t_vol_c).all():
            self._pop_up_not_synchronized_timestamps(
                t_q_cum.tolist(), t_vol_c.tolist()
            )
            return False
        return True

    def _get_missing_agg_vars(self, threedi_result):
        """Returns a list with tuples of aggregation vars (vol, discharge) +
        methods (cum, current, etc) that are not (but should be) in the
        v2_aggregation_settings

        1.  some vars_methods are always required: minimum_agg_vars
        2.  some vars methods are required when included in the model
            schematisation (e.g. pumps, laterals).
        """
        check_available_vars = threedi_result.available_vars

        ga = threedi_result.gridadmin
        gr = threedi_result.result_admin

        minimum_agg_vars = [
            ("q_cum_negative", "negative cumulative discharge"),
            ("q_cum_positive", "negative cumulative discharge"),
            ("q_cum", "cumulative discharge"),
            ("vol_current", "current volume"),
        ]

        # some vars must be aggregated when included in the model
        # schematisation (e.g. pumps, laterals). problem is that threedigrid
        # does not support e.g. ga.has_lateral, ga.has_leakage etc. For those
        # fields, we read the threedigrid metadata.
        simulated_vars_nodes = ga.nodes._meta.get_fields(only_names=True)

        if gr.has_pumpstations:
            to_add = ("q_pump_cum", "cumulative pump discharge")
            minimum_agg_vars.append(to_add)

        # TODO: wait for threedigrid's e.g. 'gr.has_rained')
        # u'rain' is always in simulated_vars_nodes. So it does not make sense
        # to check there. Thus, we're gonna read the nc's rain data
        if np.nanmax(gr.nodes.rain) > 0:
            to_add = ("rain_cum", "cumulative rain")
            minimum_agg_vars.append(to_add)

        # gr.has_simple_infiltration and gr.has_interception are added to
        # threedigrid some months after groundwater release. To coop with the
        # .h5 that has been created in that period we use the meta data
        try:
            if gr.has_simple_infiltration:
                to_add = (
                    "infiltration_rate_simple_cum",
                    "cumulative infiltration rate",
                )
                minimum_agg_vars.append(to_add)
        except AttributeError:
            if "infiltration" in simulated_vars_nodes:
                to_add = (
                    "infiltration_rate_simple_cum",
                    "cumulative infiltration rate",
                )
                minimum_agg_vars.append(to_add)

        try:
            if gr.has_interception:
                to_add = ("intercepted_volume_current", "current interception")
                minimum_agg_vars.append(to_add)
        except AttributeError:
            # gr.has_interception is added to threedigrid some months after
            # groundwater release. To coop with .h5 that has been created in
            # that period we read the simulated_vars_nodes
            if "intercepted_volume" in simulated_vars_nodes:
                to_add = ("intercepted_volume_current", "current interception")
                minimum_agg_vars.append(to_add)

        if "q_lat" in simulated_vars_nodes:
            to_add = ("q_lat_cum", "cumulative lateral discharge")
            minimum_agg_vars.append(to_add)

        if "leak" in simulated_vars_nodes:
            to_add = ("leak_cum", "cumulative leakage")
            minimum_agg_vars.append(to_add)

        if "q_sss" in simulated_vars_nodes:
            if np.count_nonzero(gr.nodes.timeseries(indexes=slice(0, -1)).q_sss) > 0:
                minimum_agg_vars.append(
                    ("q_sss_cum", "cumulative surface sources and sinks")
                )

        missing_vars = []
        for required_var in minimum_agg_vars:
            if required_var[0] not in check_available_vars:
                msg = "the aggregation nc misses aggregation: %s", required_var[1]
                logger.error(msg)
                missing_vars.append(required_var[1])
        return missing_vars

    def _pop_up_no_agg_found(self):
        header = "Error: No aggregation netcdf found"
        msg = (
            "The Water balance tool requires an 'aggregate_results_3di.nc' "
            "but this file could not be found. Please make sure you run "
            "your simulation using the 'v2_aggregation_settings' table "
            "with the following variables:"
            "\n\ncurrent:"
            "\n- volume"
            "\n- interception (in case model has interception)"
            "\n\ncumulative:"
            "\n- rain"
            "\n- discharge"
            "\n- leakage (in case model has leakage)"
            "\n- laterals (in case model has laterals)"
            "\n- pump discharge (in case model has pumps)"
            "\n- simple_infiltration (in case model has "
            "simple_infiltration)"
            "\n- sources and sinks (in case model has sources and sinks)"
            "\n\npositive cumulative:"
            "\n- discharge"
            "\n\nnegative cumulative:"
            "\n- discharge"
        )
        QMessageBox.warning(None, header, msg)

    def _pop_up_missing_agg_vars(self, missing_vars):
        header = "Error: Missing aggregation settings"
        msg = (
            "The Water balance tool found the 'aggregate_results_3di.nc' but "
            "the file does not include all required aggregation "
            "variables. Please add them to the sqlite table "
            "'v2_aggregation_settings' and run your simulation again. The "
            "required variables are:"
            "\n\ncurrent:"
            "\n- volume"
            "\n- interception (in case model has interception)"
            "\n\ncumulative:"
            "\n- rain"
            "\n- discharge"
            "\n- leakage (in case model has leakage)"
            "\n- laterals (in case model has laterals)"
            "\n- pump discharge (in case model has pumps)"
            "\n- simple_infiltration (in case model has "
            "simple_infiltration)"
            "\n- sources and sinks (in case model has sources and sinks)"
            "\n\npositive cumulative:"
            "\n- discharge"
            "\n\nnegative cumulative:"
            "\n- discharge"
            "\n\nYour aggregation .nc misses the following variables:\n"
            + ", ".join(missing_vars)
        )
        QMessageBox.warning(None, header, msg)

    def _pop_up_not_synchronized_timestamps(self, a, b):
        header = "Error: timestamps are not synchronized"
        table = "\n".join(f"{p} {q}" for p, q in zip_longest(a, b))
        msg = "q_cum and vol_current have different timesteps:\n" + table
        logger.warning(msg)
        QMessageBox.warning(None, header, msg)

    def __contains__(self, flow_name):
        """ Return if a flow is relevant for the wrapped result. """
        if flow_name in {
            "2D boundary flow",
            "2D flow",
            "lateral flow to 2D",
            "rain on 2D",
            "surface sources and sinks",
            "volume change 2D",
        }:
            return self.result.threedi_result.gridadmin.has_2d
        if flow_name in {
            "1D boundary flow",
            "1D flow",
            "lateral flow to 1D",
            "volume change 1D",
        }:
            return self.result.threedi_result.gridadmin.has_1d
        if flow_name in {
            "volume change groundwater",
            "leakage",
            "in/exfiltration (domain exchange)",
        }:
            return self.result.threedi_result.gridadmin.has_groundwater
        if flow_name in {
            "1D: 2D flow to 1D (domain exchange)",
            "1D: 2D flow to 1D",
            "2D flow to 1D (all domains)",
            "2D flow to 1D (domain exchange)",
            "2D flow to 1D",
            "2D: 2D flow to 1D (domain exchange)",
            "2D: 2D flow to 1D",
        }:
            return (
                self.result.threedi_result.gridadmin.has_1d and
                self.result.threedi_result.gridadmin.has_2d
            )
        if flow_name in {
            "pumps",
            "pump",
        }:
            return self.result.threedi_result.gridadmin.has_pumpstations
        if flow_name == "groundwater flow":
            return self.result.threedi_result.gridadmin.has_groundwater_flow
        if flow_name in {
            "simple infiltration",
            "constant infiltration",
        }:
            return self.result.threedi_result.gridadmin.has_simple_infiltration
        if flow_name == "interception":
            return self.result.threedi_result.gridadmin.has_interception
        if flow_name == "0D rainfall runoff on 1D":
            return self.result.threedi_result.gridadmin.has_0d
        return True  # everything else relevant
