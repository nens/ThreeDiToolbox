from pathlib import Path
from threedi_results_analysis import dependencies
from threedi_results_analysis.dependencies import Dependency

import mock
import os
import pytest


available_dependency = dependencies.Dependency("numpy", "numpy", "", False)
dependency_with_wrong_version = dependencies.Dependency("numpy", "numpy", "==1972", False)
missing_dependency = dependencies.Dependency("reinout", "reinout", "", False)


def test_check_importability():
    # Everything should just be importable.
    dependencies.check_importability()


def test_check_presence_1():
    dependencys_that_are_present = [available_dependency]
    dependencies._check_presence(dependencys_that_are_present)


def test_check_presence_2():
    dependencies_some_missing = [available_dependency, missing_dependency]
    missing = dependencies._check_presence(dependencies_some_missing)
    assert missing == [
        missing_dependency
    ], "reinout is not installed, so it should be missing"


def test_check_presence_3():
    missing = dependencies._check_presence([dependency_with_wrong_version])
    assert missing == [
        dependency_with_wrong_version
    ], "numpy is installed, but not with the requested version"


def test_ensure_everything_installed_smoke():
    # Should just run without errors as we have a correct test setup.
    dependencies.ensure_everything_installed()


def test_install_dependencies(tmpdir):
    small_dependencies = [
        dependency
        for dependency in dependencies.DEPENDENCIES
        if dependency.name == "threedi-schema"
    ]
    dependencies._install_dependencies(small_dependencies, target_dir=tmpdir)
    installed_directory = Path(tmpdir) / "threedi_schema"
    assert installed_directory.exists()
    # Cleanup
    dependencies.ensure_everything_installed()


def test_uninstall_dependency(tmpdir, monkeypatch):
    python_path = os.getenv("PYTHONPATH", "")
    new_python_path = f"{python_path}:{tmpdir}"
    monkeypatch.setenv("PYTHONPATH", new_python_path)

    small_dependencies = [
        Dependency("threedi-modelchecker", "threedi_modelchecker", ">=1.0.0", False)
    ]
    dependencies._install_dependencies(
        small_dependencies, target_dir=tmpdir
    )
    dependencies._uninstall_dependency(small_dependencies[0])
    for directory in os.listdir(tmpdir):
        assert "threedi_modelchecker" not in directory


def test_install_dependencies_with_error(tmpdir):
    wrong_dependencies = [missing_dependency]
    with pytest.raises(RuntimeError):
        dependencies._install_dependencies(wrong_dependencies, target_dir=tmpdir)


def test_generate_constraints_txt(tmpdir):
    target_dir = Path(tmpdir)
    dependencies.generate_constraints_txt(target_dir=target_dir)
    generated_file = target_dir / "constraints.txt"
    assert "threedi-schema" in generated_file.read_text()


def test_dependencies_target_dir_smoke():
    assert "python" in str(dependencies._dependencies_target_dir())


def test_dependencies_target_dir_somewhere_else():
    # The dependencies folder is a subdir 'deps' of tmpdir
    plugin_folder = Path("/some/profile/dir")
    result = str(dependencies._dependencies_target_dir(our_dir=plugin_folder))
    assert str(plugin_folder) + '/deps' == result


def test_get_python_interpreter_linux():
    python_interpreter = dependencies._get_python_interpreter()
    directory, filename = os.path.split(python_interpreter)
    assert "python3" in filename


def test_get_python_interpreter_windows():
    with mock.patch(
        "sys.executable", "C:/Program Files/QGIS 3.4/bin/qgis-ltr-bin.exe"
    ), mock.patch("os.path.exists", return_value=True):
        python_interpreter = dependencies._get_python_interpreter()
        directory, filename = os.path.split(python_interpreter)
        assert filename == "python3.exe"


def test_get_python_interpreter_unknown():
    with mock.patch("sys.executable", "/usr/bin/beer"):
        with pytest.raises(EnvironmentError):
            dependencies._get_python_interpreter()


def test_ensure_prerequisite_is_installed1():
    # Normally, pip is installed.
    dependencies._ensure_prerequisite_is_installed()


def test_ensure_prerequisite_is_installed2():
    with pytest.raises(RuntimeError):
        # "prerequisite=" is there only for easy testing, the default is "pip")
        dependencies._ensure_prerequisite_is_installed(prerequisite="reinout")
