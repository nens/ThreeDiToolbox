import logging

from threedi_results_analysis.utils.qlogging import ConsoleHandler
from threedi_results_analysis.utils.qlogging import FileHandler
from threedi_results_analysis.utils.qlogging import QgisHandler
from threedi_results_analysis.utils.qlogging import setup_logging

logger = logging.getLogger(__name__)


def test_logfile_path():
    assert "threedi-qgis-log.txt" in FileHandler.get_filename()


def test_loglevel():
    """Python's default log level is WARN. We want to see more."""
    setup_logging()
    root_logger = logging.getLogger("")
    assert root_logger.getEffectiveLevel() == logging.DEBUG


def test_root_logsetup():
    setup_logging()
    root_logger = logging.getLogger("")
    handler_classes = [h.__class__ for h in root_logger.handlers]
    assert ConsoleHandler in handler_classes
    assert FileHandler in handler_classes
    assert QgisHandler not in handler_classes


def test_plugin_logsetup():
    setup_logging()
    our_plugin_logger = logging.getLogger("threedi_results_analysis")
    handler_classes = [h.__class__ for h in our_plugin_logger.handlers]
    assert ConsoleHandler not in handler_classes
    assert FileHandler not in handler_classes
    assert QgisHandler in handler_classes


def test_logging_doesnt_crash():
    setup_logging()
    logger.critical("Just log something")
    logger.error("Just log something")
    logger.warning("Just log something")
    logger.info("Just log something")
    logger.debug("Just log something")


def test_write_to_file():
    setup_logging()
    text = "This ends up in the logfile"
    logger.error(text)
    assert text in open(FileHandler.get_filename()).read()
