"""Handle dependencies: installation and checking/logging.

See :doc:`linked_external-dependencies_readme`
(``external-dependencies/README.rst``) for a full explanation of the
dependency handling.

``python3 dependencies.py`` runs ``generate_constraints_txt()``: it generates
``constraints.txt``.

:py:func:`ensure_everything_installed()` checks if :py:data:`DEPENDENCIES` are
installed and installs them if needed.

:py:func:`check_importability()` double-checks if everything is importable. It also
logs the locations.

Note that we use *logging* in ``check_importability()`` as we want to have the
result in the logfile. The rest of the module uses ``print()`` statements
because it gets executed before any logging has been configured.

As we're called directly from ``__init__.py``, the imports should be
resticted. No qgis message boxes and so!

"""
from collections import namedtuple
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QProgressBar
from PyQt5.QtWidgets import QProgressDialog

import importlib
import logging
import os
import pkg_resources
import platform
import shutil
import subprocess
import sys


Dependency = namedtuple("Dependency", ["name", "package", "constraint"])

#: List of expected dependencies.
DEPENDENCIES = [
    Dependency("SQLAlchemy", "sqlalchemy", "<1.4"),
    Dependency("GeoAlchemy2", "geoalchemy2", "==0.10.2"),
    Dependency("lizard-connector", "lizard_connector", "==0.7.3"),
    Dependency("pyqtgraph", "pyqtgraph", ">=0.11.1,<0.12"),
    Dependency("threedigrid", "threedigrid", ">=1.2.3"),
    Dependency("cached-property", "cached_property", ""),
    Dependency("threedi-modelchecker", "threedi_modelchecker", ">=0.27.1"),
    Dependency("threedidepth", "threedidepth", "==0.4"),
    Dependency("click", "click", ">=8.0"),
    Dependency("alembic", "alembic", "==1.6.5"),
    Dependency("Mako", "mako", ""),
    Dependency("netCDF4", "netCDF4", ""),
    Dependency("cftime", "cftime", ""),
    Dependency("packaging", "packaging", ""),
    Dependency("python-editor", "editor", ">=0.3"),  # dep of alembic
    Dependency(
        "colorama", "colorama", ""
    ),  # dep of click and threedi-modelchecker (windows)
    Dependency("networkx", "networkx", ""),
]

# Dependencies that contain compiled extensions for windows platform
WINDOWS_PLATFORM_DEPENDENCIES = [
    Dependency("scipy", "scipy", "==1.6.2"),
]
H5PY_DEPENDENCY = Dependency("h5py", "h5py", "==2.10.0")
SUPPORTED_HDF5_VERSIONS = ["1.10.7"]

# If you add a dependency, also adjust external-dependencies/populate.sh
INTERESTING_IMPORTS = ["numpy", "osgeo", "pip", "setuptools"]

OUR_DIR = Path(__file__).parent

logger = logging.getLogger(__name__)


def create_progress_dialog(progress):
    dialog = QProgressDialog()
    dialog.setWindowTitle("3Di Toolbox install progress")
    dialog.setLabelText("Installing external dependencies")
    dialog.setWindowFlags(Qt.WindowStaysOnTopHint)
    bar = QProgressBar(dialog)
    bar.setTextVisible(True)
    bar.setValue(progress)
    bar.setValue(0)
    bar.setMaximum(100)
    dialog.setBar(bar)
    dialog.setMinimumWidth(500)
    dialog.update()
    dialog.setCancelButton(None)
    dialog.show()
    return dialog, bar


def ensure_everything_installed():
    """Check if DEPENDENCIES are installed and install them if missing."""

    _remove_old_distributions(DEPENDENCIES, _prev_dependencies_target_dir())

    # If required, create deps folder and prepend to the path
    target_dir = _dependencies_target_dir(create=True)
    if str(target_dir) not in sys.path:
        print(f"Prepending {target_dir} to sys.path")
        sys.path.insert(0, str(target_dir))

    _refresh_python_import_mechanism()

    profile_python_names = [item.name for item in _dependencies_target_dir().iterdir()]
    print("Contents of our deps dir:\n    %s" % "\n    ".join(profile_python_names))

    print("sys.path:")
    for directory in sys.path:
        print("  - %s" % directory)

    _ensure_prerequisite_is_installed()
    missing = _check_presence(DEPENDENCIES)
    if platform.system() == "Windows":
        missing += _check_presence(WINDOWS_PLATFORM_DEPENDENCIES)
        _ensure_h5py_installed()

    if missing:
        print("Missing dependencies:")
        for deps in missing:
            print(deps.name)

        restart_required = False
        try:
            _install_dependencies(missing, target_dir=target_dir)
        except RuntimeError:
            # In case some libraries are already imported, we cannot uninstall
            # because QGIS acquires a lock on dll/pyd-files. Therefore
            # we need to restart Qgis.
            restart_required = True
            pass

        restart_marker = Path(target_dir / "restarted.marker")

        if restart_required or not restart_marker.exists():
            if _is_windows():
                # We always want to restart when deps are missing
                from ThreeDiToolbox.utils.user_messages import pop_up_info

                pop_up_info(
                    "Please restart QGIS to complete the installation process of "
                    "ThreediToolbox.",
                    title="Restart required",
                )
                restart_marker.touch()

        # Always update the import mechanism
        _refresh_python_import_mechanism()

    else:
        print("Dependencies up to date")


def _ensure_h5py_installed():
    """
    On Windows Qgis comes with a hdf5 version installed.
    This plugin uses the h5py python package, which is built against a specific version
    of HDF5. The Qgis HDF5 version and the HDF5 version of the h5py package must be the
    same, otherwise it will not work. In the external-dependencies folder we supply a
    Windows version of h5py built using HDF5 1.10.7. On pypi there is no h5py 2.10.0 package available
    built with Python 3.9 and HDF5 1.10.7. We need creat such wheel ourselves.

    The following situations can occur:

                           | QGIS HDF5 = 1.10.7  | QGIS HDF5 != 1.10.7
    -----------------------|---------------------|---------------
    h5py build with 1.10.7 | A: Good             | B: Qgis crash

    The different situations are marked A and B in the table above.

    In situations A everything is good and the plugin can be loaded without any
    problems.

    Situations B occur when a user upgrades/downgrades their Qgis version when
    the ThreediToolbox is already installed with a specific version of h5py.
    In these cases we also need to upgrade/downgrade the h5py version installed with
    ThreediToolbox.

    In situations B Qgis will crash when trying to import h5py.

    We use the H5pyMarker to mark the installed h5py version. This is because we cannot check the version
    by importing h5py, as Qgis will crash if the HDF5 and h5py binaries do not match.
    """
    h5py_dependency = Dependency("h5py", "h5py", "==2.10.0")
    hdf5_version = (
        "1.10.7"  # there is only one version of HDF5 available in the QGIS installer
    )
    h5py_missing = _check_presence([h5py_dependency])
    marker_version = H5pyMarker.version()
    if h5py_missing:
        _install_h5py(hdf5_version)

    if hdf5_version == "1.10.7":
        if marker_version == "1.10.7":
            # Do nothing
            pass
        else:
            _install_h5py(hdf5_version)


def _install_h5py(hdf5_version: str):
    if hdf5_version not in SUPPORTED_HDF5_VERSIONS:
        # raise an error because we cannot continue
        message = (
            f"Unsupported HDF5 version: {hdf5_version}. "
            f"The following HDF5 versions are supported: {SUPPORTED_HDF5_VERSIONS}"
        )
        raise RuntimeError(message)

    # In case the (old) h5py library is already imported, we cannot uninstall
    # h5py because the windows acquires a lock on the *.dll-files. Therefore
    # we need to restart Qgis.
    # _uninstall_dependency(H5PY_DEPENDENCY)
    try:
        _install_dependencies([H5PY_DEPENDENCY], target_dir=_dependencies_target_dir())
    except RuntimeError:
        from ThreeDiToolbox.utils.user_messages import pop_up_info

        pop_up_info(
            "Please restart QGIS to complete the installation process of "
            "ThreediToolbox.",
            title="Restart required",
        )
        return
    H5pyMarker.create(hdf5_version)


class H5pyMarker:
    """Marker indicating with which HDF5 binaries the h5py is installed.

    Currently, there is 1 supported HDF5 version:
    - 1.10.7: use h5py from the external-dependencies folder in this repo
    """

    H5PY_MARKER = OUR_DIR / ".h5py_marker"

    @classmethod
    def version(cls) -> str:
        if cls.H5PY_MARKER.exists():
            with open(cls.H5PY_MARKER, "r") as marker:
                version = marker.readline()
            return version
        else:
            return ""

    @classmethod
    def create(cls, version: str):
        with open(cls.H5PY_MARKER, "w") as marker:
            marker.write(version)

    @classmethod
    def remove(cls):
        cls.H5PY_MARKER.unlink()


def _ensure_prerequisite_is_installed(prerequisite="pip"):
    """Check the basics: pip.

    People using OSGEO custom installs sometimes exclude those
    dependencies. Our installation scripts fail, then, because of the missing
    'pip'.

    """
    try:
        importlib.import_module(prerequisite)
    except Exception as e:
        msg = (
            "%s. 'pip', which we need, is missing. It is normally included with "
            "python. You are *probably* using a custom minimal OSGEO release. "
            "Please re-install with 'pip' included."
        ) % e
        print(msg)
        raise RuntimeError(msg)


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


def check_importability():
    """Check if the dependendies are importable and log the locations.

    If something is not importable, which should not happen, it raises an
    ImportError automatically. Which is exactly what we want, because we
    cannot continue.

    """
    packages = [dependency.package for dependency in DEPENDENCIES]
    packages += INTERESTING_IMPORTS
    logger.info("sys.path:\n    %s", "\n    ".join(sys.path))
    deps_in_target_dir = [item.name for item in _dependencies_target_dir().iterdir()]
    logger.info(
        "Contents of our dependency dir:\n    %s",
        "\n    ".join(deps_in_target_dir),
    )
    for package in packages:
        imported_package = importlib.import_module(package)
        logger.info(
            "Import '%s' found at \n    '%s'", package, imported_package.__file__
        )


def _uninstall_dependency(dependency):
    print("Trying to uninstalling dependency %s" % dependency.name)
    python_interpreter = _get_python_interpreter()
    startupinfo = None
    if _is_windows():
        startupinfo = subprocess.STARTUPINFO()
        # Prevents terminal screens from popping up
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    process = subprocess.Popen(
        [
            python_interpreter,
            "-m",
            "pip",
            "uninstall",
            "--yes",
            (dependency.name),
        ],
        universal_newlines=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        startupinfo=startupinfo,
    )
    # The input/output/error stream handling is a bit involved, but it is
    # necessary because of a python bug on windows 7, see
    # https://bugs.python.org/issue3905 .
    i, o, e = (process.stdin, process.stdout, process.stderr)
    i.close()
    result = o.read() + e.read()
    o.close()
    e.close()
    print(result)
    exit_code = process.wait()
    if exit_code:
        print("Uninstalling %s failed" % dependency.name)


def _install_dependencies(dependencies, target_dir):
    python_interpreter = _get_python_interpreter()
    base_command = [
        python_interpreter,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--no-deps",
        "--find-links",
        str(OUR_DIR / "external-dependencies"),
        "--no-index",
        "--target",
        str(target_dir),
    ]

    dialog = None
    bar = None
    startupinfo = None
    if _is_windows():
        dialog, bar = create_progress_dialog(0)
        QApplication.processEvents()
        startupinfo = subprocess.STARTUPINFO()
        # Prevents terminal screens from popping up
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    for count, dependency in enumerate(dependencies):
        _uninstall_dependency(dependency)
        print("Installing '%s' into %s" % (dependency.name, target_dir))
        command = base_command + [dependency.name + dependency.constraint]

        if dialog:
            dialog.setLabelText(f"Installing {dependency.name}")

        process = subprocess.Popen(
            command,
            universal_newlines=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
        )
        # The input/output/error stream handling is a bit involved, but it is
        # necessary because of a python bug on windows 7, see
        # https://bugs.python.org/issue3905 .
        i, o, e = (process.stdin, process.stdout, process.stderr)
        i.close()
        result = o.read() + e.read()
        o.close()
        e.close()
        print(result)
        exit_code = process.wait()
        if exit_code:
            if dialog:
                dialog.close()
                QApplication.processEvents()
            raise RuntimeError(
                f"Installing {dependency.name} failed ({exit_code}) ({result})"
            )
        print("Installed %s into %s" % (dependency.name, target_dir))
        if dependency.package in sys.modules:
            print("Unloading old %s module" % dependency.package)
            del sys.modules[dependency.package]
            # check_importability() will be called soon, which will import them again.
            # By removing them from sys.modules, we prevent older versions from
            # sticking around.

        if bar:
            bar.setValue((count / len(dependencies)) * 100)
            bar.update()
            QApplication.processEvents()

    if dialog:
        dialog.close()


def _is_windows():
    """Return whether we are starting from QGIS on Windows."""
    executable = sys.executable
    _, filename = os.path.split(executable)
    if "python3" in filename.lower():
        return False
    elif "qgis" in filename.lower():
        return True
    else:
        raise EnvironmentError("Unexpected value for sys.executable: %s" % executable)


def _get_python_interpreter():
    """Return the path to the python3 interpreter.

    Under linux sys.executable is set to the python3 interpreter used by Qgis.
    However, under Windows/Mac this is not the case and sys.executable refers to the
    Qgis start-up script.
    """
    interpreter = None
    executable = sys.executable
    directory, _ = os.path.split(executable)
    if _is_windows():
        interpreter = os.path.join(directory, "python3.exe")
    else:
        interpreter = executable

    assert os.path.exists(interpreter)  # safety check
    return interpreter


def _check_presence(dependencies):
    """Check if all dependencies are present. Return missing dependencies."""
    missing = []
    for dependency in dependencies:
        requirement = dependency.name + dependency.constraint
        print("Checking presence of %s..." % requirement)
        try:
            result = pkg_resources.require(requirement)
            print("Requirement %s found: %s" % (requirement, result))
        except pkg_resources.DistributionNotFound as e:
            print(
                "Dependency '%s' (%s) not found (%s)"
                % (dependency.name, dependency.constraint, str(e))
            )
            missing.append(dependency)
        except pkg_resources.VersionConflict:
            print(
                "Dependency '%s' (%s) has the wrong version"
                % (dependency.name, dependency.constraint)
            )
            missing.append(dependency)
    return missing


def _refresh_python_import_mechanism():
    """Refresh the import mechanism.

    This is required when deps are dynamically installed/removed. The modules
    'importlib' and 'pkg_resources' need to update their internal data structures.
    """
    # This function should be called if any modules are created/installed while your
    # program is running to guarantee all finders will notice the new module’s existence.
    importlib.invalidate_caches()

    # https://stackoverflow.com/questions/58612272/pkg-resources-get-distributionmymodule-version-not-updated-after-reload
    # Apparantely pkg_resources needs to be reloaded to be up-to-date with newly installed packages
    importlib.reload(pkg_resources)


def generate_constraints_txt(target_dir=OUR_DIR):
    """Called from the ``__main__`` to generate ``constraints.txt``."""
    constraints_file = target_dir / "constraints.txt"
    lines = ["# Generated by dependencies.py"]
    lines += [(dependency.name + dependency.constraint) for dependency in DEPENDENCIES]
    lines.append("")
    constraints_file.write_text("\n".join(lines))
    print("Wrote constraints to %s" % constraints_file)


if __name__ == "__main__":  # pragma: no cover
    generate_constraints_txt()
