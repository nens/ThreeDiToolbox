from pathlib import Path
from qgis.core import QgsVectorLayer, QgsFeature
from qgis.core import QgsGeometry, QgsPointXY, QgsField
from threedigrid.admin.gridadmin import GridH5Admin
from threedi_results_analysis.tool_sideview.utils import LineType
from threedi_results_analysis.tool_sideview.cross_section_utils import CrossSectionShape
from threedi_results_analysis.utils.user_messages import StatusProgressBar
from qgis.PyQt.QtCore import QVariant
import math
import logging
import numpy as np
logger = logging.getLogger(__name__)


class SideViewGraphGenerator():
    """Generates a profile graph based on a gridadmin file"""

    @staticmethod
    def generate_layer(gridadmin_file: Path, progress_bar: StatusProgressBar) -> QgsVectorLayer:

        ga = GridH5Admin(gridadmin_file.with_suffix('.h5'))

        graph_layer = QgsVectorLayer(f"LineString?crs=EPSG:{ga.epsg_code}&index=yes", "graph_layer", "memory")
        pr = graph_layer.dataProvider()

        pr.addAttributes([QgsField("id", QVariant.Int),
                          QgsField("start_node_id", QVariant.Int),
                          QgsField("end_node_id", QVariant.Int),
                          QgsField("real_length", QVariant.Double),
                          QgsField("type", QVariant.Int),
                          QgsField("start_level", QVariant.Double),
                          QgsField("end_level", QVariant.Double),
                          QgsField("start_height", QVariant.Double),
                          QgsField("end_height", QVariant.Double),
                          QgsField("crest_level", QVariant.Double)
                          ])

        # Tell the vector layer to fetch changes from the provider
        graph_layer.updateFields()

        # Retrieve 1D lines from gridadmin
        lines_1d_data = ga.lines.subset("1D").only("ds1d", "line_coords", "id", "content_pk", "line", "content_type", "invert_level_start_point", "invert_level_end_point", "cross1", "cross2").data
        lines_1d_data = {k: v.tolist() for (k, v) in lines_1d_data.items()}  # convert to native python items

        lines_1d2d_data = ga.lines.subset("1D2D").only("dpumax", "line").data
        lines_1d2d_data = {k: v.tolist() for (k, v) in lines_1d2d_data.items()}

        # As we already subset the list, we do not need to skip the first nan-element
        last_index = 0
        number_of_lines = len(lines_1d_data["line_coords"][0])
        for count in range(number_of_lines):  # line_coords is transposed
            feat = QgsFeature()

            p1 = QgsPointXY(lines_1d_data["line_coords"][0][count], lines_1d_data["line_coords"][1][count])
            p2 = QgsPointXY(lines_1d_data["line_coords"][2][count], lines_1d_data["line_coords"][3][count])
            geom = QgsGeometry.fromPolylineXY([p1, p2])
            feat.setGeometry(geom)

            start_level = None
            end_level = None
            start_height = None
            end_height = None

            line_type = SideViewGraphGenerator.content_type_to_line_type(lines_1d_data["content_type"][count].decode())

            node_id_1 = lines_1d_data["line"][0][count]
            node_id_2 = lines_1d_data["line"][1][count]

            if line_type == LineType.PIPE or line_type == LineType.CULVERT or line_type == LineType.ORIFICE or line_type == LineType.WEIR:
                cross1_id = lines_1d_data["cross1"][count]
                cross2_id = lines_1d_data["cross2"][count]
                assert cross1_id == cross2_id  # pipes and culverts have only one cross section definition
                cross_section = ga.cross_sections.filter(id=cross1_id)

                try:
                    height = SideViewGraphGenerator.cross_section_max_height(cross_section, ga.cross_sections.tables)
                except AttributeError:
                    raise AttributeError(f"Unable to derive height of cross section: {cross_section.id[0]} {cross1_id} {cross1_id} with shape {cross_section.shape[0]} for line {lines_1d_data['id'][count]}, count {count}, pk: {lines_1d_data['content_pk'][count]}, type: {line_type}, start_level {start_level}, end_level {end_level}, cs_pk {cross_section.content_pk[0]}, width_1d {cross_section.width_1d[0]}")

                if math.isnan(height):  # Not an error, simply not enough information
                    logger.warning(f"Unable to derive cross section height for cross section {cross1_id} with shape {cross_section.shape[0]} for line {lines_1d_data['id'][count]}, count {count}, pk: {lines_1d_data['content_pk'][count]}, type: {line_type}, setting height to 0.")
                    height = 0.0
                start_height = height
                end_height = height
                crest_level = None

                if line_type == LineType.PIPE or line_type == LineType.CULVERT:
                    start_level = lines_1d_data["invert_level_start_point"][count]
                    end_level = lines_1d_data["invert_level_end_point"][count]
                elif line_type == LineType.ORIFICE or line_type == LineType.WEIR:
                    # for bottom level, take dmax of adjacent nodes
                    node_1 = ga.nodes.filter(id=node_id_1)
                    node_2 = ga.nodes.filter(id=node_id_2)
                    start_level = np.min([node_1.dmax[0], node_2.dmax[0]]).item()
                    end_level = start_level
                    if line_type == LineType.ORIFICE:
                        crest_level = ga.lines.orifices.filter(id=lines_1d_data["id"][count]).crest_level[0]
                    if line_type == LineType.WEIR:
                        crest_level = ga.lines.weirs.filter(id=lines_1d_data["id"][count]).crest_level[0]

                # Note that id (count) is the flowline index in Python (0-based indexing)
                feat.setAttributes([count, node_id_1, node_id_2, lines_1d_data["ds1d"][count], line_type, start_level, end_level, start_height, end_height, crest_level])
                progress_bar.set_value((count / number_of_lines) * 100.0)
                if not pr.addFeature(feat):
                    logger.error(f"Unable to add feature: {pr.lastError()}")

            elif line_type == LineType.CHANNEL:

                node_1 = ga.nodes.filter(id=node_id_1)
                node_2 = ga.nodes.filter(id=node_id_2)
                start_bottom_level = node_1.dmax[0].item()
                end_bottom_level = node_2.dmax[0].item()

                start_upper_level = SideViewGraphGenerator.retrieve_node_upper_level(node_id_1, lines_1d2d_data)
                end_upper_level = SideViewGraphGenerator.retrieve_node_upper_level(node_id_2, lines_1d2d_data)
                start_height = 0
                end_height = 0
                if not math.isnan(start_upper_level):
                    start_height = (start_upper_level - start_bottom_level)

                if not math.isnan(end_upper_level):
                    end_height = (end_upper_level - end_bottom_level)

                feat.setAttributes([count, node_id_1, node_id_2, lines_1d_data["ds1d"][count], line_type, start_bottom_level, end_bottom_level, start_height, end_height, None])
                progress_bar.set_value((count / number_of_lines) * 100.0)
                if not pr.addFeature(feat):
                    logger.error(f"Unable to add feature: {pr.lastError()}")

            last_index = count  # noqa

        # # Pumps are not part of lines, add as well.
        # pump_coords = ga.pumps.node_coordinates.transpose()[1:].tolist()  # drop nan-element
        # node1_ids = ga.pumps.node1_id[1:].tolist()
        # node2_ids = ga.pumps.node2_id[1:].tolist()

        # # TODO: Retrieve this info
        # start_level = 3.0
        # end_level = 3.0
        # start_height = 3.0
        # end_height = 3.0
        # for count, pump_coord in enumerate(pump_coords):
        #     feat = QgsFeature()

        #     p1 = QgsPointXY(pump_coord[0], pump_coord[1])
        #     p2 = QgsPointXY(pump_coord[2], pump_coord[3])
        #     geom = QgsGeometry.fromPolylineXY([p1, p2])
        #     feat.setGeometry(geom)

        #     feat.setAttributes([count+last_index, node1_ids[count], node2_ids[count], None, LineType.PUMP, start_level, end_level, start_height, end_height])
        #     features.append(feat)

        graph_layer.updateExtents()
        return graph_layer

    @staticmethod
    def generate_node_info(gridadmin_file: Path):
        ga = GridH5Admin(gridadmin_file.with_suffix('.h5'))

        nodes_all = ga.nodes.only("coordinates", "drain_level", "storage_area", "calculation_type", "dmax", "id", "is_manhole", "content_pk", "node_type").data
        nodes_all = {k: v.tolist() for (k, v) in nodes_all.items()}

        lines_1d2d_data = ga.lines.subset("1D2D").only("dpumax", "line").data
        lines_1d2d_data = {k: v.tolist() for (k, v) in lines_1d2d_data.items()}

        node_info = {}
        number_of_nodes = len(nodes_all["coordinates"][0])
        for count in range(number_of_nodes):
            node_id = nodes_all["id"][count]
            length = math.sqrt(nodes_all["storage_area"][count])
            length = 0.0 if math.isnan(length) else length

            bottom_level = nodes_all["dmax"][count]
            if not ga.has_2d:
                upper_level = nodes_all["drain_level"][count]  # can be nan
            else:
                upper_level = SideViewGraphGenerator.retrieve_node_upper_level(node_id, lines_1d2d_data)

            height = 0.0
            if math.isnan(upper_level):
                height = 0.0
            else:
                # TODO: This does not always seem to be the case for 2D nodes (node type = [1, 2, 5, 6])
                if (nodes_all["node_type"][count] not in [1, 2, 5, 6]):
                    assert upper_level >= bottom_level

                if upper_level < bottom_level:
                    # logger.warning(f"Derived upper level of node is below bottom level for node {node_id}")
                    upper_level, bottom_level = bottom_level, upper_level

                height = (upper_level-bottom_level)

            node_info[node_id] = {
                "type": nodes_all["calculation_type"][count],
                "is_manhole": nodes_all["is_manhole"][count],
                "level": bottom_level,
                "height": height,
                "length": length,
            }

        return node_info

    @staticmethod
    def content_type_to_line_type(content_type: str) -> int:
        """Convertes content_type string to LineType enum"""
        content_type = content_type.removeprefix('v2_')
        if content_type == "pipe":
            return LineType.PIPE
        elif content_type == "culvert":
            return LineType.CULVERT
        elif content_type == "orifice":
            return LineType.ORIFICE
        elif content_type == "weir":
            return LineType.WEIR
        elif content_type == "channel":
            return LineType.CHANNEL

        raise AttributeError(f"Unknown content type: {content_type}")

    @staticmethod
    def cross_section_max_height(cross_section, tables) -> float:
        """Retrieves (or estimates) the height for a cross section using various heuristics.
            Returns nan when estimation not possible. Raises exception when inconsistencies are
            encountered.
        """
        count = cross_section.count[0]
        offset = cross_section.offset[0]
        shape = cross_section.shape[0]
        width_1d = cross_section.width_1d[0]

        if shape == CrossSectionShape.CIRCLE.value:
            assert count == 0
            return width_1d.item()  # for circle width = height
        elif shape in (CrossSectionShape.TABULATED_RECTANGLE.value, CrossSectionShape.TABULATED_TRAPEZIUM.value):
            # Check whether shape is closed (check whether last width is 0.0), otherwise return nan
            if tables[:, offset:offset+count][:, -1][1] == 0.0:  # widths are second row
                return max(tables[:, offset:offset+count][0]).item()  # heights are first row
            else:
                return math.nan
        elif shape == CrossSectionShape.OPEN_RECTANGLE.value:
            return math.nan

        raise AttributeError(f"Unable to derive height of cross section: {cross_section.id[0]} with shape {shape}")

    @staticmethod
    def retrieve_node_upper_level(node_id, lines_1d2d) -> float:
        # For 2D model, take minimum dpumax from adjacent 1D2D lines (if available)
        dpumax_list = []
        for count in range(len(lines_1d2d["line"][0])):
            if node_id == lines_1d2d["line"][0][count] or node_id == lines_1d2d["line"][1][count]:
                dpumax_list.append(lines_1d2d["dpumax"][count])

        if dpumax_list:
            return np.min(dpumax_list).item()
        else:
            return math.nan
