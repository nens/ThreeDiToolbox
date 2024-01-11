from pathlib import Path
from qgis.core import QgsGradientColorRamp
from qgis.core import QgsGradientStop
from qgis.core import QgsMapLayerStyle
from qgis.core import QgsStyle
from qgis.PyQt.QtGui import QColor
from ThreeDiToolbox.utils.color import ColorRampData

import logging
import os


STYLES_ROOT = Path(__file__).parent.parent / "layer_styles"

logger = logging.getLogger(__name__)


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
    QgsStyle.defaultStyle().addColorRamp(data.name, color_ramp_from_data(data))
    # If ramp with this name already exists, it will be overridden (default QGIS API behaviour)


def apply_style(layer, style_name, stype):
    qml_path = STYLES_ROOT / stype / style_name

    style_manager = layer.styleManager()
    style_manager.reset()

    style = QgsMapLayerStyle()
    style.readFromLayer(layer)

    current_style_name = (
        layer.styleManager().currentStyle()
    )  # default style name depends on language settings

    for qml_file in qml_path.glob("*.qml"):
        style_name = qml_file.stem.capitalize()
        style_manager.addStyle(style_name, style)
        style_manager.setCurrentStyle(style_name)
        (message, success) = layer.loadNamedStyle(os.path.join(qml_path, qml_file))

        if not success:  # if style not loaded remove it
            style_manager.removeStyle(style_name)
            logger.info("Styling file not succesfully loaded: {fn}".format(fn=qml_file))
            logger.info(message)

    layer.styleManager().setCurrentStyle("Default")
    layer.styleManager().removeStyle(current_style_name)
