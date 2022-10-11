# (c) Nelen & Schuurmans, see LICENSE.rst.
"""
Miscellaneous tools.
"""
from qgis.core import QgsProject
from ThreeDiToolbox import PLUGIN_DIR
from ThreeDiToolbox.utils import qlogging
from ThreeDiToolbox.utils.layer_from_netCDF import FLOWLINES_LAYER_NAME
from ThreeDiToolbox.utils.layer_from_netCDF import NODES_LAYER_NAME
from ThreeDiToolbox.utils.layer_from_netCDF import PUMPLINES_LAYER_NAME
from ThreeDiToolbox.utils.user_messages import pop_up_info
from ThreeDiToolbox.utils.user_messages import pop_up_question

import logging
import os


# Shotgun approach for removing all problematic layers by their layer name.
# Very ad-hoc. Chance that it removes a layer that was not generated by the
# plugin due to filtering-by-name.
IDENTIFIER_LIKE = [FLOWLINES_LAYER_NAME, NODES_LAYER_NAME, PUMPLINES_LAYER_NAME]

logger = logging.getLogger(__name__)


class About(object):
    """Add 3Di logo and about info."""

    def __init__(self, iface):
        self.iface = iface
        self.icon_path = os.path.join(os.path.dirname(__file__), "icons", "icon.png")
        self.menu_text = "3Di about"

    def run(self):
        """Shows dialog with version information."""
        # TODO: add link to sites
        version_file = PLUGIN_DIR / "version.rst"
        version = version_file.read_text().rstrip()

        pop_up_info(
            "3Di Toolbox version %s" % version, "About2", self.iface.mainWindow()
        )

    def on_unload(self):
        pass


class ShowLogfile(object):
    """Show link to the logfile."""

    def __init__(self, iface):
        self.iface = iface
        self.icon_path = os.path.join(os.path.dirname(__file__), "icons", "icon_logfile.png")
        # ^^^ logo: LGPL, made by Oxygen Team, see
        # http://www.iconarchive.com/show/oxygen-icons-by-oxygen-icons.org/
        self.menu_text = "Show logfile"

    def run(self):
        """Show dialog with a simple clickable link to the logfile.

        Later on, we could also show the entire logfile inside the dialog. Or
        suggest an email. The clickable link is OK for now.

        Note: such a link does not work within the development docker.

        """
        title = "Show logfile"
        location = qlogging.logfile_path()
        message = "Logfile location: <a href='file:///%s'>%s</a>" % (location, location)
        pop_up_info(message, title, self.iface.mainWindow())

    def on_unload(self):
        pass


class CacheClearer(object):
    """Tool to delete cache files."""

    def __init__(self, iface, ts_datasources):
        """Constructor.

        Args:
            iface: QGIS interface
            ts_datasources: TimeseriesDatasourceModel instance
        """
        self.iface = iface
        self.icon_path = os.path.join(os.path.dirname(__file__), "icons", "icon_broom.png")
        self.menu_text = "Clear cache"
        self.ts_datasources = ts_datasources

    def run(self):
        """Find cached spatialite and csv layer files for *ALL* items in the
        TimeseriesDatasourceModel (i.e., *ALL* rows) object and delete them.
        """
        # TODO: can ts_datasources tell us its cached files? Or can we order it
        # to clean up its cache? (Instead of us poking around in its internals).
        spatialite_filepaths = [
            item.sqlite_gridadmin_filepath()
            for item in self.ts_datasources.rows
            if os.path.exists(item.sqlite_gridadmin_filepath())
        ]
        # Note: convert to set because duplicates are possible if the same
        # datasource is loaded multiple times
        cached = set(spatialite_filepaths)
        if not cached:
            pop_up_info("No cached files found.")
            return

        # Files linked to the layers in the map registry are held open by
        # Windows. You need to delete them manually from the registry to be
        # able to remove the underlying data. Note that deleting the layer
        # from the legend doesn't necessarily delete the layer from the map
        # registry, even though it may appear that no more layers are loaded
        # visually.
        # The specific error message (for googling):
        # "error 32 the process cannot access the file because it is being used
        # by another process"
        all_layers = list(QgsProject.instance().mapLayers().values())
        loaded_layers = [
            layer
            for layer in all_layers
            if any(identifier in layer.name() for identifier in IDENTIFIER_LIKE)
        ]
        loaded_layer_ids = [layer.id() for layer in loaded_layers]

        yes = pop_up_question(
            "The following files will be deleted:\n"
            + ",\n".join(cached)
            + "\n\nContinue?"
        )

        if yes:
            try:
                QgsProject.instance().removeMapLayers(loaded_layer_ids)
            except RuntimeError:
                logger.exception("Failed to delete map layers")

            for cached_spatialite_file in cached:
                try:
                    os.remove(cached_spatialite_file)
                except OSError:
                    msg = "Failed to delete %s." % cached_spatialite_file
                    logger.exception(msg)
                    pop_up_info(msg)

            pop_up_info(
                "Cache cleared. You may need to restart QGIS and reload your data."
            )

    def on_unload(self):
        pass
