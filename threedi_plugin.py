from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtXml import QDomDocument, QDomElement
from qgis.utils import iface
from qgis.core import QgsApplication, QgsProject, QgsPathResolver, QgsSettings, QgsMapLayer
from threedi_results_analysis.misc_tools import About
from threedi_results_analysis.misc_tools import ShowLogfile
from threedi_results_analysis.misc_tools import ToggleResultsManager
from threedi_results_analysis.processing.providers import ThreediProvider
from threedi_results_analysis.gui.threedi_plugin_dockwidget import ThreeDiPluginDockWidget
from threedi_results_analysis.threedi_plugin_layer_manager import ThreeDiPluginLayerManager
from threedi_results_analysis.threedi_plugin_model import ThreeDiPluginModel
from threedi_results_analysis.threedi_plugin_model_validation import ThreeDiPluginModelValidator
from threedi_results_analysis.temporal import TemporalManager
from threedi_results_analysis.threedi_plugin_model_serialization import ThreeDiPluginModelSerializer
from threedi_results_analysis.tool_animation.map_animator import MapAnimator
from threedi_results_analysis.tool_graph.graph import ThreeDiGraph
from threedi_results_analysis.tool_sideview.sideview import ThreeDiSideView
from threedi_results_analysis.tool_statistics.statistics import StatisticsTool
from threedi_results_analysis.tool_water_balance import WaterBalanceTool
from threedi_results_analysis.tool_watershed.watershed_analysis import ThreeDiWatershedAnalyst
from threedi_results_analysis.utils import color
from threedi_results_analysis.utils.qprojects import ProjectStateMixin

import logging

logger = logging.getLogger(__name__)


class ThreeDiPlugin(QObject, ProjectStateMixin):
    """Main Plugin Class which register toolbar ad menu and add tools"""

    def __init__(self, iface):
        QObject.__init__(self)

        # Save reference to the QGIS interface
        self.iface = iface

        self.provider = None

    def initProcessing(self):
        """Create the Qgis Processing Toolbox provider and its algorithms

        Called by QGIS to check for processing algorithms.
        """
        self.provider = ThreediProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI.

        Called when the plugin is loaded.
        """
        self.model = ThreeDiPluginModel()
        self.loader = ThreeDiPluginLayerManager()
        self.validator = ThreeDiPluginModelValidator(self.model)

        QgsProject.instance().writeProject.connect(self.write)
        QgsProject.instance().writeMapLayer.connect(self.write_map_layer)  # Called after write()
        QgsProject.instance().readProject.connect(self.read)
        QgsProject.instance().removeAll.connect(self.model.clear)

        # Declare instance attributes
        self.actions = []
        self.menu = "&3Di Results Analysis"

        # Set toolbar and init a few toolbar widgets
        self.toolbar = self.iface.addToolBar("ThreeDiResultAnalysis")
        self.toolbar.setObjectName("ThreeDiResultAnalysisToolBar")

        # Init the rest of the tools
        self.about_tool = About(iface)
        self.toggle_results_manager = ToggleResultsManager(iface)
        self.graph_tool = ThreeDiGraph(iface, self.model)
        self.sideview_tool = ThreeDiSideView(iface, self.model)
        self.stats_tool = StatisticsTool(iface, self.model)
        self.water_balance_tool = WaterBalanceTool(iface, self.model)
        self.watershed_tool = ThreeDiWatershedAnalyst(iface, self.model)
        self.logfile_tool = ShowLogfile(iface)
        self.temporal_manager = TemporalManager(self.model)

        self.tools = [  # second item indicates enabled on startup
            (self.about_tool, True),
            (self.toggle_results_manager, True),
            (self.graph_tool, False),
            (self.sideview_tool, False),
            (self.stats_tool, False),
            (self.water_balance_tool, False),
            (self.watershed_tool, False),
            (self.logfile_tool, True),
        ]

        # Styling (TODO: can this be moved to where it is used?)
        for color_ramp in color.COLOR_RAMPS:
            color.add_color_ramp(color_ramp)

        for tool, enabled in self.tools:
            self._add_action(
                tool,
                tool.icon_path,
                text=tool.menu_text,
                callback=tool.run,
                parent=self.iface.mainWindow(),
                enabled_flag=enabled
            )

        assert not hasattr(self, "dockwidget")  # Should be destroyed on unload
        self.dockwidget = ThreeDiPluginDockWidget(None, iface)

        # Connect the signals

        # Addition signals
        self.dockwidget.grid_file_selected.connect(self.validator.validate_grid)
        self.dockwidget.result_grid_file_selected.connect(self.validator.validate_result_grid)
        self.validator.result_valid.connect(self.loader.load_result)
        self.validator.grid_valid.connect(self.loader.load_grid)
        self.loader.grid_loaded.connect(self.model.add_grid)
        self.loader.result_loaded.connect(self.model.add_result)

        self.model.grid_added.connect(self.dockwidget.expand_grid)

        # Removal signals
        # (note that model.remove_grid -> loader.unload_grid is connected
        # later so that tools get the signals first)
        self.dockwidget.result_removal_selected.connect(self.model.remove_result)
        self.dockwidget.grid_removal_selected.connect(self.model.remove_grid)

        # Modification signals
        self.model.grid_changed.connect(self.loader.update_grid)
        self.model.result_changed.connect(self.loader.update_result)
        self.model.result_unchecked.connect(self.loader.result_unchecked)

        self.toggle_results_manager.triggered.connect(self.dockwidget.toggle_visible)

        self.dockwidget.set_model(self.model)

        self.initProcessing()

        # temporal manager signals
        self.model.result_added.connect(self.temporal_manager.configure)
        self.model.result_removed.connect(self.temporal_manager.configure)
        self.dockwidget.align_starts_checked.connect(self.temporal_manager.set_align_starts)

        # animation signals
        self.map_animator = MapAnimator(self.dockwidget.get_tools_widget(), self.model)
        self.model.result_checked.connect(self.map_animator.results_changed)
        self.model.result_unchecked.connect(self.map_animator.results_changed)
        self.model.result_added.connect(self.map_animator.results_changed)
        self.temporal_manager.updated.connect(self.map_animator.update_results)

        # graph signals
        self.model.result_added.connect(self.graph_tool.result_added)
        self.model.result_removed.connect(self.graph_tool.result_removed)
        self.model.result_changed.connect(self.graph_tool.result_changed)
        self.model.grid_changed.connect(self.graph_tool.grid_changed)

        # sideview signals
        self.model.grid_added.connect(self.sideview_tool.grid_added)
        self.model.grid_removed.connect(self.sideview_tool.grid_removed)
        self.model.grid_changed.connect(self.sideview_tool.grid_changed)
        self.model.result_added.connect(self.sideview_tool.result_added)
        self.model.result_removed.connect(self.sideview_tool.result_removed)
        self.model.result_changed.connect(self.sideview_tool.result_changed)
        self.temporal_manager.updated.connect(self.sideview_tool.update_waterlevels)

        # watershed signals
        self.model.result_added.connect(self.watershed_tool.result_added)
        self.model.result_removed.connect(self.watershed_tool.result_removed)
        self.model.result_changed.connect(self.watershed_tool.result_changed)
        self.model.grid_changed.connect(self.watershed_tool.grid_changed)
        self.watershed_tool.closing.connect(self.loader.reset_styling)

        # statistics signals
        self.model.result_added.connect(self.stats_tool.result_added)
        self.model.result_removed.connect(self.stats_tool.result_removed)
        self.model.result_changed.connect(self.stats_tool.result_changed)
        self.model.grid_changed.connect(self.stats_tool.grid_changed)

        # water balance signals
        self.model.result_added.connect(self.water_balance_tool.result_added)
        self.model.result_removed.connect(self.water_balance_tool.result_removed)
        self.model.result_changed.connect(self.water_balance_tool.result_changed)
        self.model.grid_changed.connect(self.water_balance_tool.grid_changed)

        # Further administrative signals that need to happens last:
        # https://doc.qt.io/qt-5/signalsandslots.html#signals
        # If several slots are connected to one signal, the slots will be executed one after the other,
        # in the order they have been connected, when the signal is emitted.

        self.model.grid_removed.connect(self.loader.unload_grid)
        self.model.result_removed.connect(self.loader.unload_result)

        self.init_state_sync()

        # Disable warning that scratch layer data will be lost
        QgsSettings().setValue("askToSaveMemoryLayers", False, QgsSettings.App)

    def write(self, doc: QDomDocument) -> bool:
        # Resolver convert relative to absolute paths and vice versa
        resolver = QgsPathResolver(QgsProject.instance().fileName() if (QgsProject.instance().filePathStorage() == 1) else "")
        res, node = ThreeDiPluginModelSerializer.write(self.model, doc, resolver)
        if not res:
            logger.error("Unable to write model to QGIS project file.")
            return False

        # Allow each tool to save additional info to the xml node
        for tool, _ in self.tools:
            if not tool.write(doc, node):
                return False

        return True

    def write_map_layer(self, layer: QgsMapLayer, elem: QDomElement, _: QDomDocument):
        # Ensure all our dynamically added attributes are not serialized
        result_field_names = self.model.get_result_field_names(layer.id())
        ThreeDiPluginModelSerializer.remove_result_field_references(
            elem, result_field_names,
        )

    def read(self, doc: QDomDocument) -> bool:
        self.model.clear()
        self.dockwidget.set_model(self.model)

        # Resolver convert relative to absolute paths and vice versa
        resolver = QgsPathResolver(QgsProject.instance().fileName() if (QgsProject.instance().filePathStorage() == 1) else "")
        res, tool_node = ThreeDiPluginModelSerializer.read(self.loader, doc, resolver)
        if not res:
            self.model.clear()
            return False

        # Allow each tool to read additional info from the dedicated xml node
        for tool, _ in self.tools:
            if not tool.read(tool_node):
                self.model.clear()
                return False

        return True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI.

        Called then the plugin is unloaded.
        """

        # Stop animating
        self.temporal_manager.updated.disconnect(self.map_animator.update_results)

        # Clears model and emits subsequent signals
        self.model.clear()

        self.unload_state_sync()
        QgsApplication.processingRegistry().removeProvider(self.provider)

        for action in self.actions:
            self.iface.removePluginMenu("&3Di Results Analysis", action)
            self.iface.removeToolBarIcon(action)

        for tool, _ in self.tools:
            tool.on_unload()

        self.iface.removeDockWidget(self.dockwidget)
        del self.dockwidget
        del self.toolbar

    def _add_action(
        self,
        tool_instance,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        """Add a toolbar icon to the toolbar."""

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        setattr(tool_instance, "action_icon", action)
        self.actions.append(action)
        return action
