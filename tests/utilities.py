# coding=utf-8
from qgis.core import QgsApplication
import logging

logger = logging.getLogger(__name__)
_singletons = {}


def ensure_qgis_app_is_initialized():
    """Make sure qgis is initialized for testing."""
    # Note: if you just need the QT app to be there, you can use the qtbot fixture
    # from https://pytest-qt.readthedocs.io/en/latest/index.html
    if "app" not in _singletons:
        app = QgsApplication([], False)
        app.initQgis()
        logger.debug("Initialized qgis (for testing). Settings: %s", app.showSettings())
        _singletons["app"] = app
