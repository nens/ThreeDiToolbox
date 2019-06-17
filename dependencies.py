"""Handle dependencies: installation and checking/logging.

See ``external-dependencies/README.rst`` for a full explanation of the
dependency handling.

``python dependencies.py`` runs ``main()``: it generates ``constraints.txt``.

``ensure_everything_installed()`` checks if ``DEPENDENCIES`` are installed and
installs them if needed.

``check_importability()`` double-checks if everything is importable. It also
logs the locations.

Note that we use logging in ``check_importability()`` as we want to have the
result in the logfile. The rest of the module uses ``print()`` statements
because it gets executed before any logging has been configured.

As we're called directly from ``__init__.py``, the imports should be
resticted. No qgis message boxes and so!

"""
from collections import namedtuple
from pathlib import Path

import importlib
import logging
import os
import pkg_resources
import subprocess
import sys


Dependency = namedtuple("Dependency", ["name", "package", "constraint"])

DEPENDENCIES = [
    Dependency("GeoAlchemy2", "geoalchemy2", ">=0.6.2, <0.7"),
    Dependency("SQLAlchemy", "sqlalchemy", ">=1.1.11, <1.2"),
    Dependency("h5py", "h5py", ">= 2.7.0"),
    Dependency("lizard-connector", "lizard_connector", "==0.6"),
    Dependency("pyqtgraph", "pyqtgraph", ">=0.10.0"),
    Dependency("threedigrid", "threedigrid", "==1.0.13"),
    Dependency("cached-property", "cached_property", ""),
    Dependency("threedi-modelchecker", "threedi_modelchecker", ">=0.2"),
]
# If you add a dependency, also adjust external-dependencies/populate.sh
INTERESTING_IMPORTS = ["numpy", "gdal", "setuptools"]

OUR_DIR = Path(__file__).parent

logger = logging.getLogger(__name__)


def ensure_everything_installed():
    """Check if DEPENDENCIES are installed and install them if missing."""
    print("sys.path:")
    for directory in sys.path:
        print("  - %s" % directory)
    missing = _check_presence(DEPENDENCIES)
    target_dir = _dependencies_target_dir()
    _install_dependencies(missing, target_dir=target_dir)


def _dependencies_target_dir(our_dir=OUR_DIR):
    """Return python dir inside our profile

    Return two dirs up if we're inside the plugins dir. If not, we have to
    import from qgis (which we don't really want in this file) and ask for our
    profile dir.

    """
    if "plugins" in str(our_dir).lower():
        # Looks like we're in the plugin dir. Return ../..
        return OUR_DIR.parent.parent
    # We're somewhere outside of the plugin directory. Perhaps a symlink?
    # Perhaps a development setup? We're forced to import qgis and ask for our
    # profile directory, something we'd rather not do at this stage. But ok.
    print("We're not in our plugins directory: %s" % our_dir)
    from qgis.core import QgsApplication

    python_dir = Path(QgsApplication.qgisSettingsDirPath()) / "python"
    print("We've asked qgis for our python directory: %s" % python_dir)
    return python_dir


def check_importability():
    """Check if the dependendies are importable and log the locations.

    If something is not importable, which should not happen, it raises an
    ImportError automatically. Which is exactly what we want, because we
    cannot continue.

    """
    packages = [dependency.package for dependency in DEPENDENCIES]
    packages += INTERESTING_IMPORTS
    logger.info("sys.path:\n    %s", "\n    ".join(sys.path))
    for package in packages:
        imported_package = importlib.import_module(package)
        logger.info(
            "Import '%s' found at \n    '%s'", package, imported_package.__file__
        )


def _install_dependencies(dependencies, target_dir):
    for dependency in dependencies:
        print("Installing '%s' into %s" % (dependency.name, target_dir))
        python_interpreter = _get_python_interpreter()
        result = subprocess.run(
            [
                python_interpreter,
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--find-links",
                str(OUR_DIR / "external-dependencies"),
                "--target",
                str(target_dir),
                (dependency.name + dependency.constraint),
            ],
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        print(result.stdout)
        result.check_returncode()  # Raises CalledProcessError upon failure.
        print("Installed %s into %s" % (dependency.name, target_dir))


def _get_python_interpreter():
    """Return the path to the python3 interpreter.

    Under linux sys.executable is set to the python3 interpreter used by Qgis.
    However, under Windows/Mac this is not the case and sys.executable refers to the
    Qgis start-up script.
    """
    interpreter = None
    executable = sys.executable
    directory, filename = os.path.split(executable)
    if "python3" in filename.lower():
        interpreter = executable
    elif "qgis" in filename.lower():
        interpreter = os.path.join(directory, "python3.exe")
    else:
        raise EnvironmentError("Unexpected value for sys.executable: %s" % executable)
    assert os.path.exists(interpreter)  # safety check
    return interpreter


def _check_presence(dependencies):
    """Check if all dependencies are present. Return missing dependencies."""
    missing = []
    for dependency in dependencies:
        requirement = dependency.name + dependency.constraint
        try:
            pkg_resources.require(requirement)
        except pkg_resources.DistributionNotFound:
            print(
                "Dependency '%s' (%s) not found"
                % (dependency.name, dependency.constraint)
            )
            missing.append(dependency)
        except pkg_resources.VersionConflict:
            print(
                "Dependency '%s' (%s) has the wrong version"
                % (dependency.name, dependency.constraint)
            )
            missing.append(dependency)
    return missing


def generate_constraints_txt(target_dir=OUR_DIR):
    constraints_file = target_dir / "constraints.txt"
    lines = ["# Generated by dependencies.py"]
    lines += [(dependency.name + dependency.constraint) for dependency in DEPENDENCIES]
    lines.append("")
    constraints_file.write_text("\n".join(lines))
    print("Wrote constraints to %s" % constraints_file)


if __name__ == "__main__":  # pragma: no cover
    generate_constraints_txt()
