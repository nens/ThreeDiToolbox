from enum import Enum

"""
    Code (adapted from) from nens/threedi-schematisation-editor.
    Modified to take gridadmin data into account (instead of spatialite)
"""


class CrossSectionShape(Enum):
    CLOSED_RECTANGLE = 0  # should not be present in gridadmin
    OPEN_RECTANGLE = 1
    CIRCLE = 2
    EGG = 3  # should not be present in gridadmin
    TABULATED_RECTANGLE = 5
    TABULATED_TRAPEZIUM = 6
    YZ = 7  # should not be present in gridadmin
    INVERTED_EGG = 8  # should not be present in gridadmin


NON_TABLE_SHAPES = {
    CrossSectionShape.CLOSED_RECTANGLE.value,
    CrossSectionShape.OPEN_RECTANGLE.value,
    CrossSectionShape.CIRCLE.value,
    CrossSectionShape.EGG.value,
    CrossSectionShape.INVERTED_EGG.value,
}


TABLE_SHAPES = {
    CrossSectionShape.TABULATED_RECTANGLE.value,
    CrossSectionShape.TABULATED_TRAPEZIUM.value,
    CrossSectionShape.YZ.value,
}

# def cross_section_table_values(cross_section_table, shape_value):
#     """Get height and width values."""
#     height_list, width_list = [], []
#     for row in cross_section_table.split("\n"):
#         height_str, width_str = row.split(",")
#         height = float(height_str)
#         width = float(width_str)
#         height_list.append(height)
#         width_list.append(width)
#     if shape_value == CrossSectionShape.YZ.value:
#         height_list, width_list = width_list, height_list
#     return height_list, width_list

# def cross_section_max_height(cross_section):
#     """Get max height value."""
#     shape_value = feature["cross_section_shape"]
#     if shape_value not in TABLE_SHAPES:
#         return feature["cross_section_height"]
#     table = feature["cross_section_table"]
#     height_list, _ = cross_section_table_values(table, shape_value)
#     return max(height_list)

# def cross_section_max_width(feature):
#     """Get max width value."""
#     shape_value = feature["cross_section_shape"]
#     if shape_value not in TABLE_SHAPES:
#         return feature["cross_section_width"]
#     table = feature["cross_section_table"]
#     _, width_list = cross_section_table_values(table, shape_value)
#     return max(width_list)
