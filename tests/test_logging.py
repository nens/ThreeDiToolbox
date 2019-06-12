from ThreeDiToolbox.utils.qlogging import logfile_path
from ThreeDiToolbox.utils.qlogging import setup_logging

import logging


logger = logging.getLogger(__name__)


def _cleanup_all_handlers():
    """Logging is global, so we need to zap all handlers.

    Note that we also zap the pytest log grabber, so don't count on that one
    to exist during these tests :-)

    """
    root_logger = logging.getLogger("")
    our_plugin_logger = logging.getLogger("ThreeDiToolbox")
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)
    for handler in our_plugin_logger.handlers:
        our_plugin_logger.removeHandler(handler)


def test_logfile_path():
    assert "threedi-qgis-log.txt" in logfile_path()


def test_loglevel():
    """Python's default log level is WARN. We want to see more."""
    _cleanup_all_handlers()
    setup_logging()
    root_logger = logging.getLogger("")
    assert root_logger.getEffectiveLevel() == logging.DEBUG


def test_root_logsetup():
    _cleanup_all_handlers()
    setup_logging()
    root_logger = logging.getLogger("")
    handler_names = [handler.__class__.__name__ for handler in root_logger.handlers]
    assert "StreamHandler" in handler_names
    assert "FileHandler" in handler_names
    assert "QgisLogHandler" not in handler_names


def test_plugin_logsetup():
    _cleanup_all_handlers()
    setup_logging()
    our_plugin_logger = logging.getLogger("ThreeDiToolbox")
    handler_names = [
        handler.__class__.__name__ for handler in our_plugin_logger.handlers
    ]
    assert "StreamHandler" not in handler_names
    assert "FileHandler" not in handler_names
    assert "QgisLogHandler" in handler_names


def test_logging_doesnt_crash():
    _cleanup_all_handlers()
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
    assert text in open(logfile_path()).read()
