from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from ThreeDiToolbox import resources
from ThreeDiToolbox.misc_tools import About
from ThreeDiToolbox.tool_result_selection.result_selection import ThreeDiResultSelection
from ThreeDiToolbox.utils import color
from ThreeDiToolbox.utils import styler
from ThreeDiToolbox.utils.layer_tree_manager import LayerTreeManager
import logging


logger = logging.getLogger(__name__)

# Pycharm's refactor option "move" automatically deletes unused import statements,
# If "from ThreeDiToolbox import resources" is deleted then tool-icons wont show up.
# Lets call it.
resources  # noqa


class ThreeDiPlugin(QObject):

    def __init__(self, iface):

        QObject.__init__(self)
        self.iface = iface

        self.actions = []
        self.menu = "&3Di toolbox"

        self.toolbar = self.iface.addToolBar("ThreeDiToolbox")
        self.layer_manager = LayerTreeManager(self.iface)

        self.about_tool = About(iface)
        self.result_selection_tool = ThreeDiResultSelection(iface, self.layer_manager)

        self.tools = [
            self.about_tool,
            self.result_selection_tool,
        ]

        # Styling
        for color_ramp in color.COLOR_RAMPS:
            styler.add_color_ramp(color_ramp)

    def add_action(
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

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        for tool in self.tools:
            self.add_action(
                tool,
                tool.icon_path,
                text=tool.menu_text,
                callback=tool.run,
                parent=self.iface.mainWindow(),
            )

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        for action in self.actions:
            self.iface.removePluginMenu("&3Di toolbox", action)
            self.iface.removeToolBarIcon(action)

            for tool in self.tools:
                tool.on_unload()

        self.layer_manager.on_unload()

        try:
            del self.toolbar
        except AttributeError:
            logger.exception("Error, toolbar already removed? Continuing anyway.")
