from collections import namedtuple
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsGradientColorRamp
from qgis.core import QgsGradientStop
from qgis.core import QgsStyle

ColorRampData = namedtuple("ColorRampData", ["name", "colors", "info"])

COLOR_RAMP_OCEAN_DEEP = ColorRampData(
    "Ocean Deep",
    ["#ffffcc", "#a1dab4", "#41b6c4", "#2c7fb8", "#253494", "#0d1336"],
    {
        "source": "Thyng, K.M., C.A. Greene, R.D. Hetland, H.M. Zimmerle, and S.F. DiMarco (2016). True colors of "
        "oceanography: Guidelines for effective and accurate colormap selection. Oceanography, 29(3):9-13, "
        "http://dx.doi.org/10.5670/oceanog.2016.66."
    },
)

COLOR_RAMP_OCEAN_HALINE = ColorRampData(
    "Ocean Haline",
    [
        "#231067",
        "#2c1d90",
        "#19399f",
        "#0c5094",
        "#15628d",
        "#237289",
        "#308088",
        "#3a9187",
        "#45a383",
        "#53b47a",
        "#69c26e",
        "#8dd05f",
        "#b7da60",
        "#dce378",
        "#fdf2ae",
    ],
    {
        "source": "Thyng, K.M., C.A. Greene, R.D. Hetland, H.M. Zimmerle, and S.F. DiMarco (2016). True colors of "
        "oceanography: Guidelines for effective and accurate colormap selection. Oceanography, 29(3):9-13, "
        "http://dx.doi.org/10.5670/oceanog.2016.66."
    },
)

COLOR_RAMP_OCEAN_CURL = ColorRampData(
    "Ocean Curl",
    [
        # '#0D163E',
        "#1B3E57",
        "#185F6A",
        "#1B8179",
        "#4B9F84",
        "#8FBA99",
        "#CBD5C1",
        "#FAF1EE",
        "#EAC5B4",
        "#DD9983",
        "#CC6C67",
        "#B24560",
        "#8D2560",
        "#611554",
        # '#330C34'
    ],
    {
        "source": "Thyng, K.M., C.A. Greene, R.D. Hetland, H.M. Zimmerle, and S.F. DiMarco (2016). True colors of "
        "oceanography: Guidelines for effective and accurate colormap selection. Oceanography, 29(3):9-13, "
        "http://dx.doi.org/10.5670/oceanog.2016.66."
    },
)

COLOR_RAMPS = [COLOR_RAMP_OCEAN_DEEP, COLOR_RAMP_OCEAN_HALINE, COLOR_RAMP_OCEAN_CURL]


def color_ramp_from_data(data: ColorRampData):
    assert len(data.colors) >= 2, "A color ramp needs at least three colors"
    color1 = QColor(data.colors[0])
    color2 = QColor(data.colors[-1])
    stops = []
    if len(data.colors) > 2:
        for i, color in enumerate(data.colors[1:-1]):
            stop = QgsGradientStop((i + 1) / (len(data.colors) - 1), QColor(color))
            stops.append(stop)
    ramp = QgsGradientColorRamp(color1=color1, color2=color2, stops=stops)
    ramp.setInfo(data.info)
    return ramp


def add_color_ramp(data: ColorRampData):
    """Add color ramp to QGIS or replace if exists"""

    # If ramp with this name already exists, it will be overridden (default QGIS API behaviour)
    QgsStyle.defaultStyle().addColorRamp(data.name, color_ramp_from_data(data))


COLOR_LIST = [
    (34, 34, 34),
    (243, 195, 0),
    (135, 86, 146),
    (243, 132, 0),
    (161, 202, 241),
    (190, 0, 50),
    (194, 178, 128),
    (132, 132, 130),
    (0, 136, 86),
    (230, 143, 172),
    (0, 103, 165),
    (249, 147, 121),
    (96, 78, 151),
    (246, 166, 0),
    (179, 68, 108),
    (220, 211, 0),
    (136, 45, 23),
    (141, 182, 0),
    (101, 69, 34),
    (226, 88, 34),
    (43, 61, 38),
]
