from osgeo import ogr
from numpy import isnan


def threedigrid_to_ogr(
    tgt_ds: ogr.DataSource,
    layer_name: str,
    gridadmin_gpkg: str,
    attributes: dict,
    attr_data_types: dict,
):
    """
    Modify the target ogr Datasource with custom attributes

    :param tgt_ds: target ogr Datasource
    :param layer_name: name of the layer to be copied to target ogr Datasource
    :param gridadmin_gpkg: path to gridadmin.gpkg
    :param attributes: {attribute name: list of values}
    :param attr_data_types: {attribute name: ogr data type}
    :return: modified ogr Datasource
    """

    # open gridadmin.gpkg as input datasource
    src_ds = ogr.Open(gridadmin_gpkg, 1)
    if src_ds is None:
        raise FileNotFoundError(f"{gridadmin_gpkg} not found.")

    # copy the layer with the specified layer type to the target datasource
    layer = src_ds.GetLayerByName(layer_name)
    tgt_ds.CopyLayer(layer, layer_name)

    # iterate over layers in the target data source
    for index in range(tgt_ds.GetLayerCount()):
        layer = tgt_ds.GetLayer(index)
        layer_defn = layer.GetLayerDefn()

        # the initial geometry type of the layer is unknown or none
        # thus we need to set geometry type manually
        if layer_name == "node":
            layer_defn.SetGeomType(ogr.wkbPoint)
        elif layer_name == "cell":
            layer_defn.SetGeomType(ogr.wkbPolygon)
        elif layer_name == "flowline":
            layer_defn.SetGeomType(ogr.wkbLineString)

        # add additional attributes to the layer
        for attr_name, attr_values in attributes.items():
            if layer.GetLayerDefn().GetFieldIndex(attr_name) == -1:
                field_defn = ogr.FieldDefn(attr_name, attr_data_types[attr_name])
                layer.CreateField(field_defn)

            # set the additional attribute value for each feature
            for i in range(layer.GetFeatureCount()):
                if i >= len(attr_values):
                    break
                val = attr_values[i]
                if val is None or isnan(val):
                    continue
                if attr_data_types[attr_name] in [ogr.OFTInteger]:
                    val = int(val)
                elif attr_data_types[attr_name] in [ogr.OFTString]:
                    val = val.decode("utf-8") if isinstance(val, bytes) else str(val)

                feature = layer.GetFeature(i)
                if feature is None:
                    continue
                feature[attr_name] = val
                layer.SetFeature(feature)
                feature = None

    return
