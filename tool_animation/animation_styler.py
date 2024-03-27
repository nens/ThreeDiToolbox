from pathlib import Path
from typing import List
import logging

import numpy as np

from qgis.core import QgsMarkerSymbol
from qgis.core import QgsProperty
from qgis.core import QgsSymbolLayer
from qgis.core import QgsVectorLayer
from qgis.utils import iface

from threedi_results_analysis.datasource.result_constants import WET_CROSS_SECTION_AREA
from threedi_results_analysis.utils.color import COLOR_RAMP_OCEAN_CURL
from threedi_results_analysis.utils.color import COLOR_RAMP_OCEAN_DEEP
from threedi_results_analysis.utils.color import COLOR_RAMP_OCEAN_HALINE
from threedi_results_analysis.utils.color import color_ramp_from_data

STYLES_ROOT = Path(__file__).parent / "layer_styles"
ANIMATION_LAYERS_NR_LEGEND_CLASSES = 24
assert ANIMATION_LAYERS_NR_LEGEND_CLASSES % 2 == 0

logger = logging.getLogger(__name__)


def style_animation_flowline_current(
    lyr: QgsVectorLayer, class_bounds: List[float], variable, field_postfix=""
):
    """Applies styling to Animation Toolbar flowline layer in 'current' mode"""

    # Load basic style settings from qml file
    qml_path = STYLES_ROOT / "flowline_current.qml"

    feedback, success = lyr.loadNamedStyle(str(qml_path), True)
    if not success:
        logger.error(feedback)

    renderer = lyr.renderer()

    # Set correct legend symbol rotation
    symbol = renderer.sourceSymbol().clone()
    if variable == WET_CROSS_SECTION_AREA.name:
        symbol.deleteSymbolLayer(1)
        max_symbol_size = 1.5
    else:
        symbol.symbolLayers()[1].setSymbolAngle(90)
        max_symbol_size = 2.5
        # make arrow invisible if attribute value for field self.field_name is NULL
        enable_exp = QgsProperty.fromExpression(f'($length /  @map_scale) > 0.0025 AND abs("result{field_postfix}") > 0')
        symbol.symbolLayers()[1].setDataDefinedProperty(QgsSymbolLayer.PropertyLayerEnabled, enable_exp)

    renderer.updateSymbols(symbol)

    if field_postfix and variable != WET_CROSS_SECTION_AREA.name:
        rotation_expression = f"""(
    CASE WHEN "result{field_postfix}" < 0 THEN 180 ELSE 0 END
    +
    CASE WHEN ("line_type" >= 51 AND "line_type" <= 58) THEN 180 ELSE 0 END
    + degrees(
        azimuth(
            start_point(
                transform(
                    $geometry,
                    layer_property(  @layer , 'crs' ),
                    @project_crs
                )
            ),
            end_point(
                transform(
                    $geometry,
                    layer_property(  @layer , 'crs' ),
                    @project_crs
                )
            )
        )
    )
) % 360"""

        data_defined_angle = QgsMarkerSymbol().dataDefinedAngle().fromExpression(rotation_expression)
        symbol.symbolLayers()[1].subSymbol().setDataDefinedAngle(data_defined_angle)
        renderer.updateSymbols(symbol)

    # Set classes and colors
    color_ramp = color_ramp_from_data(COLOR_RAMP_OCEAN_DEEP)

    # Quotes are required to indicate that field name needs to be used
    class_attribute_str = f'abs("result{field_postfix}")'
    renderer.setClassAttribute(class_attribute_str)
    renderer.deleteAllClasses()
    nr_classes = len(class_bounds) - 1
    for i in range(nr_classes):
        renderer.addClassLowerUpper(lower=class_bounds[i], upper=class_bounds[i + 1])
        class_middle = (class_bounds[i] + class_bounds[i + 1]) / 2
        symbol = renderer.symbolForValue(class_middle).clone()
        color_ramp_fraction = 0.2 + 0.8 * i / (nr_classes - 1)
        color = color_ramp.color(color_ramp_fraction)
        symbol.setColor(color)
        renderer.setLegendSymbolItem(str(i), symbol)

    # Symbol size
    renderer.setSymbolSizes(max_symbol_size / 3, max_symbol_size)

    iface.layerTreeView().refreshLayerSymbology(lyr.id())
    lyr.triggerRepaint()


def style_animation_node_current(
    lyr: QgsVectorLayer, percentiles: List[float], variable: str, cells: bool, field_postfix=""
):
    """Applies styling to Animation Toolbar node layer in 'current' mode"""

    # Load basic style settings from qml file
    if cells:
        qml_path = STYLES_ROOT / "cell_current.qml"
    else:
        qml_path = STYLES_ROOT / "node_current.qml"

    lyr.loadNamedStyle(str(qml_path), True)
    renderer = lyr.renderer()

    # Set classes
    if variable == "s1":
        class_attribute_str = f'coalesce("result{field_postfix}", bottom_level)'
        percentiles[0] = float(
            -9999
        )  # to make nodes / cells also visible when dry and bottom_level < percentile[0]
    else:
        class_attribute_str = f'"result{field_postfix}"'
    renderer.setClassAttribute(class_attribute_str)
    renderer.deleteAllClasses()
    nr_classes = len(percentiles) - 1
    for i in range(nr_classes):
        renderer.addClassLowerUpper(lower=percentiles[i], upper=percentiles[i + 1])
    color_ramp = color_ramp_from_data(COLOR_RAMP_OCEAN_HALINE)
    renderer.updateColorRamp(color_ramp)

    iface.layerTreeView().refreshLayerSymbology(lyr.id())
    lyr.triggerRepaint()


def style_animation_node_difference(
    lyr: QgsVectorLayer, percentiles: List[float], variable: str, cells: bool, field_postfix=""
):
    """Applies styling to Animation Toolbar node layer in 'difference' mode"""

    # Load basic style settings from qml file
    if cells:
        qml_path = STYLES_ROOT / "cell_difference.qml"
    else:
        qml_path = STYLES_ROOT / "node_difference.qml"
    lyr.loadNamedStyle(str(qml_path), True)
    renderer = lyr.renderer()

    # disregard the absolute maximum values when defining class bounds for a prettier result
    # instead, base the class bounds on the second highest percentile value (abs_high)
    # and include the absolute maximum afterwards, so that all values are visualized
    abs_high = max(abs(percentiles[1]), abs(percentiles[-2]))
    abs_max = max(abs(percentiles[0]), abs(percentiles[-1]))

    if abs_high != 0:
        class_bounds = (
            [abs_max * -1]
            + list(
                np.arange(
                    start=abs_high * -1,
                    stop=abs_high,
                    step=(
                        (abs_high - abs_high * -1)
                        / (ANIMATION_LAYERS_NR_LEGEND_CLASSES - 2)
                    ),
                )
            )
            + [abs_high, abs_max]
        )

        if variable == "s1":
            class_attribute_str = str(
                f'coalesce("result{field_postfix}", bottom_level) - coalesce("initial_value{field_postfix}", bottom_level)'
            )
        else:
            class_attribute_str = str(f'"result{field_postfix}" - "initial_value{field_postfix}"')
        renderer.setClassAttribute(class_attribute_str)
        renderer.deleteAllClasses()
        for i in range(len(class_bounds) - 1):
            renderer.addClassLowerUpper(
                lower=class_bounds[i], upper=class_bounds[i + 1]
            )

    color_ramp = color_ramp_from_data(COLOR_RAMP_OCEAN_CURL)
    renderer.updateColorRamp(color_ramp)

    lyr.triggerRepaint()
    iface.layerTreeView().refreshLayerSymbology(lyr.id())
