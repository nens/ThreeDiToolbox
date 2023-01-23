from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtCore import QObject
from ThreeDiToolbox.tool_graph.graph_view import GraphDockWidget
from ThreeDiToolbox.threedi_plugin_model import ThreeDiResultItem
from qgis.PyQt.QtCore import pyqtSlot
import qgis
import os


class ThreeDiGraph(QObject):

    def __init__(self, iface, model):
        QObject.__init__(self)

        self.iface = iface
        self.model = model

        self.icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "icon_graph.png")
        self.menu_text = "Show 3Di results in Graph"

        self.dock_widgets = []
        self.widget_nr = 0

    def on_unload(self):
        """
        on close of graph plugin
        """
        for widget in self.dock_widgets:
            widget.close()  # TODO: delete as well?

    def on_close_child_widget(self, widget_nr):
        """Cleanup necessary items here when plugin dockwidget is closed"""
        nr = None

        # find widget based on nr
        for i in range(0, len(self.dock_widgets)):
            widget = self.dock_widgets[i]
            if widget.nr == widget_nr:
                nr = i

        # close widget
        if nr is not None:
            widget = self.dock_widgets[nr]
            widget.closingWidget.disconnect(self.on_close_child_widget)

            del self.dock_widgets[nr]

    @pyqtSlot(ThreeDiResultItem)
    def result_added(self, result_item: ThreeDiResultItem):
        # Assign a line pattern to this result (TODO: consider keeping track of the patterns
        # in this plugin instead of storing in model?)
        result_item.pattern = ThreeDiGraph.get_line_pattern(result_item=result_item)

        self.action_icon.setEnabled(self.model.number_of_results() > 0)

    @pyqtSlot(ThreeDiResultItem)
    def result_removed(self, _: ThreeDiResultItem):
        self.action_icon.setEnabled(self.model.number_of_results() > 0)

    @pyqtSlot(ThreeDiResultItem)
    def result_activated(self, _: ThreeDiResultItem):
        for dock_widget in self.dock_widgets:
            dock_widget.on_result_selection_change()

    @pyqtSlot(ThreeDiResultItem)
    def result_deactivated(self, _: ThreeDiResultItem):
        for dock_widget in self.dock_widgets:
            dock_widget.on_result_selection_change()

    def run(self):
        """
        Run method that loads and starts the plugin (docked graph widget)
        """
        # create the dockwidget
        self.widget_nr += 1
        new_widget = GraphDockWidget(
            iface=self.iface,
            nr=self.widget_nr,
            model=self.model,
        )
        self.dock_widgets.append(new_widget)

        # connect cleanup on closing of dockwidget
        new_widget.closingWidget.connect(self.on_close_child_widget)

        # show the dockwidget
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, new_widget)

        # make stack of graph widgets (instead of next to each other)
        if len(self.dock_widgets) > 1:
            window = qgis.core.QgsApplication.activeWindow()
            window.tabifyDockWidget(self.dock_widgets[0], new_widget)

        new_widget.show()

    @staticmethod
    def get_line_pattern(result_item: ThreeDiResultItem) -> Qt.PenStyle:
        """Determine (default) line pattern for this result plot

        Look at the already-used styles os sibblings and try to pick an unused one.

        :param item_field:
        """
        available_styles = [
            Qt.SolidLine,
            Qt.DashLine,
            Qt.DotLine,
            Qt.DashDotLine,
            Qt.DashDotDotLine,
        ]

        already_used_patterns = []
        grid_item = result_item.parent()
        for i in range(grid_item.rowCount()):
            if grid_item.child(i) is not result_item:
                sibling_pattern = grid_item.child(i).pattern
                assert sibling_pattern
                already_used_patterns.append(sibling_pattern)

        for style in available_styles:
            if style not in already_used_patterns:
                # Hurray, an unused style.
                return style

        # No unused styles. Use the solid line style as a default.
        return Qt.SolidLine
