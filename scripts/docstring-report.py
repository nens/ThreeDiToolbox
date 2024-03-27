"""Helper script for generating compact docstring coverage report.

The ``docstr-coverage`` package has a quite verbose output. This script
mimicks the one-line-per-file output of ``coverage.py``.

It also sets some defaults and does more elaborate filtering/exclusion than
currently possible with the basic ``docstr-coverage`` package.

"""
from docstr_coverage import coverage

import glob


FORMAT = "%-74s %5s  %5s  %3d%%"


def main():
    """Call docstr-coverage's main method with our preferences.

    - Custom filtering.

    - Some defaults (like "don't worry about __init__() methods").

    - Custom one-line-per file output.

    """
    filenames = glob.glob("**/*.py", recursive=True)
    filenames = [
        filename
        for filename in filenames
        if not (
            filename.startswith("external")
            or filename.startswith("help")
            or filename.startswith("deps")
            or "/test" in filename
        )
    ]
    file_results, total_results = coverage.get_docstring_coverage(
        filenames,
        skip_magic=True,
        skip_file_docstring=False,
        skip_init=True,
        skip_class_def=False,
        verbose=0,
    )

    for filename in filenames:
        result = file_results.get(filename)
        print(
            FORMAT
            % (
                filename,
                result["needed_count"],
                result["missing_count"],
                result["coverage"],
            )
        )

    print(
        FORMAT
        % (
            "TOTAL",
            total_results["needed_count"],
            total_results["missing_count"],
            total_results["coverage"],
        )
    )


if __name__ == "__main__":
    main()
