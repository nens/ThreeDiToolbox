from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtXml import QDomElement, QDomDocument
import logging

logger = logging.getLogger(__name__)


class ThreeDiPluginTool(QObject):
    """
    The base class of each tool
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def write(self, doc: QDomDocument, elem: QDomElement) -> bool:
        """Called when a QGS project is written, allowing each tool to presist
        additional info int the dedicated xml tools node."""

        return True

    def read(self, _: QDomElement) -> bool:
        """Called when a QGS project is read, allowing each tool to read
        additional info from the dedicated xml tools node."""

        return True

    def on_unload(self):
        """Called when the plugin is unloaded. Tool can cleanup necessary items"""
        pass
