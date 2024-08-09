from osgeo import ogr
from numpy import nan
from typing import Sequence


ogr.UseExceptions()


GEOMETRY_TYPE_MAP = {
    "node": ogr.wkbPoint,
    "cell": ogr.wkbPolygon,
    "flowline": ogr.wkbLineString,
    "pump": ogr.wkbPoint,
    "pump_linestring": ogr.wkbLineString,
}


def threedigrid_to_ogr(
    tgt_ds: ogr.DataSource,
    layer_name: str,
    gridadmin_gpkg: str,
    attributes: dict,
    attr_data_types: dict,
    ids: Sequence[int] = None,
):
    """
    Modify the target ogr Datasource with custom attributes

    :param tgt_ds: target ogr Datasource
    :param layer_name: name of the layer to be copied to target ogr Datasource.
        One of 'node', 'cell', 'flowline', 'pump', 'pump_linestring'
    :param gridadmin_gpkg: path to gridadmin.gpkg
    :param attributes: {attribute name: list of values}
    :param attr_data_types: {attribute name: ogr data type}
    :param ids: list of ids to request a subset of nodes/cells/flowlines
    :return: modified ogr Datasource
    """
    if layer_name not in list(GEOMETRY_TYPE_MAP.keys()):
        raise ValueError(f"Argument layer_name must be one of {list(GEOMETRY_TYPE_MAP.keys())}")

    # open gridadmin.gpkg as input datasource
    src_ds = ogr.Open(gridadmin_gpkg, 0)
    if src_ds is None:
        raise FileNotFoundError(f"{gridadmin_gpkg} not found.")

    # copy the source layer with the specified layer name to the target datasource
    src_layer = src_ds.GetLayerByName(layer_name)
    if ids is not None:
        src_layer.SetAttributeFilter(f"id in {tuple(ids)}")
    layer = tgt_ds.CopyLayer(src_layer, layer_name)
    layer_defn = layer.GetLayerDefn()

    # the initial geometry type of the layer is unknown or none
    # thus we need to set geometry type manually
    layer_defn.SetGeomType(GEOMETRY_TYPE_MAP[layer_name])

    # add additional attributes to the layer
    for attr_name, attr_values in attributes.items():
        if len(attr_values) != layer.GetFeatureCount():
            raise ValueError(
                f"The number of attribute values ({len(attr_values)}) supplied for attribute {attr_name} differs from "
                f"the number of {layer_name} features to be copied ({layer.GetFeatureCount()})"
            )
        if layer_defn.GetFieldIndex(attr_name) == -1:
            field_defn = ogr.FieldDefn(attr_name, attr_data_types[attr_name])
            layer.CreateField(field_defn)

        # set the additional attribute value for each feature
        for i, feature in enumerate(layer):
            val = attr_values[i]
            if feature is None or val is None or val is nan:
                continue
            if attr_data_types[attr_name] in [ogr.OFTInteger]:
                val = int(val)
            elif attr_data_types[attr_name] in [ogr.OFTString]:
                val = val.decode("utf-8") if isinstance(val, bytes) else str(val)

            feature[attr_name] = val
            layer.SetFeature(feature)
            feature = None

    return
