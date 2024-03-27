# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtCore import Qt
from .watershed_analysis_dockwidget import WatershedAnalystDockWidget, GROUP_NAME
from threedi_results_analysis.threedi_plugin_tool import ThreeDiPluginTool
from threedi_results_analysis.threedi_plugin_model import ThreeDiResultItem, ThreeDiGridItem
from qgis.PyQt.QtXml import QDomElement, QDomDocument
from qgis.PyQt.QtCore import pyqtSlot, pyqtSignal
from threedi_results_analysis.utils.qprojects import set_read_only
from qgis.core import QgsProject
import logging

logger = logging.getLogger(__name__)

required_layer_names = ["cell", "flowline", "catchment"]
optional_layer_names = ["surface"]
all_possible_layer_names = required_layer_names + optional_layer_names


class ThreeDiWatershedAnalyst(ThreeDiPluginTool):
    closing = pyqtSignal(ThreeDiGridItem)

    def __init__(self, iface, model):
        super().__init__()
        self.iface = iface
        self.model = model

        self.icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "icon_watershed.png")
        self.menu_text = "Watershed tool"

        self.dock_widget = None
        self._active = False

        # Cache Layer (ids) and group (reference) per result (id)
        self.preloaded_layers = {}

    def read(self, xml_elem: QDomElement) -> bool:
        self.preloaded_layers.clear()

        watershed_node = xml_elem.firstChildElement("water_shed")
        if not watershed_node:
            logger.error("Unable to read XML (no dedicated watershed node)")
            return False

        result_nodes = watershed_node.elementsByTagName("result")
        for i in range(result_nodes.count()):
            result_node = result_nodes.item(i).toElement()
            result_id = result_node.attribute("id")
            self.preloaded_layers[result_id] = {}

            layer_nodes = result_node.elementsByTagName("layer")
            for i in range(layer_nodes.count()):
                layer_node = layer_nodes.item(i).toElement()
                layer_id = layer_node.attribute("id")
                layer_table_name = layer_node.attribute("table_name")
                if layer_table_name not in all_possible_layer_names:
                    continue
                self.preloaded_layers[result_id][layer_table_name] = layer_id

            # See if we can find a possible group
            result = self.model.get_result(result_id)
            grid_item = result.parent()
            assert grid_item
            tool_group = grid_item.layer_group.findGroup(GROUP_NAME)
            if tool_group:
                result_group = tool_group.findGroup(result.text())
                if result_group:
                    self.preloaded_layers[result_id]["group"] = result_group
                    result_group.nameChanged.connect(lambda _, txt, result_item=result: result_item.setText(txt))

        # When the layers have been loaded, you want them to be removable until we
        # open the tool.
        self.release_layers()
        return True

    def write(self, doc: QDomDocument, xml_elem: QDomElement) -> bool:
        watershed_node = doc.createElement("water_shed")
        xml_elem.appendChild(watershed_node)

        for result_id, layer_dict in self.preloaded_layers.items():
            result_element = doc.createElement("result")
            result_element.setAttribute("id", result_id)
            result_element = watershed_node.appendChild(result_element)

            # We only write out relevant items of the dictionary
            for table_name, id in layer_dict.items():
                if table_name not in all_possible_layer_names:
                    continue
                layer_element = doc.createElement("layer")
                layer_element.setAttribute("table_name", table_name)
                layer_element.setAttribute("id", id)
                layer_element = result_element.appendChild(layer_element)

        return True

    @property
    def active(self):
        return self._active

    def on_unload(self):
        if self.dock_widget is not None:
            self.dock_widget.close()

        self.release_layers()

    def on_close_child_widget(self, last_grid_item: ThreeDiGridItem):
        """Cleanup necessary items here when plugin dock widget is closed"""
        self.dock_widget.closingWidget.disconnect(self.on_close_child_widget)
        if last_grid_item:
            self.closing.emit(last_grid_item)
        self.dock_widget = None
        self._active = False
        self.release_layers()

    def release_layers(self) -> None:
        """Remove the read-only / non-removable flag from all generated layers"""
        for _, loaded_layer_dict in self.preloaded_layers.items():
            for layer_name in all_possible_layer_names:
                if layer_name in optional_layer_names:
                    if layer_name not in loaded_layer_dict:
                        continue
                layer = QgsProject.instance().mapLayer(loaded_layer_dict[layer_name])
                if layer is not None:
                    set_read_only(layer, False)

    def update_preloaded_layers(self) -> None:
        """Check the list of preloaded layers, in case one if removed, it will be removed from cache"""
        for result_id, loaded_layer_dict in self.preloaded_layers.items():
            for layer_name in all_possible_layer_names:
                if layer_name in optional_layer_names:
                    if layer_name not in loaded_layer_dict:
                        continue
                layer = QgsProject.instance().mapLayer(loaded_layer_dict[layer_name])
                if not layer:
                    logger.info(f"Watershed: {layer_name} layer already removed, removed from cache.")
                    del loaded_layer_dict[layer_name]

            # Check whether the results group already exist for this result, if so, add to cache
            result = self.model.get_result(result_id)
            tool_group = result.parent().layer_group.findGroup(GROUP_NAME)
            if tool_group:
                result_group = tool_group.findGroup(result.text())
                if result_group:
                    loaded_layer_dict["group"] = result_group
                    result_group.nameChanged.connect(lambda _, txt, result_item=result: result_item.setText(txt))

    def run(self):
        """Run method that loads and starts the tool"""
        self.update_preloaded_layers()
        if not self.active:
            if self.dock_widget is None:
                self.dock_widget = WatershedAnalystDockWidget(self.iface, self.model, self.preloaded_layers)

            self.dock_widget.closingWidget.connect(self.on_close_child_widget)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)

        self.dock_widget.show()
        self._active = True

    @pyqtSlot(ThreeDiResultItem)
    def result_added(self, result_item: ThreeDiResultItem) -> None:
        self.action_icon.setEnabled(self.model.number_of_results() > 0)
        if not self.active:
            return

        self.dock_widget.add_result(result_item)

    @pyqtSlot(ThreeDiResultItem)
    def result_removed(self, result_item: ThreeDiResultItem) -> None:
        self.action_icon.setEnabled(self.model.number_of_results() > 0)
        if not self.active:
            return

        # Remove from combobox etc
        self.dock_widget.remove_result(result_item)

        # Removed cached layers and groups
        if result_item.id in self.preloaded_layers:
            layer_dict = self.preloaded_layers[result_item.id]
            for table_name in required_layer_names:
                QgsProject.instance().removeMapLayer(layer_dict[table_name])
            for table_name in optional_layer_names:
                if table_name in layer_dict:
                    QgsProject.instance().removeMapLayer(layer_dict[table_name])

            # Remove group
            if "group" in layer_dict:
                result_group = layer_dict["group"]
                tool_group = result_group.parent()
                tool_group.removeChildNode(result_group)

            # In case the tool ("watershed") group is now empty, we'll remove that too
            tool_group = result_item.parent().layer_group.findGroup(GROUP_NAME)
            if len(tool_group.children()) == 0:
                tool_group.parent().removeChildNode(tool_group)

            # Remove from dict
            del self.preloaded_layers[result_item.id]

    @pyqtSlot(ThreeDiResultItem)
    def result_changed(self, result_item: ThreeDiResultItem) -> None:
        # also rename result layer groups
        if result_item.id in self.preloaded_layers:
            # Could be that the group is deleted
            if "group" in self.preloaded_layers[result_item.id]:
                layer_result_group = self.preloaded_layers[result_item.id]["group"]
                layer_result_group.setName(result_item.text())

        if not self.active:
            return

        self.dock_widget.change_result(result_item)

    @pyqtSlot(ThreeDiResultItem)
    def grid_changed(self, grid_item: ThreeDiGridItem) -> None:
        if not self.active:
            return

        results = []
        self.model.get_results_from_item(grid_item, False, results)
        for result in results:
            self.dock_widget.change_result(result)
