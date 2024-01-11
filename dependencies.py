"""As this is the sunset version, we remove previously used dependencies installed
within the toolbox
"""
from collections import namedtuple
from pathlib import Path
from qgis.core import Qgis

import setuptools  # noqa: https://github.com/pypa/setuptools/issues/2993
import logging
import os
import platform
import shutil


# in case the dependency is a tar, the constraint should be the
# explicit version (e.g. "==3.8.0")
Dependency = namedtuple("Dependency", ["name", "package", "constraint", "tar"])

#: List of previously removed dependencies, we'll remove those
DEPENDENCIES = [
    Dependency("SQLAlchemy", "sqlalchemy", "==2.0.6", False),
    Dependency("GeoAlchemy2", "geoalchemy2", "==0.13.*", False),
    Dependency("lizard-connector", "lizard_connector", "==0.7.3", False),
    Dependency("pyqtgraph", "pyqtgraph", ">=0.13.2", False),
    Dependency("threedigrid", "threedigrid", "==2.0.*", False),
    Dependency("threedi-schema", "threedi_schema", "==0.217.*", False),
    Dependency("threedi-modelchecker", "threedi_modelchecker", "==2.4.*", False),
    Dependency("threedidepth", "threedidepth", "==0.6.1", False),
    Dependency("click", "click", ">=8.0", False),
    Dependency("alembic", "alembic", "==1.8.*", False),
    Dependency(
        "importlib-resources", "importlib_resources", "", False
    ),  # backward compat. alembic
    Dependency(
        "zipp", "zipp", "", False
    ),  # backward compat. alembic
    Dependency("Mako", "mako", "", False),
    Dependency("cftime", "cftime", ">=1.5.0", False),  # threedigrid[results]
    Dependency("packaging", "packaging", "", False),
    Dependency(
        "colorama", "colorama", "", False
    ),  # dep of click and threedi-modelchecker (windows)
    Dependency("networkx", "networkx", "", False),
    Dependency("condenser", "condenser", ">=0.2.1", False),
    Dependency("Shapely", "shapely", ">=2.0.0", False),
    Dependency("threedigrid_builder", "threedigrid_builder", "==1.12.*", False),
    Dependency("hydxlib", "hydxlib", "==1.5.1", False),
    Dependency("h5netcdf", "h5netcdf", "", False),
    Dependency("greenlet", "greenlet", "!=0.4.17", False),
    Dependency("typing-extensions", "typing_extensions", ">=4.2.0", False),
]
# Dependencies that contain compiled extensions for windows platform
WINDOWS_PLATFORM_DEPENDENCIES = [
    Dependency("scipy", "scipy", "==1.6.2", False),
]
# On Windows, the hdf5 binary and thus h5py version depends on the QGis version
# QGis upgraded from hdf5 == 1.10.7 to hdf5 == 1.14.0 in QGis 3.28.6
QGIS_VERSION = Qgis.QGIS_VERSION_INT
if QGIS_VERSION < 32806 and platform.system() == "Windows":
    SUPPORTED_HDF5_VERSIONS = ["1.10.7"]
    H5PY_DEPENDENCY = Dependency("h5py", "h5py", "==2.10.0", False)
else:
    SUPPORTED_HDF5_VERSIONS = ["1.14.0"]
    H5PY_DEPENDENCY = Dependency("h5py", "h5py", "==3.8.0", True)

# If you add a dependency, also adjust external-dependencies/populate.sh
INTERESTING_IMPORTS = ["numpy", "osgeo", "pip", "setuptools"]

OUR_DIR = Path(__file__).parent

logger = logging.getLogger(__name__)


def ensure_everything_cleaned_up():
    """Check if DEPENDENCIES are installed and install them if missing."""

    # We'll also remove distributions in the users 'python' folder, old versions of
    # the toolbox put them there
    _remove_old_distributions(DEPENDENCIES + WINDOWS_PLATFORM_DEPENDENCIES + [H5PY_DEPENDENCY], _prev_dependencies_target_dir())

    # We'll remove the deps subfolder
    target_dir = _dependencies_target_dir(create=False)
    shutil.rmtree(path=str(target_dir), ignore_errors=True)


def _dependencies_target_dir(our_dir=OUR_DIR, create=False) -> Path:
    """Return (and create) the desired deps folder

    This is the 'deps' subdirectory of the plugin home folder

    """
    target_dir = our_dir / "deps"
    if not target_dir.exists() and create:
        print(f"Creating target dir {target_dir}")
        target_dir.mkdir()

    return target_dir


def _prev_dependencies_target_dir(our_dir=OUR_DIR) -> Path:
    """Return python dir inside our profile

    Return two dirs up if we're inside the plugins dir. This was the
    previous installation folder of the dependencies.
    """
    if "plugins" in str(our_dir).lower():
        return OUR_DIR.parent.parent


def _remove_old_distributions(dependencies, path):
    """Remove old distributions of dependencies

    In previous version of the Toolbox, depencencies were
    stored in the users 'python' folder. This caused
    versioning conflicts (as these dependencies were
    not removed when the plugin was uninstalled).

    Removes all folders and files that contain the
    dependency name or package name
    """
    succeeded = True
    files_to_remove = [
        node
        for node in os.listdir(str(path))
        for dependency in dependencies
        if (dependency.package in node or dependency.name in node)
    ]

    for f in files_to_remove:
        dep_path = str(path / f)

        try:
            if os.path.exists(dep_path):
                if os.path.isfile(dep_path):
                    print(f"Deleting file {f} from {path}")
                    os.remove(dep_path)
                else:
                    print(f"Deleting folder {f} from {path}")
                    shutil.rmtree(dep_path)
        except PermissionError as e:
            print(f"Unable to remove {dep_path} ({str(e)})")
            succeeded = False

    return succeeded
