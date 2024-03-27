"""Tests QGIS plugin init."""
from threedi_results_analysis import dependencies
from threedi_results_analysis import PLUGIN_DIR

import configparser
import importlib
import logging
import mock
import pkg_resources
import threedi_results_analysis


logger = logging.getLogger(__name__)

TEST_DATA_DIR = PLUGIN_DIR / "tests" / "data"


def test_read_init():
    """Test that the plugin __init__ will validate on plugins.qgis.org."""

    # You should update this list according to the latest in
    # https://github.com/qgis/qgis-django/blob/master/qgis-app/plugins/validator.py
    # Last updated 2019-06-17 by Reinout
    required_metadata = [
        "name",
        "description",
        "version",
        "qgisMinimumVersion",
        "email",
        "author",
        "about",
        "tracker",
        "repository",
    ]

    metadata_file = PLUGIN_DIR / "metadata.txt"
    logger.info(metadata_file)
    metadata = []
    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read(metadata_file, encoding="utf-8")
    message = 'Cannot find a section named "general" in %s' % metadata_file
    assert parser.has_section("general"), message
    metadata.extend(parser.items("general"))

    for key in required_metadata:
        message = 'Cannot find mandatory metadata "%s" in metadata source (%s).' % (
            key,
            metadata_file,
        )
        assert key in dict(metadata), message


def test_classFactory(qtbot):
    # Smoke test: just fire it up.
    def mock_init(self, iface):
        # Don't let it set up all the tools, we're testing that elsewhere.
        return

    # Somehow some deps seemed to be missing after a recent change, that's why we install
    # everything again.
    importlib.reload(pkg_resources)
    dependencies.ensure_everything_installed()
    with mock.patch("threedi_results_analysis.threedi_plugin.ThreeDiPlugin.__init__", mock_init):
        iface = mock.Mock()
        assert threedi_results_analysis.classFactory(iface)
