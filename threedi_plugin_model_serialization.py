from qgis.PyQt.QtXml import QDomDocument, QDomElement
from threedi_results_analysis.utils.constants import TOOLBOX_XML_ELEMENT_ROOT
from threedi_results_analysis.threedi_plugin_model import ThreeDiPluginModel
from threedi_results_analysis.threedi_plugin_layer_manager import ThreeDiPluginLayerManager
from qgis.PyQt.QtGui import QStandardItem
from threedi_results_analysis.threedi_plugin_model import ThreeDiGridItem, ThreeDiResultItem, already_used_ids
from typing import Tuple
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)


class ThreeDiPluginModelSerializer:

    @staticmethod
    def read(loader: ThreeDiPluginLayerManager, doc: QDomDocument, resolver) -> bool:
        """Reads the model from the provided XML DomDocument

        Recursively traverses down the XML tree. Resolver is used to convert between relative
        and absolute paths.

        Returns True on success and the dedicated QDomElement that
        the tools can use read persistent data from (can be None).
        """

        # Find existing element corresponding to the result model
        results_nodes = doc.elementsByTagName(TOOLBOX_XML_ELEMENT_ROOT)

        if results_nodes.length() > 1:
            logger.error("XML file contains multiple toolbox root elements, aborting load.")
            return False, None
        elif results_nodes.length() == 0:
            return True, None  # Nothing to load

        results_node = results_nodes.at(0)
        assert results_node.parentNode() is not None

        # Now traverse through the XML tree and add model items
        if not ThreeDiPluginModelSerializer._read_recursive(loader, results_node, None, resolver):
            logger.error("Unable to read XML, aborting read")
            return False, None

        # Retrieve dedicated XML node for tools
        tools_node = results_node.firstChildElement("tools")
        if not tools_node:
            logger.error("Unable to read XML (no dedicated tool node), aborting read")
            return False, None

        return True, tools_node

    @staticmethod
    def _read_recursive(loader: ThreeDiPluginLayerManager, xml_parent: QDomElement, model_parent: QStandardItem, resolver) -> bool:

        if not xml_parent.hasChildNodes():
            return True

        child_xml_nodes = xml_parent.childNodes()

        for i in range(child_xml_nodes.count()):
            xml_node = child_xml_nodes.at(i)

            if xml_node.isElement():
                xml_element_node = xml_node.toElement()
                tag_name = xml_element_node.tagName()
                model_node = None
                if tag_name == "grid":

                    id = xml_element_node.attribute("id")
                    already_used_ids.append(id)

                    model_node = ThreeDiGridItem(Path(resolver.readPath(xml_element_node.attribute("path"))), xml_element_node.attribute("text"), id)
                    assert xml_node.hasChildNodes()
                    layer_nodes = xml_element_node.elementsByTagName("layer")
                    for i in range(layer_nodes.count()):
                        label_node = layer_nodes.at(i).toElement()
                        model_node.layer_ids[label_node.attribute("table_name")] = label_node.attribute("id")

                    if not loader.load_grid(model_node):
                        return False

                elif tag_name == "result":

                    id = xml_element_node.attribute("id")
                    already_used_ids.append(id)

                    model_node = ThreeDiResultItem(Path(resolver.readPath(xml_element_node.attribute("path"))), id)
                    model_node.setCheckState(int(xml_element_node.attribute("check_state")))
                    model_node.setText(xml_element_node.attribute("text"))

                    assert isinstance(model_parent, ThreeDiGridItem)
                    if not loader.load_result(model_node, model_parent):
                        return False

                elif tag_name == "layer":  # Subelement of grid
                    continue  # Leaf of XML tree, no processing
                elif tag_name == "tools":  # Node dedicated for tools
                    continue
                else:
                    logger.error("Unexpected XML item type, aborting read")
                    return False

                if not ThreeDiPluginModelSerializer._read_recursive(loader, xml_node, model_node, resolver):
                    return False
            else:
                return False

        return True

    @staticmethod
    def write(model: ThreeDiPluginModel, doc: QDomDocument, resolver) -> Tuple[bool, QDomElement]:
        """Add the model to the provided XML DomDocument

        Recursively traverses down the model tree. QGIS' resolver is used to convert
        between relative and absolute paths.

        Returns True on success and the newly created dedicated QDomElement that
        the tools can use to persist data.
        """
        # Find and remove the existing element corresponding to the result model
        results_nodes = doc.elementsByTagName(TOOLBOX_XML_ELEMENT_ROOT)
        if results_nodes.length() == 1:
            results_node = results_nodes.at(0)
            assert results_node.parentNode() is not None
            results_node.parentNode().removeChild(results_node)

        # Create new results node under main (qgis) node
        qgis_nodes = doc.elementsByTagName("qgis")
        assert qgis_nodes.length() == 1 and qgis_nodes.at(0) is not None
        qgis_node = qgis_nodes.at(0)
        results_node = doc.createElement(TOOLBOX_XML_ELEMENT_ROOT)
        results_node = qgis_node.appendChild(results_node)
        assert results_node is not None

        # Traverse through the model and save the nodes
        if not ThreeDiPluginModelSerializer._write_recursive(doc, results_node, model.invisibleRootItem(), resolver):
            logger.error("Unable to write model")
            return False, None

        # Add a dedicated node for the tools to persist information
        tool_node = doc.createElement("tools")
        tool_node = results_node.appendChild(tool_node)

        return True, tool_node

    @staticmethod
    def _write_recursive(doc: QDomDocument, xml_parent: QDomElement, model_parent: QStandardItem, resolver) -> bool:
        # Something is wrong when exactly one of them is None
        assert not (bool(xml_parent is not None) ^ bool(model_parent is not None))

        # Iterate over model child nodes and continue recursive traversion
        if model_parent.hasChildren():
            for i in range(model_parent.rowCount()):
                model_node = model_parent.child(i)
                xml_node = doc.createElement("temp")  # tag required

                # Populate the new xml_node with the info from model_node
                if isinstance(model_node, ThreeDiGridItem):
                    xml_node.setTagName("grid")
                    xml_node.setAttribute("path", resolver.writePath(str(model_node.path)))
                    xml_node.setAttribute("text", model_node.text())
                    xml_node.setAttribute("id", model_node.id)

                    # Write corresponding layer id's
                    for table_name, layer_id in model_node.layer_ids.items():
                        layer_element = doc.createElement("layer")
                        layer_element.setAttribute("id", layer_id)
                        layer_element.setAttribute("table_name", table_name)
                        xml_node.appendChild(layer_element)

                elif isinstance(model_node, ThreeDiResultItem):
                    xml_node.setTagName("result")
                    xml_node.setAttribute("path", resolver.writePath(str(model_node.path)))
                    xml_node.setAttribute("text", model_node.text())
                    xml_node.setAttribute("id", model_node.id)
                    xml_node.setAttribute("check_state", str(model_node.checkState()))
                else:
                    logger.error("Unknown node type for serialization")
                    return False

                xml_node = xml_parent.appendChild(xml_node)
                assert xml_node is not None

                if not ThreeDiPluginModelSerializer._write_recursive(doc, xml_node, model_node, resolver):
                    return False

        return True

    @staticmethod
    def remove_result_field_references(elem, field_names):
        """
        Remove references to result fields from the map layer element.

        They cannot be reused because new result ids will be generated when
        the project is reloaded and the result model is repopulated.
        """
        # modify datasource
        datasource = elem.firstChildElement('datasource').text()
        for field_name in field_names:
            datasource = re.sub(
                pattern=r'&field=' + field_name + r'[^&]*',
                repl='',
                string=datasource,
            )
        elem.firstChildElement('datasource').firstChild().setNodeValue(datasource)

        # remove elements
        elements_to_be_removed = (
            ('fieldConfiguration', 'name'),
            ('aliases', 'field'),
            ('defaults', 'field'),
            ('constraints', 'field'),
            ('constraintExpressions', 'field'),
        )
        for tag, attr in elements_to_be_removed:
            parent = elem.firstChildElement(tag)
            children = parent.childNodes()
            for child in [children.item(i) for i in range(children.count())]:
                if child.toElement().attribute(attr) in field_names:
                    parent.removeChild(child)
