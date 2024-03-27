from qgis.core import Qgis
from qgis.core import QgsFeatureRequest
from qgis.core import QgsVectorLayer
from qgis.core import QgsWkbTypes
from qgis.core import QgsGeometry
from qgis.gui import QgsHighlight
from qgis.gui import QgsMapToolIdentify
from qgis.gui import QgsRubberBand
from qgis.gui import QgsVertexMarker
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtCore import QEvent
from qgis.PyQt.QtCore import QMetaObject
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QBrush
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtGui import QPalette
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtGui import QTransform
from qgis.PyQt.QtWidgets import QAbstractItemView
from qgis.PyQt.QtWidgets import QComboBox
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.PyQt.QtWidgets import QHBoxLayout
from qgis.PyQt.QtWidgets import QLabel
from qgis.PyQt.QtWidgets import QPushButton
from qgis.PyQt.QtWidgets import QSizePolicy
from qgis.PyQt.QtWidgets import QSpacerItem
from qgis.PyQt.QtWidgets import QSplitter
from qgis.PyQt.QtWidgets import QTabWidget
from qgis.PyQt.QtWidgets import QTableView
from qgis.PyQt.QtWidgets import QVBoxLayout
from qgis.PyQt.QtWidgets import QWidget
from threedi_results_analysis import PLUGIN_DIR
from threedi_results_analysis.tool_water_balance.views.custom_pg_Items import RotateLabelAxisItem
from threedi_results_analysis.utils.user_messages import messagebar_message, StatusProgressBar

from ..utils import PolygonWithCRS
from ..config import AGG_CUMULATIVE_FLOW
from ..config import AGG_FLOW
from ..config import BC_IO_SERIES
from ..config import GRAPH_SERIES
from ..config import INPUT_SERIES
from ..config import TIME_UNITS_TO_SECONDS
from ..models.wb_item import WaterbalanceItemModel

from collections import defaultdict
from copy import deepcopy
from itertools import chain
import functools
import logging
import numpy as np
import pyqtgraph as pg


logger = logging.getLogger(__name__)

MSG_TITLE = "Water balance tool"
QCOLOR_RED = QColor(255, 0, 0)
POLYGON_TYPES = {
    QgsWkbTypes.MultiPolygon,
    QgsWkbTypes.MultiPolygonZ,
    QgsWkbTypes.MultiPolygon25D,
    QgsWkbTypes.Polygon,
    QgsWkbTypes.PolygonZ,
    QgsWkbTypes.Polygon25D,
}
VOLUME_CHANGE_SERIE_NAMES = {
    "volume change 2D",
    "volume change groundwater",
    "volume change 1D",
}

SERIES_NAME_TO_LINE_TYPES = {
    "2D flow": ["2d"],
    "2D boundary flow": ["2d_bound"],
    "1D flow": ["1d"],
    "1D boundary flow": ["1d_bound"],
    "2D flow to 1D (domain exchange)": ["1d_2d_exch"],
    "2D flow to 1D": ["1d__1d_2d_flow", "2d__1d_2d_flow"],
    "pumps": ["pumps_hoover"],
    "groundwater flow": ["2d_groundwater"],
    "in/exfiltration (domain exchange)": [
        "2d_vertical_infiltration_pos",
        "2d_vertical_infiltration_neg",
    ],
}

SERIES_NAME_TO_NODE_TYPES = {
    "volume change": ["1d", "2d", "2d_groundwater"],
    "volume change 2D": ["2d"],
    "volume change 1D": ["1d"],
    "volume change groundwater": ["2d_groundwater"],
    "rain on 2D": ["2d"],
    "0D rainfall runoff on 1D": ["1d"],
    "lateral flow to 1D": ["1d"],
    "lateral flow to 2D": ["2d"],
    "leakage": ["2d"],
    "interception": ["2d"],
    "constant infiltration": ["2d"],
    "external (rain and laterals)": ["1d", "2d"],
    "surface sources and sinks": ["2d"],
}


# some helper functions and classes
#######################


def _get_request_filter(ids):
    ids_flat = list(set([i for j in list(ids.values()) for i in j]))
    return QgsFeatureRequest().setFilterFids(ids_flat)


def _get_feature_iterator(layer, request_filter):
    # mainly pumps are often not present
    if layer:
        return layer.getFeatures(request_filter)
    else:
        return []

#######################


@functools.total_ordering
class Bar(object):
    """Bar for water balance barchart with positive and negative components."""

    SERIES_INDEX = dict(INPUT_SERIES)

    def __init__(self, label_name, in_series, out_series, type):
        self.label_name = label_name
        self.in_series = in_series
        self.out_series = out_series
        self.type = type
        self._balance_in = None
        self._balance_out = None

    @staticmethod
    def _get_time_indices(ts, t1, t2):
        """Time series indices in range t1-t2."""
        idx_x1 = np.searchsorted(ts, t1)
        if not t2:
            idx_x2 = len(ts)
        else:
            idx_x2 = np.searchsorted(ts, t2)
        return np.arange(idx_x1, idx_x2)

    @property
    def end_balance_in(self):
        return self._balance_in

    def set_end_balance_in(self, ts, ts_series, t1=0, t2=None):
        idxs = [self.SERIES_INDEX[name] for name in self.in_series]
        ts_indices_sliced = self._get_time_indices(ts, t1, t2)
        ts_deltas = np.concatenate(([0], np.diff(ts)))
        # shape = (N_idxs, len(ts))
        balance_tmp = (ts_deltas * ts_series[:, idxs].T).clip(min=0)
        self._balance_in = balance_tmp[:, ts_indices_sliced].sum()

    @property
    def end_balance_out(self):
        return self._balance_out

    def set_end_balance_out(self, ts, ts_series, t1=0, t2=None):
        idxs = [self.SERIES_INDEX[name] for name in self.out_series]
        ts_indices_sliced = self._get_time_indices(ts, t1, t2)
        ts_deltas = np.concatenate(([0], np.diff(ts)))
        balance_tmp = (ts_deltas * ts_series[:, idxs].T).clip(max=0)
        self._balance_out = balance_tmp[:, ts_indices_sliced].sum()

    def calc_balance(self, ts, ts_series, t1=0, t2=None):
        """Calculate balance values."""
        self.set_end_balance_in(ts, ts_series, t1, t2)
        self.set_end_balance_out(ts, ts_series, t1, t2)
        if self.is_storage_like:
            self.convert_to_net()

    def convert_to_net(self):
        """Make a bar that contains the net value (positive or negative)."""
        # NOTE: use addition because out is negative
        net_val = self._balance_in + self._balance_out
        if net_val > 0:
            self._balance_in = net_val
            self._balance_out = 0
        else:
            self._balance_in = 0
            self._balance_out = net_val

    def invert(self):
        """Flip positive to negative and vice versa."""
        self._balance_in, self._balance_out = (
            -1 * self._balance_out,
            -1 * self._balance_in,
        )

    @property
    def is_storage_like(self):
        return "storage" in self.label_name

    # add sorting
    def __lt__(self, other):
        # TODO: label_names are not unique, should add 'type' to make a
        # primary key
        if not self.is_storage_like and other.is_storage_like:
            return True
        elif self.is_storage_like and not other.is_storage_like:
            return False
        return self.label_name < other.label_name


class BarManager(object):
    def __init__(self, series):
        self.series = series
        self.bars = sorted(
            [
                Bar(
                    label_name=x["label_name"],
                    in_series=x["in"],
                    out_series=x["out"],
                    type=x["type"],
                )
                for x in series
            ]
        )

    def calc_balance(self, ts, ts_series, t1, t2, net=False, invert=[]):
        for b in self.bars:
            b.calc_balance(ts, ts_series, t1=t1, t2=t2)
            if net:
                b.convert_to_net()
            if b.label_name in invert:
                b.invert()

    @property
    def x(self):
        return np.arange(len(self.bars))

    @property
    def xlabels(self):
        return [b.label_name for b in self.bars]

    @property
    def end_balance_in(self):
        return [b.end_balance_in for b in self.bars]

    @property
    def end_balance_out(self):
        return [b.end_balance_out for b in self.bars]


class WaterbalanceItemTable(QTableView):
    hoverExitAllRows = pyqtSignal()  # exit the whole widget
    hoverExitRow = pyqtSignal(str)
    hoverEnterRow = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QTreeView::item:hover{background-color:#FFFF00;}")
        self.setMouseTracking(True)
        self.verticalHeader().hide()
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.model = None

        self._last_hovered_row = -1
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
        result = QTableView.eventFilter(self, widget, event)
        if widget is not self.viewport():
            return result

        if event.type() == QEvent.Leave:
            self.hoverExitAllRows.emit()
            new_row = -1
        elif event.type() == QEvent.MouseMove:
            new_row = self.indexAt(event.pos()).row()
        else:
            return result

        old_row = self._last_hovered_row

        if old_row >= 0 and new_row != old_row:
            old_name = self.model.rows[old_row].name.value
            self.hover_exit(old_row)
            self.hoverExitRow.emit(old_name)

        if new_row >= 0 and new_row != old_row:
            new_name = self.model.rows[new_row].name.value
            self.hover_enter(new_row)
            self.hoverEnterRow.emit(new_name)

        self._last_hovered_row = new_row
        return result

    def hover_enter(self, row_nr):
        item = self.model.rows[row_nr]
        name = item.name.value

        if name in VOLUME_CHANGE_SERIE_NAMES:
            item.fill_color.value = item.fill_color.value[:3] + [0]
            item.pen_color.value = item.pen_color.value[:3] + [255]
        else:
            item.fill_color.value = item.fill_color.value[:3] + [220]
            item.pen_color.value = item.pen_color.value[:3] + [255]

    def hover_exit(self, row_nr):

        item = self.model.rows[row_nr]
        name = item.name.value

        if name in VOLUME_CHANGE_SERIE_NAMES:
            item.fill_color.value = item.fill_color.value[:3] + [0]
            item.pen_color.value = item.pen_color.value[:3] + [180]
        else:
            item.fill_color.value = item.fill_color.value[:3] + [150]
            item.pen_color.value = item.pen_color.value[:3] + [180]

    def setModel(self, model):
        super().setModel(model)
        self.model = model
        self.model.set_column_sizes_on_view(self)


class WaterBalancePlotWidget(pg.PlotWidget):
    def __init__(self, model, result):
        super().__init__()
        self.model = model
        self.result = result
        self.showGrid(True, True, 0.5)
        self.hideButtons()
        self.setLabel("bottom", "time", "hrs")
        self.setLabel("left", "flow", "m³/s")
        # Auto SI prefix scaling doesn't work properly with m3, m2 etc.
        self.getAxis("left").enableAutoSIPrefix(False)

        self._plot_data_items = None

    def redraw_water_balance(self, time, time_label, values, values_label):
        """
        Plotdata depends on the previous item, to be able to stack on top of
        it. Therefore adding to the graph goes in reversed order.
        """
        self.clear()
        zeros = np.zeros(shape=(np.size(time, 0),))
        zero_serie = pg.PlotDataItem(
            x=time,
            y=zeros,
            connect="finite",
            pen=pg.mkPen(color=QColor(0, 0, 0, 200), width=1),
        )
        self.addItem(zero_serie, ignoreBounds=True)

        # all item.name.value (e.g. '1d-2d flow', 'pumps', 'rain') have both a
        # 'in' and 'out' flow: so two lines that together form a graph.
        # However the volume change lines are summed into 1 line (so no out and
        # in)
        self._plot_data_items = defaultdict(dict)
        for d7n in ["in", "out"]:
            prev_serie = zeros
            prev_pldi = zero_serie
            for item in self.model.rows:
                name = item.name.value
                _plots = self._plot_data_items[name]
                if item.active.value:
                    if name in VOLUME_CHANGE_SERIE_NAMES:
                        pen_color = item.pen_color.value
                        not_cum_serie = (
                            values[name]["values"]["in"] + values[name]["values"]["out"]
                        )
                        plot_item = pg.PlotDataItem(
                            x=time,
                            y=not_cum_serie,
                            connect="finite",
                            pen=pg.mkPen(
                                color=QColor(*pen_color), width=4, style=Qt.DashDotLine
                            ),
                        )
                        # only get 1 line (the sum of 'in' and 'out')
                        _plots["sum"] = plot_item

                    else:  # name not in VOLUME_CHANGE_SERIE_NAMES
                        pen_color = item.pen_color.value
                        fill_color = item.fill_color.value
                        cum_serie = prev_serie + values[name]["values"][d7n]
                        plot_item = pg.PlotDataItem(
                            x=time,
                            y=cum_serie,
                            connect="finite",
                            pen=pg.mkPen(color=QColor(*pen_color), width=1),
                        )
                        fill = pg.FillBetweenItem(
                            prev_pldi, plot_item, pg.mkBrush(*fill_color)
                        )
                        # keep reference
                        _plots[d7n] = plot_item
                        _plots[d7n + "fill"] = fill
                        prev_serie = cum_serie
                        prev_pldi = plot_item

        # add PlotItems to graph
        for d7n in ["in", "out"]:
            for item in reversed(self.model.rows):
                name = item.name.value
                _plots = self._plot_data_items[name]
                if item.active.value:
                    if name in VOLUME_CHANGE_SERIE_NAMES:
                        self.addItem(_plots["sum"], ignoreBounds=True)
                    else:  # name not in VOLUME_CHANGE_SERIE_NAMES
                        self.addItem(_plots[d7n], ignoreBounds=True)
                        self.addItem(_plots[d7n + "fill"], ignoreBounds=True)

        # set range to contents
        x_min = min(pdi.xData.min() for pdi in self.plotItem.listDataItems())
        x_max = max(pdi.xData.max() for pdi in self.plotItem.listDataItems())
        self.setXRange(x_min, x_max, padding=None, update=True)

        y_min = min(pdi.yData.min() for pdi in self.plotItem.listDataItems())
        y_max = max(pdi.yData.max() for pdi in self.plotItem.listDataItems())
        self.setYRange(y_min, y_max, padding=None, update=True)

        # one would say a simple autorange should work, but it does not
        # self.autoRange(padding=0)

        # set labels
        self.setLabel("left", *values_label)
        self.setLabel("bottom", *time_label)

        # set labels for in and out fluxes TODO fix?
        text_upper = pg.TextItem(text="out", anchor=(0, 1), angle=-90)
        text_upper.setPos(0, 0)
        text_lower = pg.TextItem(text="in", anchor=(1, 1), angle=-90)
        text_lower.setPos(0, 0)
        self.addItem(text_upper)
        self.addItem(text_lower)

    def hover_enter_plot_highlight(self, name):
        if name not in self._plot_data_items:  # meaning it is not active
            return
        plots = self._plot_data_items[name]
        item = [item for item in self.model.rows if item.name.value == name][0]
        if "in" in plots:
            plots["in"].setPen(color=item.pen_color.value, width=1)
            plots["infill"].setBrush(pg.mkBrush(item.fill_color.value))
        if "out" in plots:
            plots["out"].setPen(color=item.pen_color.value, width=1)
            plots["outfill"].setBrush(pg.mkBrush(item.fill_color.value))
        if "sum" in plots:
            plots["sum"].setPen(
                color=item.pen_color.value, width=4, style=Qt.DashDotLine
            )

    def hover_exit_plot_highlight(self, name):
        if name not in self._plot_data_items:  # meaning it is not active
            return
        plots = self._plot_data_items[name]
        item = [item for item in self.model.rows if item.name.value == name][0]
        if "in" in plots:
            plots["in"].setPen(color=item.pen_color.value, width=1)
            plots["infill"].setBrush(pg.mkBrush(item.fill_color.value))
        if "out" in plots:
            plots["out"].setPen(color=item.pen_color.value, width=1)
            plots["outfill"].setBrush(pg.mkBrush(item.fill_color.value))
        if "sum" in plots:
            plots["sum"].setPen(
                color=item.pen_color.value, width=4, style=Qt.DashDotLine
            )


class WaterBalanceWidget(QDockWidget):
    closingWidget = pyqtSignal()

    def __init__(self, title, iface, manager):
        super().__init__(title)

        self.iface = iface
        self.manager = manager
        self.wb_polygon_highlight = None

        # setup ui
        self.setup_ui(self)

        self.model = WaterbalanceItemModel()
        self.model.dataChanged.connect(self.data_changed)
        self.wb_item_table.setModel(self.model)
        self.selection_vis = SelectionVisualisation(iface.mapCanvas())

        # fill comboboxes with selections
        self.agg_combo_box.insertItems(0, [AGG_FLOW, AGG_CUMULATIVE_FLOW])
        self.ts_units_combo_box.insertItems(0, ["hrs", "mins", "s"])

        # add listeners
        self.select_polygon_button.clicked.connect(self._set_map_tool)
        self.chart_button.clicked.connect(self.show_barchart)

        self.wb_item_table.hoverEnterRow.connect(self.hover_enter_action)
        self.wb_item_table.hoverExitRow.connect(self.hover_exit_action)
        self.activate_all_button.clicked.connect(self.activate_layers)
        self.deactivate_all_button.clicked.connect(self.deactivate_layers)

        self.tab_widget.currentChanged.connect(self.tab_changed)
        self.agg_combo_box.currentIndexChanged.connect(self.combo_changed)
        self.ts_units_combo_box.currentIndexChanged.connect(self.combo_changed)

        # initially turn on tool
        self._set_map_tool()

    @property
    def agg(self):
        return self.agg_combo_box.currentText()

    @property
    def time_units(self):
        return self.ts_units_combo_box.currentText()

    def _get_io_series_net(self):
        io_series_net = [
            x
            for x in BC_IO_SERIES
            if (
                x["type"] in ["2d", "2d_vert", "2d_groundwater", "1d"]
                and "storage" not in x["label_name"]
                and "exchange" not in x["label_name"]
                and x["label_name"] != "1D: 2D flow to 1D"
                and x["label_name"] != "2D: 2D flow to 1D"
                and x["label_name"] != "1D: 2D flow to 1D (domain exchange)"
                and x["label_name"] != "2D: 2D flow to 1D (domain exchange)"
            )
            or x["type"] == "NETVOL"
        ]
        return io_series_net

    def _get_io_series_2d(self):
        io_series_2d = [
            x
            for x in BC_IO_SERIES
            if x["type"] in ["2d", "2d_vert"]
            and x["label_name"] != "1D: 2D flow to 1D"
            and x["label_name"] != "1D: 2D flow to 1D (domain exchange)"
        ]
        return io_series_2d

    def _get_io_series_2d_groundwater(self):
        io_series_2d_groundwater = [
            x for x in BC_IO_SERIES if x["type"] in ["2d_groundwater", "2d_vert"]
        ]
        return io_series_2d_groundwater

    def _get_io_series_1d(self):
        io_series_1d = [
            x
            for x in BC_IO_SERIES
            if x["type"] == "1d"
            and x["label_name"] != "2D: 2D flow to 1D"
            and x["label_name"] != "2D: 2D flow to 1D (domain exchange)"
        ]
        return io_series_1d

    def show_barchart(self):
        """
        Show a pop-up with a barchart based on the current temporal view in the
        plot widget
        """
        if not self.manager:
            return

        # determine the time in seconds from the current plot state
        plot_widget = self.tab_widget.currentWidget()
        viewbox_state = plot_widget.getPlotItem().getViewBox().getState()
        view_range = viewbox_state["viewRange"]
        t1, t2 = view_range[0]
        t1 = t1 * TIME_UNITS_TO_SECONDS[self.time_units]
        t2 = t2 * TIME_UNITS_TO_SECONDS[self.time_units]

        self.wb_tabbed_view = QTabWidget()

        io_series_net = self._get_io_series_net()
        io_series_2d = self._get_io_series_2d()
        io_series_2d_groundwater = self._get_io_series_2d_groundwater()
        io_series_1d = self._get_io_series_1d()

        for result in self.manager:
            calc = self.manager[result]
            tab_label = calc.label
            time, flow = calc.time, calc.flow
            relevant = functools.partial(calc.filter_series, "label_name")

            bm_net = BarManager(relevant(io_series_net))
            bm_2d = BarManager(relevant(io_series_2d))
            bm_2d_groundwater = BarManager(relevant(io_series_2d_groundwater))
            bm_1d = BarManager(relevant(io_series_1d))

            bm_net.calc_balance(time, flow, t1, t2, net=True)
            bm_2d.calc_balance(time, flow, t1, t2)
            bm_2d_groundwater.calc_balance(
                time, flow, t1, t2, invert=["in/exfiltration (domain exchange)"]
            )
            bm_1d.calc_balance(time, flow, t1, t2)

            t_start = max(0, t1)
            wb_barchart_widget = pg.GraphicsView(self.wb_tabbed_view)

            layout = pg.GraphicsLayout()
            wb_barchart_widget.setCentralItem(layout)
            text = "Water balance from t=%.2f to t=%.2f \n Model name: %s" % (
                t_start,
                t2,
                calc.wrapped_result.threedi_result.short_model_slug,
            )
            layout.addLabel(text, row=0, col=0, colspan=3)

            def get_keyword_indexes(input_list, keyword):
                """Return a list of indexes from `input_list` which contain the
                `keyword`"""
                bar_indexes_to_mark = []
                for index, label in enumerate(input_list):
                    if keyword in label:
                        bar_indexes_to_mark.append(index)
                return bar_indexes_to_mark

            # We want to mark some bars with a different color. Labels with the key
            # 'domain exchange' and the last label ('change in storage').
            domain_exchange_key = "(domain exchange)"
            standard_in_brush = QBrush(QColor(0, 122, 204))
            standard_out_brush = QBrush(QColor(255, 128, 0))

            domain_exchange_in_brush = QBrush(
                QColor(0, 122, 204), style=Qt.BDiagPattern
            )  # Qt.BDiagPattern
            domain_exchange_in_brush.setTransform(QTransform().scale(0.01, 0.01))
            domain_exchange_out_brush = QBrush(QColor(255, 128, 0), style=Qt.BDiagPattern)
            domain_exchange_out_brush.setTransform(QTransform().scale(0.01, 0.01))
            change_storage_brush = QBrush(QColor("grey"))

            # #####
            # Net #
            # #####

            domain_exchange_indexes = get_keyword_indexes(
                bm_net.xlabels, domain_exchange_key
            )
            in_brushes = [standard_in_brush] * (len(bm_net.xlabels) - 1)
            for i in domain_exchange_indexes:
                in_brushes[i] = domain_exchange_in_brush
            in_brushes.append(change_storage_brush)
            out_brushes = [standard_out_brush] * (len(bm_net.xlabels) - 1)
            for i in domain_exchange_indexes:
                out_brushes[i] = domain_exchange_out_brush
            out_brushes.append(change_storage_brush)

            bg_net_in = pg.BarGraphItem(
                x=bm_net.x, height=bm_net.end_balance_in, width=0.6, brushes=in_brushes
            )
            bg_net_out = pg.BarGraphItem(
                x=bm_net.x, height=bm_net.end_balance_out, width=0.6, brushes=out_brushes
            )
            axis_net = RotateLabelAxisItem(25, "bottom")
            net_plot = layout.addPlot(
                row=1, col=0, colspan=2, axisItems={"bottom": axis_net}
            )
            net_plot.addItem(bg_net_in)
            net_plot.addItem(bg_net_out)
            axis_net.setHeight(100)
            axis_net.setTicks([list(zip(bm_net.x, bm_net.xlabels))])

            net_plot.setTitle("Net water balance")
            y_axis = net_plot.getAxis("left")
            y_axis.setLabel("volume (m³)")
            net_plot.getViewBox().setLimits(xMin=-1, xMax=max(bm_net.x) + 2)

            # # ######
            # # Logo #
            # # ######

            path_3di_logo = str(PLUGIN_DIR / "icons" / "icon.png")
            logo_3di = QPixmap(path_3di_logo)
            logo_3di = logo_3di.scaledToHeight(40)
            label_3di = QLabel()
            label_3di.setPixmap(logo_3di)

            path_topsector_logo = str(PLUGIN_DIR / "icons" / "topsector_small.png")
            logo_topsector = QPixmap(path_topsector_logo)
            logo_topsector = logo_topsector.scaledToHeight(40)
            label_topsector = QLabel()
            label_topsector.setPixmap(logo_topsector)

            path_deltares_logo = str(PLUGIN_DIR / "icons" / "deltares_small.png")
            logo_deltares = QPixmap(path_deltares_logo)
            logo_deltares = logo_deltares.scaledToHeight(40)
            label_deltares = QLabel()
            label_deltares.setPixmap(logo_deltares)

            logo_label_text = QLabel("Powered by 3Di, Topsector Water and Deltares")

            powered_by_widget = QWidget()
            pallete = QPalette(QColor("white"))
            powered_by_widget.setAutoFillBackground(True)
            powered_by_widget.setPalette(pallete)
            powered_by_layout = QVBoxLayout()
            powered_by_widget.setMaximumHeight(130)

            logo_container = QWidget()
            logo_container.setMaximumWidth(300)
            logo_container_layout = QHBoxLayout()
            logo_container_layout.addWidget(label_3di)
            logo_container_layout.addWidget(label_topsector)
            logo_container_layout.addWidget(label_deltares)
            logo_container.setLayout(logo_container_layout)

            powered_by_layout.addWidget(logo_label_text)
            powered_by_layout.addWidget(logo_container)

            powered_by_widget.setLayout(powered_by_layout)
            logo_ProxyWidget = layout.scene().addWidget(powered_by_widget)
            layout.addItem(logo_ProxyWidget, row=1, col=2)

            # # ####
            # # 2D #
            # # ####

            domain_exchange_indexes = get_keyword_indexes(
                bm_2d.xlabels, domain_exchange_key
            )
            in_brushes = [standard_in_brush] * (len(bm_2d.xlabels) - 1)
            for i in domain_exchange_indexes:
                in_brushes[i] = domain_exchange_in_brush
            in_brushes.append(change_storage_brush)
            out_brushes = [standard_out_brush] * (len(bm_2d.xlabels) - 1)
            for i in domain_exchange_indexes:
                out_brushes[i] = domain_exchange_out_brush
            out_brushes.append(change_storage_brush)

            surface_in = pg.BarGraphItem(
                x=bm_2d.x, height=bm_2d.end_balance_in, width=0.6, brushes=in_brushes
            )
            surface_out = pg.BarGraphItem(
                x=bm_2d.x, height=bm_2d.end_balance_out, width=0.6, brushes=out_brushes
            )
            axis_surface = RotateLabelAxisItem(25, "bottom")
            surface_plot = layout.addPlot(row=2, col=0, axisItems={"bottom": axis_surface})
            surface_plot.addItem(surface_in)
            surface_plot.addItem(surface_out)
            axis_surface.setHeight(100)
            axis_surface.setTicks([list(zip(bm_net.x, bm_2d.xlabels))])

            surface_plot.setTitle("2D surface water domain")
            y_axis = surface_plot.getAxis("left")
            y_axis.setLabel("volume (m³)")

            surface_plot.getViewBox().setLimits(xMin=-1, xMax=max(bm_2d.x) + 2)

            # # ################
            # # 2D groundwater #
            # # ################

            domain_exchange_indexes = get_keyword_indexes(
                bm_2d_groundwater.xlabels, domain_exchange_key
            )
            in_brushes = [standard_in_brush] * (len(bm_2d_groundwater.xlabels) - 1)
            for i in domain_exchange_indexes:
                in_brushes[i] = domain_exchange_in_brush
            in_brushes.append(change_storage_brush)
            out_brushes = [standard_out_brush] * (len(bm_2d_groundwater.xlabels) - 1)
            for i in domain_exchange_indexes:
                out_brushes[i] = domain_exchange_out_brush
            out_brushes.append(change_storage_brush)

            groundwater_in = pg.BarGraphItem(
                x=bm_2d_groundwater.x,
                height=bm_2d_groundwater.end_balance_in,
                width=0.6,
                brushes=in_brushes,
            )
            groundwater_out = pg.BarGraphItem(
                x=bm_2d_groundwater.x,
                height=bm_2d_groundwater.end_balance_out,
                width=0.6,
                brushes=out_brushes,
            )
            axis_groundwater = RotateLabelAxisItem(25, "bottom")
            groundwater_plot = layout.addPlot(
                row=2, col=1, axisItems={"bottom": axis_groundwater}
            )
            groundwater_plot.addItem(groundwater_in)
            groundwater_plot.addItem(groundwater_out)
            axis_groundwater.setHeight(100)
            axis_groundwater.setTicks(
                [list(zip(bm_2d_groundwater.x, bm_2d_groundwater.xlabels))]
            )

            groundwater_plot.setTitle("2D groundwater domain")
            y_axis = groundwater_plot.getAxis("left")
            y_axis.setLabel("volume (m³)")
            groundwater_plot.getViewBox().setLimits(
                xMin=-1, xMax=max(bm_2d_groundwater.x) + 2
            )

            # # ####
            # # 1D #
            # # ####

            domain_exchange_indexes = get_keyword_indexes(
                bm_1d.xlabels, domain_exchange_key
            )
            in_brushes = [standard_in_brush] * (len(bm_1d.xlabels) - 1)
            for i in domain_exchange_indexes:
                in_brushes[i] = domain_exchange_in_brush
            in_brushes.append(change_storage_brush)
            out_brushes = [standard_out_brush] * (len(bm_1d.xlabels) - 1)
            for i in domain_exchange_indexes:
                out_brushes[i] = domain_exchange_out_brush
            out_brushes.append(change_storage_brush)

            network1d_in = pg.BarGraphItem(
                x=bm_1d.x, height=bm_1d.end_balance_in, width=0.6, brushes=in_brushes
            )
            network1d_out = pg.BarGraphItem(
                x=bm_1d.x, height=bm_1d.end_balance_out, width=0.6, brushes=out_brushes
            )
            axis_network1d = RotateLabelAxisItem(25, "bottom")
            network1d_plot = layout.addPlot(
                row=2, col=2, axisItems={"bottom": axis_network1d}
            )
            network1d_plot.addItem(network1d_in)
            network1d_plot.addItem(network1d_out)
            axis_network1d.setHeight(100)
            axis_network1d.setTicks([list(zip(bm_1d.x, bm_1d.xlabels))])

            network1d_plot.setTitle("1D network domain")
            y_axis = network1d_plot.getAxis("left")
            y_axis.setLabel("volume (m³)")
            network1d_plot.getViewBox().setLimits(xMin=-1, xMax=max(bm_1d.x) + 2)

            # Link y-axes
            surface_plot.setYLink(groundwater_plot)
            surface_plot.setYLink(network1d_plot)
            network1d_plot.setYLink(groundwater_plot)

            # Set y-range so all bars are visible
            y_min = min(
                bm_2d.end_balance_out
                + bm_2d_groundwater.end_balance_out
                + bm_1d.end_balance_out
            )
            y_max = max(
                bm_2d.end_balance_in
                + bm_2d_groundwater.end_balance_in
                + bm_1d.end_balance_in
            )
            network1d_plot.setYRange(min=y_min, max=y_max)

            self.wb_tabbed_view.addTab(wb_barchart_widget, tab_label)

        self.wb_tabbed_view.setWindowTitle("Waterbalance")
        self.wb_tabbed_view.resize(1000, 600)
        self.wb_tabbed_view.show()

    def data_changed(self, index):
        if self.model.columns[index.column()].name == "active":
            self.update_water_balance(reset_model=False)

    def combo_changed(self, index):
        self.update_water_balance(reset_model=False)

    def tab_changed(self, index):
        self.update_water_balance(reset_model=False)

    def hover_enter_action(self, name):
        if not self.manager:
            return

        # plot highlight
        self.tab_widget.currentWidget().hover_enter_plot_highlight(name)

        # map geometry highlight
        result = self.tab_widget.currentWidget().result
        calc = self.manager[result]

        # note that using getitem on qgs_lines and qgs_points works because
        # they are defaultdict(list)
        line_geoms = list(chain(*(
            calc.qgs_lines[t] for t in SERIES_NAME_TO_LINE_TYPES.get(name, [])
        )))
        point_geoms = list(chain(*(
            calc.qgs_points[t] for t in SERIES_NAME_TO_NODE_TYPES.get(name, [])
        )))

        self.selection_vis.update(line_geoms, point_geoms)

    def hover_exit_action(self, name):
        if not self.manager:
            return

        # plot highlight
        self.tab_widget.currentWidget().hover_exit_plot_highlight(name)

        # map geometry highlight
        self.selection_vis.reset()

    def _set_map_tool(self):
        self.iface.mapCanvas().setMapTool(self.map_tool_select_polygon)

    def _unset_map_tool(self):
        self.iface.mapCanvas().unsetMapTool(self.map_tool_select_polygon)

    def activate_layers(self):
        self.model.dataChanged.disconnect(self.data_changed)
        for item in self.model.rows:
            item.active.value = True
        self.model.dataChanged.connect(self.data_changed)
        self.update_water_balance(reset_model=False)

    def deactivate_layers(self):
        self.model.dataChanged.disconnect(self.data_changed)
        for item in self.model.rows:
            item.active.value = False
        self.model.dataChanged.connect(self.data_changed)
        self.update_water_balance(reset_model=False)

    def get_table_data(self):
        """
        Only the config, no actual result data. The link between item and data
        will be the names of the series. This will be fed to insertRows on the
        model.
        """
        table_data = deepcopy(GRAPH_SERIES)

        for item in table_data:
            item["active"] = True
            item["fill_color"] = [
                int(c) for c in item["def_fill_color"].split(",")
            ]
            item["pen_color"] = [
                int(c) for c in item["def_pen_color"].split(",")
            ]

        return table_data

    def update_water_balance(self, index=None, reset_model=False):
        """
        Redraw plots after comboboxes or active tab changes.
        """
        if not self.manager:
            self.model.removeRows(0, len(self.model.rows))
            return

        plot_widget = self.tab_widget.currentWidget()
        calc = self.manager[plot_widget.result]

        if reset_model:
            table_data = calc.filter_series(
                key="name", series=self.get_table_data(),
            )
            self.model.removeRows(0, len(self.model.rows))
            self.model.insertRows(table_data)

        graph_data = calc.get_graph_data(agg=self.agg, time_units=self.time_units)
        plot_widget.redraw_water_balance(**graph_data)

    def closeEvent(self, event):
        self.select_polygon_button.clicked.disconnect(self._set_map_tool)
        self.chart_button.clicked.disconnect(self.show_barchart)

        self.wb_item_table.hoverEnterRow.disconnect(self.hover_enter_action)
        self.wb_item_table.hoverExitRow.disconnect(self.hover_exit_action)
        self.activate_all_button.clicked.disconnect(self.activate_layers)
        self.deactivate_all_button.clicked.disconnect(self.deactivate_layers)

        self.tab_widget.currentChanged.disconnect(self.tab_changed)
        self.agg_combo_box.currentIndexChanged.disconnect(self.combo_changed)
        self.ts_units_combo_box.currentIndexChanged.disconnect(self.combo_changed)

        self.unset_wb_polygon()
        self._unset_map_tool()
        self.closingWidget.emit()
        event.accept()

    def setup_ui(self, dock_widget):
        """
        initiate main Qt building blocks of interface
        :param dock_widget: QDockWidget instance
        """

        dock_widget.setObjectName("dock_widget")
        dock_widget.setAttribute(Qt.WA_DeleteOnClose)

        self.dock_widget_content = QWidget(self)
        self.dock_widget_content.setObjectName("dockWidgetContent")

        self.main_vlayout = QVBoxLayout(self)
        self.dock_widget_content.setLayout(self.main_vlayout)

        # add button to add objects to graphs
        self.button_bar_hlayout = QHBoxLayout(self)
        self.select_polygon_button = QPushButton("Select Polygon", self)
        self.select_polygon_button.setCheckable(True)
        self.button_bar_hlayout.addWidget(self.select_polygon_button)
        self.chart_button = QPushButton(self)
        self.button_bar_hlayout.addWidget(self.chart_button)

        self.agg_combo_box = QComboBox(self)
        self.button_bar_hlayout.addWidget(self.agg_combo_box)
        self.ts_units_combo_box = QComboBox(self)
        self.button_bar_hlayout.addWidget(self.ts_units_combo_box)

        # now first add a QSpacerItem so that the QPushButton (added sub-
        # sequently) are aligned on the right-side of the button_bar_hlayout
        spacer_item = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.button_bar_hlayout.addItem(spacer_item)

        self.activate_all_button = QPushButton(self)
        self.button_bar_hlayout.addWidget(
            self.activate_all_button, alignment=Qt.AlignRight
        )

        self.deactivate_all_button = QPushButton(self)
        self.button_bar_hlayout.addWidget(
            self.deactivate_all_button, alignment=Qt.AlignRight
        )

        self.main_vlayout.addLayout(self.button_bar_hlayout)

        # add tabWidget for graphWidgets
        self.splitter = QSplitter(self)

        # tab widget for the plots
        self.tab_widget = QTabWidget(self.splitter)
        self.tab_widget.setMinimumSize(QSize(240, 250))

        self.splitter.addWidget(self.tab_widget)

        # table
        self.wb_item_table = WaterbalanceItemTable(self.splitter)
        self.wb_item_table.setMinimumSize(QSize(120, 0))
        self.splitter.addWidget(self.wb_item_table)

        self.splitter.setSizes([360, 120])
        self.splitter.setCollapsible(0, False)
        self.splitter.setStretchFactor(0, 8)
        self.splitter.setCollapsible(1, False)
        self.splitter.setStretchFactor(1, 1)

        self.main_vlayout.addWidget(self.splitter)

        # add dockwidget
        dock_widget.setWidget(self.dock_widget_content)
        self.chart_button.setText("Show total balance")
        self.activate_all_button.setText("activate all")
        self.deactivate_all_button.setText("deactivate all")
        QMetaObject.connectSlotsByName(dock_widget)

        # add selection maptool
        self.map_tool_select_polygon = SelectPolygonTool(
            widget=self, canvas=self.iface.mapCanvas(),
        )
        self.map_tool_select_polygon.setButton(self.select_polygon_button)
        self.map_tool_select_polygon.setCursor(Qt.CrossCursor)

    def add_result(self, result, update=True):
        if not self.manager.add_result(result):
            return
        plot_widget = WaterBalancePlotWidget(model=self.model, result=result)
        tab_label = self.manager[result].label
        self.tab_widget.addTab(plot_widget, tab_label)
        if update:
            self.update_water_balance(reset_model=True)

    def _get_tab_index(self, result):
        tab_widget = self.tab_widget
        for tab_index in range(tab_widget.count()):
            if tab_widget.widget(tab_index).result is result:
                return tab_index

    def remove_result(self, result):
        if not self.manager.remove_result(result):
            return
        tab_index = self._get_tab_index(result)
        update = tab_index == self.tab_widget.currentIndex()
        self.tab_widget.removeTab(tab_index)
        if update:
            self.update_water_balance(reset_model=True)

    def change_grid(self, grid):
        results = []
        grid.model().get_results_from_item(grid, False, results)
        for result in results:
            if result not in self.manager:
                return

            tab_index = self._get_tab_index(result)
            tab_label = self.manager[result].label
            self.tab_widget.setTabText(tab_index, tab_label)

    def change_result(self, result):
        if result not in self.manager:
            return
        tab_index = self._get_tab_index(result)
        tab_label = self.manager[result].label
        self.tab_widget.setTabText(tab_index, tab_label)

    def set_wb_polygon(self, polygon, layer):
        """ Highlight and set the current water balance polygon."""

        # highlight must be done before transform
        highlight = QgsHighlight(self.iface.mapCanvas(), polygon, layer)
        highlight.setColor(QColor(0, 0, 255, 127))
        # highlight.setWidth(3)

        self.wb_polygon_highlight = highlight
        self.manager.polygon = PolygonWithCRS(polygon=polygon, crs=layer.crs())
        progress_bar = StatusProgressBar(
            len(self.manager), "Calculating water balance",
        )
        for idx, result in enumerate(self.manager):
            self.add_result(result, update=False)
            progress_bar.increase_progress()

        self.update_water_balance(reset_model=True)

    def unset_wb_polygon(self):
        """ De-highlight and unset the current water balance polygon."""
        if self.manager.polygon is None:
            return
        self.iface.mapCanvas().scene().removeItem(self.wb_polygon_highlight)
        self.wb_polygon_highlight = None
        self.manager.polygon = None
        self.tab_widget.clear()
        self.model.removeRows(0, len(self.model.rows))


class SelectionVisualisation(object):
    """Visualize selected lines and points."""

    def __init__(self, canvas, color=QCOLOR_RED):
        self.canvas = canvas
        self.color = color
        self.vertex_markers = []
        self.lines = []
        self.points = []

    @functools.cached_property
    def rb_line(self):
        rb_line = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        rb_line.setColor(self.color)
        rb_line.setLineStyle(Qt.DotLine)
        rb_line.setWidth(3)
        return rb_line

    def show(self):
        # visualize lines
        multiline = QgsGeometry().fromMultiPolylineXY(self.lines)
        self.rb_line.setToGeometry(multiline, None)
        # visualize points
        for p in self.points:
            marker = QgsVertexMarker(self.canvas)
            marker.setCenter(p)
            marker.setIconType(QgsVertexMarker.ICON_BOX)
            marker.setColor(self.color)
            marker.setVisible(True)
            self.vertex_markers.append(marker)

    def reset(self):
        self.rb_line.reset(QgsWkbTypes.LineGeometry)
        for m in self.vertex_markers:
            m.setVisible(False)
            # rubber bands are owned by the canvas, so we must explictly
            # delete them
            self.canvas.scene().removeItem(m)
        self.vertex_markers = []
        self.lines = []
        self.points = []

    def update(self, lines, points):
        """lines and points are lists of QgsPoints and QgsPolylines."""
        self.reset()
        self.lines = lines
        self.points = points
        self.show()

    def close(self):
        self.reset()
        # delete the rubberband we've been re-using
        self.canvas.scene().removeItem(self.rb_line)


class SelectPolygonTool(QgsMapToolIdentify):
    def __init__(self, widget, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget = widget

        # select at most one feature
        self.identifyMenu().setAllowMultipleReturn(False)

    def canvasReleaseEvent(self, event):
        self.widget.unset_wb_polygon()
        layer_list = []
        for layer in self.parent().layers():
            if isinstance(layer, QgsVectorLayer):
                if layer.wkbType() in POLYGON_TYPES:
                    layer_list.append(layer)
        identify_results = self.identify(
            x=int(event.pos().x()),
            y=int(event.pos().y()),
            layerList=layer_list,
            mode=self.IdentifyMode.LayerSelection,
        )
        if not identify_results:
            msg = 'No polygons found in this location.'
            messagebar_message(MSG_TITLE, msg, Qgis.Warning, 3)
            return

        identify_result = identify_results[0]
        layer = identify_result.mLayer
        feature = identify_result.mFeature

        polygon = feature.geometry()
        if not polygon.wkbType() in POLYGON_TYPES:
            msg = 'Not a (suitable) polygon.'
            messagebar_message(MSG_TITLE, msg, Qgis.Warning, 3)
            return

        self.widget.set_wb_polygon(polygon=polygon, layer=layer)
