from collections import OrderedDict
from random import randint
from threedi_results_analysis.models.base import BaseModel
from threedi_results_analysis.models.base_fields import CheckboxField
from threedi_results_analysis.models.base_fields import ColorField
from threedi_results_analysis.models.base_fields import ValueField
from threedi_results_analysis.utils.color import COLOR_LIST

import numpy as np


EMPTY_TIMESERIES = np.array([], dtype=float)


def select_default_color(item_field):
    """
    return color for lines
    :param item_field: ItemField object
    :return: tuple with the 3 color bands (values between 0-256)
    """

    model = item_field.row.model
    colors = OrderedDict([(str(color), color) for color in COLOR_LIST])

    for item in model.rows:
        if str(item.color.value) in colors:
            del colors[str(item.color.value)]

    if len(colors) >= 1:
        return list(colors.values())[0]

    # predefined colors are all used, return random color
    return (randint(0, 256), randint(0, 256), randint(0, 256), int(180))


class WaterbalanceItemModel(BaseModel):
    """Model implementation for water balance graph items"""

    ts = np.array([0])

    class Fields(object):
        """Fields and functions of ModelItem"""

        active = CheckboxField(
            show=True, default_value=True, column_width=20, column_name=""
        )
        fill_color = ColorField(
            show=False,
            column_width=30,
            column_name="",
            default_value=select_default_color,
        )
        pen_color = ColorField(
            show=True,
            column_width=30,
            column_name="",
            default_value=select_default_color,
        )
        name = ValueField(
            show=True,
            column_width=120,
            column_name="Category"
        )
        default_method = ValueField(show=False)
        order = ValueField(show=False)
        series = ValueField(show=False)
