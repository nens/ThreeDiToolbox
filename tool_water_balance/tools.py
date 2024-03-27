from pathlib import Path
import logging

from qgis.PyQt.QtCore import Qt
from threedi_results_analysis.utils.user_messages import StatusProgressBar
from threedi_results_analysis.threedi_plugin_tool import ThreeDiPluginTool

from .calculation import WaterBalanceCalculation
from .utils import WrappedResult
from .views.widgets import WaterBalanceWidget

logger = logging.getLogger(__name__)


class WaterBalanceTool(ThreeDiPluginTool):
    """QGIS Plugin Implementation."""

    def __init__(self, iface, model):
        """Constructor.
        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        super().__init__()
        self.iface = iface
        self.icon_path = str(Path(__file__).parent.parent / 'icons' / 'weight-scale.png')
        self.menu_text = u"Water balance tool"

        self.is_active = False
        self.widget = None
        self.manager = WaterBalanceCalculationManager(model=model, iface=iface)

    def run(self):
        if self.is_active:
            return

        widget = WaterBalanceWidget(
            "3Di Water balance", manager=self.manager, iface=self.iface,
        )
        widget.closingWidget.connect(self.on_close_child_widget)
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, widget)
        widget.show()

        self.is_active = True
        self.widget = widget
        # TODO connect signals of results changes

    def on_unload(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""
        if self.widget is not None:
            self.widget.close()
        self.active = False

    def on_close_child_widget(self):
        """Cleanup necessary items here when plugin widget is closed"""
        self.widget.closingWidget.disconnect(self.on_close_child_widget)
        self.widget = None
        self.is_active = False
        # TODO disconnect signals of result changes

    def result_added(self, result):
        self.action_icon.setEnabled(self.manager.model.number_of_results() > 0)
        if self.is_active:
            progress_bar = StatusProgressBar(1, "Calculating water balance...")
            self.widget.add_result(result)
            progress_bar.increase_progress()

    def result_removed(self, result):
        if self.is_active:
            self.widget.remove_result(result)

    def result_changed(self, result):
        if self.is_active:
            self.widget.change_result(result)

    def grid_changed(self, grid):
        if self.is_active:
            self.widget.change_grid(grid)


class WaterBalanceCalculationManager:
    """
    Reset the cache
    """
    def __init__(self, model, iface):
        self.model = model
        self.iface = iface
        self._calculations = {}
        self._polygon = None

    def add_result(self, result):
        if self.polygon is None:
            return False

        wrapped_result = WrappedResult(result)
        if not wrapped_result.has_required_vars():
            return
        if not wrapped_result.has_synchronized_timestamps():
            return

        polygon = self.polygon.transformed(crs=wrapped_result.lines.crs())
        mapcrs = self.iface.mapCanvas().mapSettings().destinationCrs()
        calculation = WaterBalanceCalculation(
            result=result, polygon=polygon, mapcrs=mapcrs,
        )

        self._calculations[result.path] = calculation
        return True

    def remove_result(self, result):
        try:
            del self._calculations[result.path]
            return True
        except KeyError:
            return False

    @property
    def polygon(self):
        return self._polygon

    @polygon.setter
    def polygon(self, polygon):
        if polygon is None:
            self._polygon = None
            self._calculations = {}
            return

        self._polygon = polygon
        for result in self.model.get_results(checked_only=False):
            self.add_result(result)

    def __getitem__(self, result):
        return self._calculations[result.path]

    def __iter__(self):
        for calculation in self._calculations.values():
            yield calculation.result

    def __bool__(self):
        return bool(self._calculations)

    def __contains__(self, result):
        return result.path in self._calculations

    def __len__(self):
        return len(self._calculations)
