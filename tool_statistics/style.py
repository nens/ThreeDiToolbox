import os
import numpy as np

from qgis.core import (
    QgsSymbolLayer,
    QgsMarkerSymbol,
    QgsProperty,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
)
from qgis import utils

STYLE_DIR = os.path.join(os.path.dirname(__file__), "style")


class Style:
    def __init__(
        self,
        name: str,
        output_type: str,
        params: dict,
        qml: str,
        styling_method,
    ):
        self.name = name
        assert output_type in ("flowline", "node", "cell", "pump", "pump_linestring", "raster")
        self.output_type = output_type
        self.params = params
        if os.path.isabs(qml):
            self.qml = qml
        else:
            self.qml = os.path.join(STYLE_DIR, qml)
        if not os.path.isfile(self.qml):
            raise FileNotFoundError("QML file not found")
        self.styling_method = styling_method

    def apply(self, qgis_layer, style_kwargs):
        self.styling_method(qgis_layer, self.qml, **style_kwargs)


def style_on_single_column(layer, qml: str, column: str, update_classes: bool = True):
    layer.loadNamedStyle(qml)
    layer.renderer().setClassAttribute(column)
    if update_classes:
        layer.renderer().updateClasses(
            vlayer=layer,
            mode=layer.renderer().mode(),
            nclasses=len(layer.renderer().ranges()),
        )

        # Add a class for 0 if the lowest value is 0
        range_0 = layer.renderer().ranges()[0]
        if range_0.lowerValue() == 0 and range_0.upperValue() > 0.000001:
            layer.renderer().addBreak(breakValue=0.000001, updateSymbols=True)
            layer.renderer().updateRangeLabel(rangeIndex=0, label="0")

    layer.triggerRepaint()
    utils.iface.layerTreeView().refreshLayerSymbology(layer.id())


def style_difference(layer, qml: str, value: str, reference: str, update_classes: bool = True):
    layer.loadNamedStyle(qml)
    layer.renderer().setClassAttribute(f"{value} - {reference}")
    if update_classes:
        layer.renderer().updateClasses(
            vlayer=layer,
            mode=layer.renderer().mode(),
            nclasses=len(layer.renderer().ranges()),
        )
    layer.triggerRepaint()
    utils.iface.layerTreeView().refreshLayerSymbology(layer.id())


def style_balance(
    layer,
    qml: str,
    positive_col1: str,
    positive_col2: str,
    positive_col3: str,
    negative_col1: str,
    negative_col2: str,
    negative_col3: str,
):
    layer.loadNamedStyle(qml)

    positive_columns = []
    negative_columns = []
    for col in [positive_col1, positive_col2, positive_col3]:
        if col != "":
            positive_columns.append("coalesce({col}, 0)".format(col=col))
    for col in [negative_col1, negative_col2, negative_col3]:
        if col != "":
            negative_columns.append("coalesce({col}, 0)".format(col=col))
    class_attribute_string = "({pos})-({neg})".format(
        pos=" + ".join(positive_columns), neg=" + ".join(negative_columns)
    )
    layer.renderer().setClassAttribute(class_attribute_string)
    layer.renderer().deleteAllClasses()
    min_expression = QgsExpression(
        "minimum({})".format(class_attribute_string)
    )
    max_expression = QgsExpression(
        "maximum({})".format(class_attribute_string)
    )
    context = QgsExpressionContext()
    context.appendScopes(
        QgsExpressionContextUtils.globalProjectLayerScopes(layer)
    )
    min_val = min_expression.evaluate(context)
    max_val = max_expression.evaluate(context)
    abs_max = max(abs(min_val), abs(max_val))
    class_bounds = list(
        np.arange(abs_max * -1, abs_max, ((abs_max - abs_max * -1) / 10.0))
    )
    class_bounds.append(abs_max)
    for i in range(len(class_bounds) - 1):
        layer.renderer().addClassLowerUpper(
            lower=class_bounds[i], upper=class_bounds[i + 1]
        )
    color_ramp = layer.renderer().sourceColorRamp()
    layer.renderer().updateColorRamp(color_ramp)
    layer.triggerRepaint()
    utils.iface.layerTreeView().refreshLayerSymbology(layer.id())


def style_change_water_level(layer, qml: str, first: str, last: str):

    layer.loadNamedStyle(qml)
    class_attribute_string = (
        f"((coalesce({last}, bottom_level))-(coalesce({first}, bottom_level)))"
    )
    layer.renderer().setClassAttribute(class_attribute_string)
    # layer.renderer().deleteAllClasses()
    # min_expression = QgsExpression('minimum({})'.format(class_attribute_string))
    # max_expression = QgsExpression('maximum({})'.format(class_attribute_string))
    # context = QgsExpressionContext()
    # context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
    # min_val = min_expression.evaluate(context)
    # max_val = max_expression.evaluate(context)
    # abs_max = max(abs(min_val), abs(max_val))
    # class_bounds = list(np.arange(abs_max * -1, abs_max, ((abs_max - abs_max * -1) / 10.0)))
    # class_bounds.append(abs_max)
    # for i in range(len(class_bounds) - 1):
    #     layer.renderer().addClassLowerUpper(lower=class_bounds[i], upper=class_bounds[i + 1])
    # color_ramp = layer.renderer().sourceColorRamp()
    # layer.renderer().updateColorRamp(color_ramp)
    layer.triggerRepaint()
    utils.iface.layerTreeView().refreshLayerSymbology(layer.id())


def style_as_vector(layer, qml: str, x: str, y: str):
    layer.loadNamedStyle(qml)

    # set data defined rotation
    rotation_expression = 'degrees(azimuth( make_point( 0,0), make_point( "{x}",  "{y}" )))'.format(
        x=x, y=y
    )
    data_defined_angle = (
        QgsMarkerSymbol()
        .dataDefinedAngle()
        .fromExpression(rotation_expression)
    )
    layer.renderer().sourceSymbol().setDataDefinedAngle(data_defined_angle)

    # update coloring
    class_attribute_string = 'sqrt("{x}" * "{x}" + "{y}" * "{y}")'.format(
        x=x, y=y
    )
    layer.renderer().setClassAttribute(class_attribute_string)
    layer.renderer().updateClasses(
        vlayer=layer,
        mode=layer.renderer().mode(),
        nclasses=len(layer.renderer().ranges()),
    )

    # update size
    layer.renderer().setSymbolSizes(0, 2)

    layer.triggerRepaint()
    utils.iface.layerTreeView().refreshLayerSymbology(layer.id())


def style_flow_direction(layer, qml: str, column: str, invert=False):
    layer.loadNamedStyle(qml)

    # set data defined rotation
    rotation_expression = f"""
        CASE WHEN "{column}" {">" if invert else "<"} 0
        THEN degrees(azimuth(start_point($geometry), end_point($geometry))) + 90
        ELSE degrees(azimuth(start_point($geometry), end_point($geometry))) - 90
        END
    """
    data_defined_angle = (
        QgsMarkerSymbol()
        .dataDefinedAngle()
        .fromExpression(rotation_expression)
    )
    layer.renderer().sourceSymbol()[1].subSymbol().setDataDefinedAngle(
        data_defined_angle
    )

    # update coloring
    class_attribute_string = f'abs("{column}")'
    layer.renderer().setClassAttribute(class_attribute_string)
    layer.renderer().updateClasses(
        vlayer=layer,
        mode=layer.renderer().mode(),
        nclasses=len(layer.renderer().ranges()),
    )

    # set marker size & line width
    p10 = (
        layer.renderer().ranges()[0].upperValue()
    )  # hacky way to get the p10 and p90 values as there is no such function available in qgis
    p90 = layer.renderer().ranges()[-1].lowerValue()
    marker_size_expression = (
        "coalesce(scale_linear(abs({column}), {p10}, {p90}, 1, 3), 0)".format(
            column=column, p10=p10, p90=p90
        )
    )
    data_defined_marker_size = (
        QgsMarkerSymbol()
        .dataDefinedSize()
        .fromExpression(marker_size_expression)
    )
    layer.renderer().sourceSymbol()[1].subSymbol().setDataDefinedSize(
        data_defined_marker_size
    )

    line_width_expression = "coalesce(scale_linear(abs({column}), {p10}, {p90}, 0.1, 1), 0)".format(
        column=column, p10=p10, p90=p90
    )
    data_defined_line_width = QgsProperty.fromExpression(line_width_expression)
    layer.renderer().sourceSymbol()[0].setDataDefinedProperty(
        QgsSymbolLayer.PropertyStrokeWidth, data_defined_line_width
    )

    # update classes because triggerRepaint alone doesn't do the trick
    layer.renderer().updateClasses(
        vlayer=layer,
        mode=layer.renderer().mode(),
        nclasses=len(layer.renderer().ranges()),
    )
    layer.triggerRepaint()

    # update legend for layer
    utils.iface.layerTreeView().refreshLayerSymbology(layer.id())


def style_gradient(layer, qml: str, column: str):
    style_flow_direction(layer=layer, qml=qml, column=column, invert=True)


def style_ts_reduction_analysis(
    layer, qml: str, col1: str, col2: str, col3: str
):
    layer.loadNamedStyle(qml)
    filter_expression = "{col1} >10 or {col2} > 50 or {col3} > 80".format(
        col1=col1, col2=col2, col3=col3
    )
    layer.renderer().rootRule().children()[0].setFilterExpression(
        filterExp=filter_expression
    )
    layer.triggerRepaint()
    utils.iface.layerTreeView().refreshLayerSymbology(layer.id())


STYLE_FLOW_DIRECTION = Style(
    name="Flow direction",
    output_type="flowline",
    params={"column": "column"},
    qml="flow_direction.qml",
    styling_method=style_flow_direction,
)

STYLE_GRADIENT = Style(
    name="Gradient",
    output_type="flowline",
    params={"column": "column"},
    qml="flow_direction.qml",
    styling_method=style_gradient,
)

STYLE_SINGLE_COLUMN_GRADUATED_FLOWLINE = Style(
    name="Single column graduated",
    output_type="flowline",
    params={"column": "column"},
    qml="flowline.qml",
    styling_method=style_on_single_column,
)

STYLE_TIMESTEP_REDUCTION_ANALYSIS = Style(
    name="Timestep reduction analysis",
    output_type="flowline",
    params={"col1": "column", "col2": "column", "col3": "column"},
    qml="ts_reduction_analysis.qml",
    styling_method=style_ts_reduction_analysis,
)

STYLE_SINGLE_COLUMN_GRADUATED_NODE = Style(
    name="Single column graduated",
    output_type="node",
    params={"column": "column"},
    qml="node.qml",
    styling_method=style_on_single_column,
)

STYLE_WATER_ON_STREET_DURATION_NODE = Style(
    name="Water on street duration",
    output_type="node",
    params={"column": "column"},
    qml="water_on_street_duration.qml",
    styling_method=lambda layer, qml, column, update_classes=False: style_on_single_column(
        layer,
        qml,
        column,
        update_classes
    ),
)

STYLE_MANHOLE_WATER_DEPTH_0D1D_NODE = Style(
    name="Manhole water depth (0D1D)",
    output_type="node",
    params={"value": "column"},
    qml="manhole_water_depth.qml",
    styling_method=lambda layer, qml, value, reference="drain_level", update_classes=False: style_difference(
        layer,
        qml,
        value,
        reference,
        update_classes
    ),
)

STYLE_MANHOLE_WATER_DEPTH_1D2D_NODE = Style(
    name="Manhole water depth (1D2D)",
    output_type="node",
    params={"value": "column"},
    qml="manhole_water_depth.qml",
    styling_method=lambda layer, qml, value, reference="exchange_level_1d2d", update_classes=False: style_difference(
        layer,
        qml,
        value,
        reference,
        update_classes
    ),
)

STYLE_MANHOLE_MIN_FREEBOARD_0D1D = Style(
    name="Manhole freeboard (0D1D)",
    output_type="node",
    params={"value": "column"},
    qml="manhole_freeboard.qml",
    styling_method=lambda layer, qml, value, reference="drain_level", update_classes=False: style_difference(
        layer,
        qml,
        value,
        reference,
        update_classes
    ),
)

STYLE_MANHOLE_MIN_FREEBOARD_1D2D = Style(
    name="Manhole freeboard (1D2D)",
    output_type="node",
    params={"value": "column"},
    qml="manhole_freeboard.qml",
    styling_method=lambda layer, qml, value, reference="exchange_level_1d2d", update_classes=False: style_difference(
        layer,
        qml,
        value,
        reference,
        update_classes
    ),
)

STYLE_CHANGE_WL = Style(
    name="Change in water level",
    output_type="cell",
    params={"first": "column", "last": "column"},
    qml="change_water_level.qml",
    styling_method=style_change_water_level,
)

STYLE_VECTOR = Style(
    name="Vector",
    output_type="node",
    params={"x": "column", "y": "column"},
    qml="vector.qml",
    styling_method=style_as_vector,
)

STYLE_SINGLE_COLUMN_GRADUATED_CELL = Style(
    name="Single column graduated",
    output_type="cell",
    params={"column": "column"},
    qml="cell.qml",
    styling_method=style_on_single_column,
)

STYLE_BALANCE = Style(
    name="Balance",
    output_type="cell",
    params={
        "positive_col1": "column",
        "positive_col2": "column",
        "positive_col3": "column",
        "negative_col1": "column",
        "negative_col2": "column",
        "negative_col3": "column",
    },
    qml="balance.qml",
    styling_method=style_balance,
)

STYLE_SINGLE_COLUMN_GRADUATED_PUMP = Style(
    name="Single column graduated",
    output_type="pump",
    params={"column": "column"},
    qml="node.qml",
    styling_method=style_on_single_column,
)

STYLE_SINGLE_COLUMN_GRADUATED_PUMP_LINESTRING = Style(
    name="Single column graduated",
    output_type="pump_linestring",
    params={"column": "column"},
    qml="flowline.qml",
    styling_method=style_on_single_column,
)


STYLES = [
    STYLE_FLOW_DIRECTION,
    STYLE_GRADIENT,
    STYLE_SINGLE_COLUMN_GRADUATED_FLOWLINE,
    STYLE_TIMESTEP_REDUCTION_ANALYSIS,
    STYLE_SINGLE_COLUMN_GRADUATED_NODE,
    STYLE_VECTOR,
    STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    STYLE_CHANGE_WL,
    STYLE_BALANCE,
    STYLE_WATER_ON_STREET_DURATION_NODE,
    STYLE_MANHOLE_WATER_DEPTH_0D1D_NODE,
    STYLE_MANHOLE_WATER_DEPTH_1D2D_NODE,
    STYLE_MANHOLE_MIN_FREEBOARD_0D1D,
    STYLE_MANHOLE_MIN_FREEBOARD_1D2D,
    STYLE_SINGLE_COLUMN_GRADUATED_PUMP,
    STYLE_SINGLE_COLUMN_GRADUATED_PUMP_LINESTRING,
]


DEFAULT_STYLES = {
    # Flowlines
    "q": {"flowline": STYLE_FLOW_DIRECTION},
    "u1": {"flowline": STYLE_FLOW_DIRECTION},
    "au": {"flowline": STYLE_SINGLE_COLUMN_GRADUATED_FLOWLINE},
    "qp": {"flowline": STYLE_FLOW_DIRECTION},
    "up1": {"flowline": STYLE_FLOW_DIRECTION},
    "ts_max": {"flowline": STYLE_SINGLE_COLUMN_GRADUATED_FLOWLINE},
    "grad": {"flowline": STYLE_GRADIENT},
    "bed_grad": {"flowline": STYLE_GRADIENT},
    "wl_at_xsec": {"flowline": STYLE_SINGLE_COLUMN_GRADUATED_FLOWLINE},

    # Pumps
    "q_pump": {
        "pump": STYLE_SINGLE_COLUMN_GRADUATED_PUMP,
        "pump_linestring": STYLE_SINGLE_COLUMN_GRADUATED_PUMP_LINESTRING,
    },

    # Nodes
    "s1": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "vol": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "rain": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "rain_depth": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "infiltration_rate_simple": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "infiltration_rate_simple_mm": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "su": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "uc": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "ucx": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "ucy": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "q_lat": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "q_lat_mm": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "intercepted_volume": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "intercepted_volume_mm": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "q_sss": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "q_sss_mm": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "q_in_x": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "q_in_x_mm": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "q_in_y": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "q_in_y_mm": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "q_out_x": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "q_out_x_mm": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "q_out_y": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
    "q_out_y_mm": {
        "node": STYLE_SINGLE_COLUMN_GRADUATED_NODE,
        "cell": STYLE_SINGLE_COLUMN_GRADUATED_CELL,
    },
}
