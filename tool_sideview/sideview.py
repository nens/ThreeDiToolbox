from qgis.PyQt.QtCore import Qt, pyqtSlot
from threedi_results_analysis.tool_sideview.sideview_view import SideViewDockWidget
from threedi_results_analysis.threedi_plugin_model import ThreeDiGridItem, ThreeDiResultItem
from threedi_results_analysis.threedi_plugin_tool import ThreeDiPluginTool
import qgis
import os


class ThreeDiSideView(ThreeDiPluginTool):

    def __init__(self, iface, model):
        super().__init__()

        self.iface = iface
        self.model = model
        self.icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "icon_route.png")
        self.menu_text = u"Side view tool"
        self.dock_widgets = []
        self.widget_nr = 0

    def on_unload(self):
        """
        on close of sideview plugin
        """
        for widget in self.dock_widgets:
            widget.close()

    @pyqtSlot(ThreeDiGridItem)
    def result_added(self, item: ThreeDiResultItem):
        for dock_widget in self.dock_widgets:
            dock_widget.result_added(item)

    @pyqtSlot(ThreeDiGridItem)
    def result_removed(self, item: ThreeDiResultItem):
        for dock_widget in self.dock_widgets:
            dock_widget.result_removed(item)

    @pyqtSlot(ThreeDiGridItem)
    def result_changed(self, item: ThreeDiResultItem):
        for dock_widget in self.dock_widgets:
            dock_widget.result_changed(item)

    @pyqtSlot(ThreeDiGridItem)
    def grid_added(self, item: ThreeDiGridItem):
        for dock_widget in self.dock_widgets:
            dock_widget.grid_added(item)
        self.action_icon.setEnabled(self.model.number_of_grids() > 0)

    @pyqtSlot(ThreeDiGridItem)
    def grid_removed(self, item: ThreeDiGridItem):
        for dock_widget in self.dock_widgets:
            dock_widget.grid_removed(item)

    @pyqtSlot(ThreeDiGridItem)
    def grid_changed(self, item: ThreeDiGridItem):
        for dock_widget in self.dock_widgets:
            dock_widget.grid_changed(item)

    @pyqtSlot()
    def update_waterlevels(self):
        for dock_widget in self.dock_widgets:
            dock_widget.update_waterlevel()

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

    def run(self):

        self.widget_nr += 1
        new_widget = SideViewDockWidget(
            self.iface,
            nr=self.widget_nr,
            model=self.model
        )
        self.dock_widgets.append(new_widget)

        # connect cleanup on closing of dockwidget
        new_widget.closingWidget.connect(self.on_close_child_widget)

        # show the dockwidget
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, new_widget)

        # make stack of dock widgets (instead of next to each other)
        if len(self.dock_widgets) > 1:
            window = qgis.core.QgsApplication.activeWindow()
            window.tabifyDockWidget(self.dock_widgets[0], new_widget)

        new_widget.show()

        # When loading the first dockwidget, automatically activate first grid
        if self.widget_nr == 1:  # just added the first
            if self.model.get_grids():
                new_widget.grid_selected(0)
