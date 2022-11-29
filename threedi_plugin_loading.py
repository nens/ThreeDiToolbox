import os
from collections import OrderedDict

from threedigrid.admin.exporters.geopackage import GeopackageExporter
from qgis.PyQt.QtCore import QObject, pyqtSlot, pyqtSignal
from qgis.core import Qgis, QgsVectorLayer, QgsProject, QgsCoordinateReferenceSystem
from qgis.utils import iface

from ThreeDiToolbox.tool_result_selection import models
from ThreeDiToolbox.utils.user_messages import StatusProgressBar, pop_up_critical
from ThreeDiToolbox.utils.constants import TOOLBOX_QGIS_GROUP_NAME
from ThreeDiToolbox.utils.utils import safe_join
from ThreeDiToolbox.threedi_plugin_model import ThreeDiGridItem, ThreeDiResultItem

styles_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "layer_styles", "grid")

import logging
logger = logging.getLogger(__name__)


class ThreeDiPluginModelLoader(QObject):
    grid_loaded = pyqtSignal(ThreeDiGridItem)
    result_loaded = pyqtSignal(ThreeDiResultItem)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def _generate_gpkg(path_h5, path_gpkg):
        progress_bar = StatusProgressBar(100, "Generating geopackage")
        exporter = GeopackageExporter(str(path_h5), str(path_gpkg))
        exporter.export(
            lambda count, total, pb=progress_bar: pb.set_value((count * 100) // total)
        )
        del progress_bar
        iface.messageBar().pushMessage("GeoPackage", "Generated geopackage", Qgis.Info)

    @pyqtSlot(ThreeDiGridItem)
    def load_grid(self, item: ThreeDiGridItem) -> bool:
        # generate geopackage if needed and point item path to it
        if item.path.suffix == ".h5":
            path_h5 = item.path
            path_gpkg = path_h5.with_suffix(".gpkg")
            if not path_gpkg.exists():
                self.__class__._generate_gpkg(path_h5=path_h5, path_gpkg=path_gpkg)
            item.path = path_gpkg
        else:
            path_gpkg = item.path

        if not ThreeDiPluginModelLoader._add_layers_from_gpkg(path_gpkg, item):
            pop_up_critical("Failed adding the layers to the project.")
            return False

        iface.messageBar().pushMessage(
            "GeoPackage", "Added layers to the project", Qgis.Info
        )

        self.grid_loaded.emit(item)
        return True

    @pyqtSlot(ThreeDiGridItem)
    def unload_grid(self, item: ThreeDiGridItem) -> bool:
        """Removes the corresponding layers from the group in the project"""

        # TODO: does the layer also need to be removed from registry?

        assert item.layer_group
        # Deletion of root node of a tree will delete all nodes of the tree
        item.layer_group.parent().removeChildNode(item.layer_group)
        item.layer_group = None

    @pyqtSlot(ThreeDiGridItem)
    def update_grid(self, item: ThreeDiGridItem) -> bool:
        """Updates the group name in the project"""

        assert item.layer_group
        item.layer_group.setName(item.text())
        QgsProject.instance().setDirty()

    @pyqtSlot(ThreeDiResultItem)
    def load_result(self, threedi_result_item: ThreeDiResultItem) -> bool:
        """ Load Result file and apply default styling """
        path_nc = threedi_result_item.path

        layer_helper = models.DatasourceLayerHelper(path_nc)
        progress_bar = StatusProgressBar(100, "Retrieving layers from NetCDF")

        # Note that get_result_layers generates an intermediate sqlite
        line, node, cell, pumpline = layer_helper.get_result_layers(progress_bar)
        del progress_bar

        # Apply default styling on memory layers
        line.loadNamedStyle(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "layer_styles",
                "tools",
                "flowlines.qml",
            )
        )

        node.loadNamedStyle(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "layer_styles",
                "tools",
                "nodes.qml",
            )
        )

        QgsProject.instance().addMapLayers([line, node, cell, pumpline])

        self.result_loaded.emit(threedi_result_item)
        return True

    @staticmethod
    def _add_layers_from_gpkg(path, item: ThreeDiGridItem) -> bool:
        """Retrieves (a subset of the)  layers from gpk and add to project.

        Checks whether all layers contain the same CRS, if
        so, sets this CRS on the project.
        """

        # Layers need to be in specific order and naming:
        gpkg_layers = OrderedDict(
            [
                ("Pump (point)", "pump"),
                ("Node", "node"),
                ("Pump (line)", "pump_linestring"),
                ("Flowline", "flowline"),
                ("Cell", "cell"),
                ("Obstacle", "obstacle"),
            ]
        )

        srs_ids = set()
        invalid_layers = []
        empty_layers = []
        for layer_name, table_name in gpkg_layers.items():

            # Using the QgsInterface function addVectorLayer shows (annoying) confirmation dialogs
            # iface.addVectorLayer(gpkg_file + "|layername=" + layer, layer, 'ogr')
            vector_layer = QgsVectorLayer(str(path) + "|layername=" + table_name, layer_name, "ogr")
            if not vector_layer.isValid():
                invalid_layers.append(layer_name)
                continue

            # only load layers that contain some features
            if not vector_layer.featureCount():
                empty_layers.append(layer_name)
                continue

            # apply the style
            qml_path = safe_join(styles_dir, f"{table_name}.qml")
            if os.path.exists(qml_path):
                vector_layer.loadNamedStyle(qml_path)
                # prior to QGIS 3.24, this method would show a, (annoying) message box
                # warning when a style with the same styleName already existed. Unfortunately,
                # QgsProviderRegistry::styleExists is not available in Python
                if table_name not in vector_layer.listStylesInDatabase()[2]:
                    vector_layer.saveStyleToDatabase(table_name, "", True, "")

            srs_ids.add(vector_layer.crs().srsid())

            # Won't add if already exists
            item.layer_group = ThreeDiPluginModelLoader._add_layer_to_group(vector_layer, item.text())

        # Invalid layers info
        if invalid_layers:
            invalid_info = "\n\nThe following layers are missing or invalid:\n * " + "\n * ".join(invalid_layers) + "\n\n"
            iface.messageBar().pushMessage(
                "GeoPackage",
                invalid_info,
                Qgis.Warning,
            )

        # Empty layers info
        if empty_layers:
            empty_info = "\n\nThe following layers contained no feature:\n * " + "\n * ".join(empty_layers) + "\n\n"
            iface.messageBar().pushMessage(
                "GeoPackage",
                empty_info,
                Qgis.Warning,
            )

        if len(srs_ids) == 1:
            srs_id = srs_ids.pop()
            crs = QgsCoordinateReferenceSystem.fromSrsId(srs_id)
            if crs.isValid():
                QgsProject.instance().setCrs(crs)
                iface.messageBar().pushMessage(
                    "GeoPackage",
                    "Setting project CRS according to the source geopackage",
                    Qgis.Info,
                )
            else:
                iface.messageBar().pushMessage(
                    "GeoPackage",
                    "Skipping setting project CRS - does gridadmin file contains a valid SRS?",
                    Qgis.Warning,
                )
        else:
            iface.messageBar().pushMessage(
                "GeoPackage",
                f"Skipping setting project CRS - the source file {str(path)} SRS codes are inconsistent.",
                Qgis.Warning,
            )

        return True

    @staticmethod
    def _add_layer_to_group(layer, group_name):
        """
        Add a layer to the layer tree group, returns
        the corresponding group.
        """
        root = QgsProject.instance().layerTreeRoot()
        root_group = root.findGroup(TOOLBOX_QGIS_GROUP_NAME)
        if not root_group:
            root_group = root.insertGroup(0, TOOLBOX_QGIS_GROUP_NAME)

        layer_group = root_group.findGroup(group_name)
        if not layer_group:
            layer_group = root_group.insertGroup(0, group_name)

        # In case the group already contains a layer with the same name,
        # don't add the layer (TODO: allow overwrite?)
        existing_layers = layer_group.children()
        for existing_layer in existing_layers:
            if existing_layer.name() == layer.name():
                return layer_group

        project = QgsProject.instance()
        project.addMapLayer(layer, addToLegend=False)
        layer_group.addLayer(layer)

        return layer_group
