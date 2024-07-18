import sys
import importlib.util
from subprocess import CalledProcessError, run
from pkg_resources import get_distribution, DistributionNotFound, RequirementParseError


def install_package(package_name, version=None):
    package_to_install = package_name if not version else f"{package_name}{version}"
    try:
        run([sys.executable, '-m', 'pip', 'install', package_to_install], check=True)
    except CalledProcessError as e:
        print(f"Error installing {package_name}: {e}")
        sys.exit(1)


def read_dependencies_file(file_path):
    spec = importlib.util.spec_from_file_location("dependencies", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DEPENDENCIES


def install_dependencies_from_file(file_path):
    dependencies = read_dependencies_file(file_path)
    for dep in dependencies:
        if dep.name in ['threedi-modelchecker', 'threedigrid-builder']:
            install_package(dep.package, dep.constraint)


def get_dependency_version(package_name, dependency_name):
    try:
        dist = get_distribution(package_name)
        requires = dist.requires()
        for req in requires:
            if req.name == dependency_name:
                return req.specs[0][1] if req.specs else None
    except (DistributionNotFound, RequirementParseError) as e:
        print(f"Error getting {dependency_name} version for {package_name}: {e}")
        sys.exit(1)
    return None


def check_dependency_conflicts():
    dependencies_file_path = 'dependencies.py'
    install_dependencies_from_file(dependencies_file_path)

    modelchecker_schema_version = get_dependency_version('threedi-modelchecker', 'threedi-schema')
    gridbuilder_schema_version = get_dependency_version('threedigrid-builder', 'threedi-schema')

    if not modelchecker_schema_version or not gridbuilder_schema_version:
        print("Could not determine the required versions of threedi-schema.")
        sys.exit(1)

    print(f"Model Checker Schema Version: {modelchecker_schema_version}")
    print(f"Grid Builder Schema Version: {gridbuilder_schema_version}")

    modelchecker_schema_minor_version = modelchecker_schema_version[:2]
    gridbuilder_schema_minor_version = gridbuilder_schema_version[:2]

    if modelchecker_schema_minor_version != gridbuilder_schema_minor_version:
        print(f"Version conflict detected: threedi-modelchecker requires threedi-schema=={modelchecker_schema_version}, but threedigrid-builder requires threedi-schema=={gridbuilder_schema_version}")
        sys.exit(1)

    print("No version conflicts detected.")
    sys.exit(0)


def main():
    check_dependency_conflicts()


if __name__ == "__main__":
    main()
