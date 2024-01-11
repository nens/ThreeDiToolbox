# (c) Nelen & Schuurmans, see LICENSE.rst.
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtCore import QObject
from qgis.core import QgsSettings
from qgis.PyQt.QtWidgets import QFileDialog
import os
import logging

logger = logging.getLogger(__name__)


class ThreeDiResultSelection(QObject):

    schematisation_selected = pyqtSignal(str)

    def __init__(self, iface, layer_manager):

        super().__init__()
        self.iface = iface

        self.icon_path = ":/plugins/ThreeDiToolbox/icons/icon_add_datasource.png"
        self.menu_text = u"Select 3Di schematisation"
        self.layer_manager = layer_manager

    def run(self):
        # Show dialog and load schematisation
        settings = QgsSettings("3di", "qgisplugin")

        try:
            init_path = settings.value("last_used_spatialite_path", type=str)
        except TypeError:
            logger.debug(
                "Last used datasource path is no string, setting it to our home dir."
            )
            init_path = os.path.expanduser("~")

        filepath, __ = QFileDialog.getOpenFileName(
            None, "Open 3Di model spatialite file", init_path, "Spatialite (*.sqlite)"
        )

        if filepath == "":
            return False

        self.add_spatialite_connection(filepath, self.iface)
        settings.setValue("last_used_spatialite_path", os.path.dirname(filepath))

        self.layer_manager._on_set_schematisation(filepath)

    def add_spatialite_connection(self, spatialite_path, iface):
        """Add spatialite_path as a spatialite connection in the qgis-browser"""
        filename = os.path.basename(spatialite_path)
        QgsSettings().setValue(
            f"SpatiaLite/connections/{filename}/sqlitepath", spatialite_path
        )
        iface.reloadConnections()

    def on_unload(self):
        pass
