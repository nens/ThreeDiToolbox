import os

from osgeo import ogr

from threedigrid.admin.exporters.geopackage import GeopackageExporter
from qgis.PyQt.QtCore import QObject, pyqtSlot
from qgis.core import Qgis, QgsVectorLayer, QgsProject, QgsCoordinateReferenceSystem
from qgis.utils import iface

from ThreeDiToolbox.tool_result_selection import models
from ThreeDiToolbox.utils.user_messages import StatusProgressBar, pop_up_critical
from ThreeDiToolbox.utils.constants import TOOLBOX_GROUP_NAME
from .threedi_plugin_model import ThreeDiGridItem, ThreeDiResultItem


class ThreeDiPluginModelLoader(QObject):

    @staticmethod
    def _add_layer_to_group(layer, layer_name):
        """
        Add a layer to the layer tree group
        """
        root = QgsProject.instance().layerTreeRoot()
        root_group = root.findGroup(TOOLBOX_GROUP_NAME)
        if not root_group:
            root_group = root.insertGroup(0, TOOLBOX_GROUP_NAME)

        layer_group = root_group.findGroup(layer_name)
        if not layer_group:
            layer_group = root_group.insertGroup(0, layer_name)

        project = QgsProject.instance()
        project.addMapLayer(layer, addToLegend=False)
        layer_group.insertLayer(0, layer)

    @staticmethod
    def _add_layers_from_gpkg(path, item: ThreeDiGridItem) -> bool:
        """Retrieves layers from gpk and add to project.

        Checks whether all layers contain the same CRS, if
        so, sets this CRS on the project
        """

        gpkg_layers = [lr.GetName() for lr in ogr.Open(str(path))]
        srs_ids = set()
        for layer in gpkg_layers:

            # Using the QgsInterface function addVectorLayer shows (annoying) confirmation dialogs
            # iface.addVectorLayer(gpkg_file + "|layername=" + layer, layer, 'ogr')
            vector_layer = QgsVectorLayer(str(path) + "|layername=" + layer, layer, "ogr")
            if not vector_layer.isValid():
                return False

            # TODO: styling?

            layer_srs_id = vector_layer.crs().srsid()
            srs_ids.add(layer_srs_id)

            ThreeDiPluginModelLoader._add_layer_to_group(vector_layer, item.text())

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
                return False
        else:
            iface.messageBar().pushMessage(
                "GeoPackage",
                f"Skipping setting project CRS - the source file {str(path)} SRS codes are inconsistent.",
                Qgis.Warning,
            )
            return False

        return True

    @staticmethod
    @pyqtSlot(ThreeDiGridItem)
    def import_grid_item(item: ThreeDiGridItem) -> bool:
        path = item.path
        base, suffix = path.parent / path.stem, path.suffix
        path_gpkg = base.with_suffix(".gpkg")

        if suffix == ".h5":
            progress_bar = StatusProgressBar(100, "Generating geopackage")
            path_h5 = base.with_suffix(".h5")
            exporter = GeopackageExporter(str(path_h5), str(path_gpkg))
            exporter.export(
                lambda count, total, pb=progress_bar: pb.set_value((count * 100) // total)
            )
            del progress_bar

        iface.messageBar().pushMessage("GeoPackage", "Generated geopackage", Qgis.Info)

        if not ThreeDiPluginModelLoader._add_layers_from_gpkg(path_gpkg, item):
            pop_up_critical("Failed adding the layers to the project.")
            return False

        iface.messageBar().pushMessage(
            "GeoPackage", "Added layers to the project", Qgis.Info
        )

        return True

    @staticmethod
    @pyqtSlot(ThreeDiResultItem)
    def import_result_item(threedi_result_item: ThreeDiResultItem) -> bool:
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

        return True
