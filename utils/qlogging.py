"""Module for setting up both python and qgis logging.

In our plugin code, we just want to use ``logger.info()`` and so. This ought
to end up in a logfile we can look at for debug purposes. Ideally, customers
can mail it to us.

Log messages also ought to end up in qgis's ``QgsMessageLog`` at the bottom of
the screen (if you've enabled it). We should set this up only for our own
messages, btw.

TODO: there probably needs to be some tweaking of log levels. Perhaps the
verbosity ought to be made configurable.

"""
from qgis.core import Qgis
from qgis.core import QgsApplication
from qgis.core import QgsMessageLog
from ThreeDiToolbox.utils import log_traceback_monkeypatch  # noqa

import logging
import os


LOGFILE_NAME = "threedi-qgis-log.txt"
PYTHON_FORMAT = "%(name)s %(levelname)s %(message)s"
QGIS_FORMAT = "%(name)s\n%(message)s"  # Note: split over two lines.


logger = logging.getLogger(__name__)


class QgisLogHandler(logging.Handler):
    """logging handler to get python log messages into the qgis MessageLog."""

    def emit(self, record):
        """Show log message in the message area

        We map the python log level to qgis' levels. Note: qgis doesn't
        distinguish between ERROR and WARNING. Normally, we use WARNING for
        stuff that might be wrong and ERROR for stuff that really is wrong. We
        hardly use CRITICAL. So it is best to treat python's ERROR level as
        ``qgis.Critical``, as that's the most useful distinction.

        We don't do popups or messagebar stuff: that kind of UI decisions is
        best left to the actual UI code. Some logger.error() messages should
        be shown to the user in the message bar, but others not. We cannnot
        make a generic decision here.

        """
        msg = self.format(record)

        if record.levelno >= logging.ERROR:
            level = Qgis.Critical
        elif record.levelno >= logging.WARNING:
            level = Qgis.Warning
        else:
            level = Qgis.Info

        QgsMessageLog.logMessage(msg, level=level)


def logfile_path():
    """Return logfile location

    We place the logfile (called :py:data:`LOGFILE_NAME`) inside our qgis
    profile's directory.

    returns:
        full path (str) to our logfile

    """
    return os.path.join(QgsApplication.qgisSettingsDirPath(), LOGFILE_NAME)


def setup_logging():
    """
    Set up python and QGIS logging.

    Set the root logger level to DEBUG.
    Add file and console handlers to the root logger.
    Add a QGIS handler to loggers within ThreeDiToolbox.
    Set level of PyQt5 loggers to INFO
    """
    root_logger = logging.getLogger("")
    # Python's default log level is WARN, but we also want to see DEBUG
    # messages.
    root_logger.setLevel(logging.DEBUG)
    if not root_logger.handlers:
        # console
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        python_formatter = logging.Formatter(PYTHON_FORMAT)
        stream_handler.setFormatter(python_formatter)
        root_logger.addHandler(stream_handler)
        # file
        file_handler = logging.FileHandler(logfile_path(), mode="w", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(python_formatter)
        root_logger.addHandler(file_handler)
        logger.info("Started logfile: %s", logfile_path())

    # QGIS handler for all "__name__" loggers in the ThreeDiToolbox package
    our_plugin_logger = logging.getLogger("ThreeDiToolbox")
    if not our_plugin_logger.handlers:
        qgis_log_handler = QgisLogHandler()
        qgis_log_handler.setLevel(logging.INFO)
        qgis_formatter = logging.Formatter(QGIS_FORMAT)
        qgis_log_handler.setFormatter(qgis_formatter)
        our_plugin_logger.addHandler(qgis_log_handler)

    # We don't want all the "PyQt5.uic.properties DEBUG setting property text"
    # messages.
    verbose_pyqt_logger = logging.getLogger("PyQt5.uic")
    verbose_pyqt_logger.setLevel(logging.INFO)
