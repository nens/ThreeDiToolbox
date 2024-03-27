from threedi_results_analysis import PLUGIN_DIR


DOC_SOURCE_DIR = PLUGIN_DIR / "doc" / "source"


def generate_subdir_readme_symlinks():
    """Create a symlink for every README in a direct subdirectory.

    Note: the symlinks to the main README and CHANGELOG and so are done by
    hand.

    """
    for readme in PLUGIN_DIR.glob("*/README.rst"):
        subdir_name = readme.parent.name
        target_name = f"linked_{subdir_name}_readme.rst"
        target = DOC_SOURCE_DIR / target_name
        # Relative: an absolute symlink (in the docker) doesn't work locally.
        relative_symlink = f"../../{subdir_name}/README.rst"
        if not target.exists():
            target.symlink_to(relative_symlink)
            print(f"Added symlink {target_name} to {relative_symlink}")


def generate_reference_docs():
    """Generated autodoc files for the relevant directories.

    We look for ``__init__.py`` files in subdirs and sub-subdirs and generate
    a ``.rst`` file with ``.. automodule::`` statements per directory.

    We ignore the ``__init__.py`` files as they should really be empty and, if
    not, their contents are probably imported and could result in
    duplicates. Of course, we also ignore the test files.

    """
    directories = []
    # "dunder" is python-speak for double-underscore.
    for dunder_init in PLUGIN_DIR.glob("*/__init__.py"):
        subdir = dunder_init.parent
        directories.append(subdir)
        for dunder_init in subdir.glob("*/__init__.py"):
            subsubdir = dunder_init.parent
            directories.append(subsubdir)

    directories.sort()
    for directory in directories:
        python_files = sorted(
            [str(f.relative_to(PLUGIN_DIR)) for f in directory.glob("*.py")]
        )
        python_files = [
            python_file
            for python_file in python_files
            if not ("test" in python_file or "__init__" in python_file)
        ]
        if not python_files:
            continue

        relative_directory_name = str(directory.relative_to(PLUGIN_DIR))
        reference_filename = "reference_%s.rst" % relative_directory_name.replace(
            "/", "_"
        )
        content = []
        content.append("%s/" % relative_directory_name)
        content.append("=" * 100)
        content.append("")
        # TODO: link to readme, if available?
        for python_file in python_files:
            relative_module_name = python_file.replace(".py", "").replace("/", ".")
            content.append(relative_module_name)
            content.append("-" * 100)
            content.append("")
            content.append(".. automodule:: ThreeDiToolbox.%s" % relative_module_name)
            content.append("")

        rendered_content = "\n".join(content)
        reference_file = DOC_SOURCE_DIR / "automatic_references" / reference_filename
        reference_file.write_text(rendered_content)


def main():
    generate_subdir_readme_symlinks()
    generate_reference_docs()


if __name__ == "__main__":
    main()
