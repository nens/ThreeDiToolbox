"""Plugin initialization module

Qgis automatically calls an installed plugin's :py:func:`classFactory` to
actually load the plugin.

Note: beforehand we call our dependency mechanism (see
:doc:`linked_external-dependencies_readme`) to ensure all dependencies are
there.

"""
from pathlib import Path
from ThreeDiToolbox import dependencies

import faulthandler
import sys


#: Handy constant for building relative paths.
PLUGIN_DIR = Path(__file__).parent


# sys.stderr is not available under Windows in Qgis, which is what the faulthandler
# uses by default.
if sys.stderr is not None and hasattr(sys.stderr, "fileno"):
    faulthandler.enable()

print('Ensuring dependencies are cleaned')
dependencies.ensure_everything_cleaned_up()


def enable_high_dpi_scaling():
    """Enable High DPI scaling."""
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtCore import QCoreApplication
    from qgis.PyQt.QtWidgets import QApplication

    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)


def classFactory(iface):
    """Return ThreeDiToolbox class from file ThreeDiToolbox.

    In addition, we set up python logging (see
    :py:mod:`ThreeDiToolbox.utils.qlogging`).

    args:
        iface (QgsInterface): A QGIS interface instance.

    """
    from ThreeDiToolbox.utils.qlogging import setup_logging

    enable_high_dpi_scaling()
    setup_logging()

    from .threedi_plugin import ThreeDiPlugin

    return ThreeDiPlugin(iface)
