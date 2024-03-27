from pathlib import Path
from threedigrid.admin.gridadmin import GridH5Admin
from threedi_results_analysis.tool_sideview.utils import LineType
from threedi_results_analysis.tool_sideview.cross_section_utils import CrossSectionShape
import math
import logging
import numpy as np
logger = logging.getLogger(__name__)


class SideViewGraphGenerator():

    def __init__(self, gridadmin_file: Path):
        # Preload some big data structs
        self.ga = GridH5Admin(gridadmin_file.with_suffix('.h5'))
        self.lines_1d2d_data = self.ga.lines.subset("1D2D").only("dpumax", "line").data
        self.lines_1d2d_data = {k: v.tolist() for (k, v) in self.lines_1d2d_data.items()}

    def retrieve_profile_info_from_flowline(self, flowline_id: int) -> tuple[float, float, float, float, float, int]:

        line = self.ga.lines.filter(id=flowline_id)

        start_level = None
        end_level = None
        start_height = None
        end_height = None
        crest_level = None

        line_type = SideViewGraphGenerator.content_type_to_line_type(line.content_type[0].decode())
        node_id_1 = line.line[0][0]
        node_id_2 = line.line[1][0]

        if line_type == LineType.PIPE or line_type == LineType.CULVERT or line_type == LineType.ORIFICE or line_type == LineType.WEIR:
            cross1_id = line.cross1[0]
            cross2_id = line.cross2[0]
            assert cross1_id == cross2_id  # pipes and culverts have only one cross section definition
            cross_section = self.ga.cross_sections.filter(id=cross1_id)

            try:
                height = SideViewGraphGenerator.cross_section_max_height(cross_section, self.ga.cross_sections.tables)
            except AttributeError:
                raise AttributeError(f"Unable to derive height of cross section: {cross_section.id[0]} {cross1_id} {cross1_id} with shape {cross_section.shape[0]} for line {flowline_id}")

            if math.isnan(height):  # Not an error, simply not enough information
                logger.warning(f"Unable to derive cross section height for cross section {cross1_id} with shape {cross_section.shape[0]} for line {flowline_id}, setting height to 0.")
                height = 0.0
            start_height = height
            end_height = height

            if line_type == LineType.PIPE or line_type == LineType.CULVERT:
                start_level = line.invert_level_start_point[0].item()
                end_level = line.invert_level_end_point[0].item()
            elif line_type == LineType.ORIFICE or line_type == LineType.WEIR:
                # for bottom level, take dmax of adjacent nodes
                node_1 = self.ga.nodes.filter(id=node_id_1)
                node_2 = self.ga.nodes.filter(id=node_id_2)
                start_level = np.min([node_1.dmax[0], node_2.dmax[0]]).item()
                end_level = start_level
                # crest_level is input, can be corrected due to incorrect node bottom levels -> use dpumax
                # crest_level = ga.lines.orifices.filter(id=lines_1d_data["id"][count]).crest_level[0].item()
                crest_level = line.dpumax[0].item()

        elif line_type == LineType.CHANNEL:

            node_1 = self.ga.nodes.filter(id=node_id_1)
            node_2 = self.ga.nodes.filter(id=node_id_2)
            start_level = node_1.dmax[0].item()
            end_level = node_2.dmax[0].item()

            start_upper_level = SideViewGraphGenerator.retrieve_node_upper_level(node_id_1, self.lines_1d2d_data)
            end_upper_level = SideViewGraphGenerator.retrieve_node_upper_level(node_id_2, self.lines_1d2d_data)
            start_height = 0
            end_height = 0
            if not math.isnan(start_upper_level):
                start_height = (start_upper_level - start_level)

            if not math.isnan(end_upper_level):
                end_height = (end_upper_level - end_level)

        return (start_level, end_level, start_height, end_height, crest_level, line_type)

    def retrieve_profile_info_from_node(self, node_id: int) -> tuple[float, float]:

        node = self.ga.nodes.filter(id=node_id)

        bottom_level = node.dmax[0]
        if not self.ga.has_2d:
            upper_level = node.drain_level[0].item()  # can be nan
            height = (upper_level-bottom_level)
        else:
            upper_level = SideViewGraphGenerator.retrieve_node_upper_level(node_id, self.lines_1d2d_data)

            height = np.float64(0.0)
            if math.isnan(upper_level):
                height = np.float64(0.0)
            else:
                # TODO: This does not always seem to be the case for 2D nodes (node type = [1, 2, 5, 6])
                if (node.node_type[0] not in [1, 2, 5, 6]):
                    assert upper_level >= bottom_level

                if upper_level < bottom_level:
                    logger.warning(f"Derived upper level of node is below bottom level for node {node_id}")
                    # Flip
                    upper_level, bottom_level = bottom_level, upper_level

                height = (upper_level-bottom_level)

        return (bottom_level.item(), height.item())

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
