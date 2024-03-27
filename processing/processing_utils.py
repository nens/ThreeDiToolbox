import os
from collections import OrderedDict

from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer
from threedi_results_analysis.utils.utils import safe_join
from threedigrid.admin.exporters.geopackage import GeopackageExporter


class Progress(object):
    def __init__(self, feedback):
        self.percentage = 0
        self.feedback = feedback

    def update(self, count, total):
        if (count * 100) // total > self.percentage:
            self.percentage = (count * 100) // total
            self.feedback.setProgress(int(self.percentage))


def gridadmin2geopackage(input_gridadmin, gpkg_path, context, feedback):
    """Inside processing context function to convert gridadmin.h5 to GeoPackage layers."""
    layers_to_add = OrderedDict()

    plugin_dir = os.path.dirname(os.path.realpath(__file__))
    styles_dir = os.path.join(plugin_dir, "styles")
    progress = Progress(feedback)
    exporter = GeopackageExporter(input_gridadmin, gpkg_path)
    exporter.export(progress.update)
    feedback.pushInfo("Export done!")

    # Unfortunately, temporaryLayerStore keeps layers to be added as a dictionary, so the order is lost
    data_srcs = OrderedDict(
        [
            ("Obstacle", "obstacle"),
            ("Cell", "cell"),
            ("Pump (point)", "pump"),
            ("Pump (line)", "pump_linestring"),
            ("Node", "node"),
            ("Flowline", "flowline"),
        ]
    )

    layers = dict()
    invalid_layers = []
    empty_layers = []
    srs_ids = set()
    for layer_name, table_name in data_srcs.items():
        uri = gpkg_path + f"|layername={table_name}"
        layer = QgsVectorLayer(uri, layer_name, "ogr")
        layers[layer_name] = layer

        # only load valid layers
        if not layer.isValid():
            invalid_layers.append(layer_name)
            continue

        # only load layers that contain some features
        if not layer.featureCount():
            empty_layers.append(layer_name)
            continue

        # apply the style and add for loading when alg is completed
        qml_path = safe_join(styles_dir, f"{table_name}.qml")
        if os.path.exists(qml_path):
            layer.loadNamedStyle(qml_path)
            layer.saveStyleToDatabase(table_name, "", True, "")
        layer_srs_id = layer.crs().srsid()
        srs_ids.add(layer_srs_id)
        layers_to_add[layer_name] = layer

    # Invalid layers info
    if invalid_layers:
        invalid_info = "\n\nThe following layers are missing or invalid:\n * " + "\n * ".join(invalid_layers) + "\n\n"
        feedback.pushInfo(invalid_info)

    # Empty layers info
    if empty_layers:
        empty_info = "\n\nThe following layers contained no feature:\n * " + "\n * ".join(empty_layers) + "\n\n"
        feedback.pushInfo(empty_info)

    # Set project CRS only if all source layers have the same CRS
    if len(srs_ids) == 1:
        srs_id = srs_ids.pop()
        crs = QgsCoordinateReferenceSystem.fromSrsId(srs_id)
        if crs.isValid():
            context.project().setCrs(crs)
            crs_info = "Setting project CRS according to the source gridadmin file."
        else:
            crs_info = "Skipping setting project CRS - does gridadmin file contains a valid EPSG code?"
    else:
        crs_info = f"Skipping setting project CRS - the source file {input_gridadmin} EPSG codes are inconsistent."
    feedback.pushInfo(crs_info)
    return layers_to_add


def load_computational_layers(layers_to_add, project):
    """Function to add computational grid layers to the project map canvas."""
    root = project.instance().layerTreeRoot()
    group = root.addGroup("Computational grid")
    for index, (layer_name, layer) in enumerate(layers_to_add.items()):
        project.addMapLayer(layer, False)
        group.insertLayer(int(index), layer)
