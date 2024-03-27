"""Main pytest configuration file: fixtures + a qgis import mechanism fix.

Pytest automatically uses a ``conftest.py`` file, when found. Note that you
can have also have such files in subdirectories. The fixtures in this file
*stay* available there, except when you override them.

"""
from qgis.core import QgsProject
from qgis.core import QgsVectorLayer

from threedi_results_analysis import PLUGIN_DIR
from threedi_results_analysis.threedi_plugin_model import ThreeDiGridItem
from threedi_results_analysis.threedi_plugin_model import ThreeDiResultItem

from pathlib import Path

import os
import pytest
import shutil


def fix_import_mechanism():
    """Make pytest work in combination with qgis.

    We prevent Qgis from grabbing python's import mechanism. Qgis overrides
    something, which breaks pytest by causing an infinite import loop.

    """
    os.environ["QGIS_NO_OVERRIDE_IMPORT"] = "KEEPYOURPAWSOFF"


fix_import_mechanism()  # Needs to be called right away.

DATA_DIR = PLUGIN_DIR / "tests" / "data"
BERGERMEER_DIR = DATA_DIR / "testmodel" / "v2_bergermeer"
RESULTS_3DI_PATH = BERGERMEER_DIR / "results_3di.nc"


@pytest.fixture()
def threedi_result():
    """Fixture: return a instance of ThreediResult

    The instance contains result data of the model 'v2_bergermeer'. It
    contains both results and aggregate result data.

    """
    # Late import, otherwise we get circular import errors.
    from threedi_results_analysis.datasource.threedi_results import ThreediResult

    return ThreediResult(file_path=RESULTS_3DI_PATH, h5_path=BERGERMEER_DIR / "gridadmin.h5")


@pytest.fixture()
def ts_datasources(tmp_path):
    """Fixture: return ts_datasources with one threedi_result (the one above) preloaded.

    Note that the test data is first copied, so it is safe to modify.

    """
    # Late import, otherwise we get circular import errors.
    from threedi_results_analysis.tool_result_selection.models import TimeseriesDatasourceModel

    shutil.copytree(BERGERMEER_DIR, tmp_path / "v2_bergermeer")
    copied_results_3di_path = tmp_path / "v2_bergermeer" / "results_3di.nc"
    result = TimeseriesDatasourceModel()
    test_values = {
        "active": False,
        "name": "bergermeer v2 from main conftest.py",
        "file_path": copied_results_3di_path,
        "type": "netcdf-groundwater",
    }
    result.insertRows([test_values])
    return result


@pytest.fixture(scope='session')
def three_di_result_item(tmpdir_factory):
    """ Result pointing to the bergermeer test model. """
    tmp_path = tmpdir_factory.mktemp("testdata")
    shutil.copytree(BERGERMEER_DIR, tmp_path / "v2_bergermeer")

    path_gpkg = tmp_path / "v2_bergermeer" / "gridadmin.gpkg"
    path_nc = tmp_path / "v2_bergermeer" / "results_3di.nc"
    grid = ThreeDiGridItem(path=Path(path_gpkg), text="foo")
    result = ThreeDiResultItem(path=Path(path_nc))
    grid.appendRow(result)

    gpkg_layers = {"Node": "node", "Flowline": "flowline"}
    for layer_name, table_name in gpkg_layers.items():
        layer_uri = f"{grid.path}|layername={table_name}"
        vector_layer = QgsVectorLayer(layer_uri, layer_name, "ogr")
        grid.layer_ids[table_name] = vector_layer.id()
        QgsProject.instance().addMapLayer(vector_layer)

    yield result
