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
]
INTERESTING_IMPORTS = ["numpy", "gdal", "setuptools"]

our_dir = Path(__file__).parent
PROFILE_LIBRARY_DIR = our_dir.parent.parent

logger = logging.getLogger(__name__)


def ensure_everything_installed():
    """Check if DEPENDENCIES are installed and install them if missing."""
    missing = _check_presence(DEPENDENCIES)
    _install_dependencies(missing)


def check_importability():
    """Check if the dependendies are importable and log the locations.

    If something is not importable, which should not happen, it raises an
    ImportError automatically. Which is exactly what we want, because we
    cannot continue.

    """
    packages = [dependency.package for dependency in DEPENDENCIES]
    packages += INTERESTING_IMPORTS
    for package in packages:
        imported_package = importlib.import_module(package)
        logger.info("Import '%s' found at '%s'", package, imported_package.__file__)


def _install_dependencies(dependencies, target_dir=PROFILE_LIBRARY_DIR):
    for dependency in dependencies:
        print(sys.path)
        print("Installing '%s' into %s" % (dependency.name, target_dir))
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--find-links",
                str(our_dir / "external-dependencies"),
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
    return missing


def generate_constraints_txt():
    constraints_file = our_dir / "constraints.txt"
    lines = [(dependency.name + dependency.constraint) for dependency in DEPENDENCIES]
    lines.append("")
    constraints_file.write_text("\n".join(lines))
    print("Wrote constraints to %s" % constraints_file)


if __name__ == "__main__":
    generate_constraints_txt()
