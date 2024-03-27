Documentation howto
===================

To build the documentation, run ``make html``::

  docker-compose run qgis-desktop make html

This command also calls ``scripts/generate-reference-docs.py`` that handles
the READMEs and the autodoc files (see the next section).


Structure
---------

The ``doc/source/`` directory contains the main ``index.rst``. The TOC (=table
of contents) entries in here MUST point at all the available documentation
files.

Also in here: generic documentation (like this page).

Documentation for tools and so should be done in a ``README.rst`` in the
tool's main directory (so not in a sub-sub directory). The script mentioned
above automatically generates a symlink that you can then point at in the
``index.rst``.

For every directory and subdirectory with python files, an "autodoc" file is
generated (by abovementioned script) in
``doc/source/automatic_references/``. These files are automatically included
in the TOC. Note that the test files and the ``__init__.py`` are skipped. If a
directory is removed or renamed, you probably have to remove a file in here,
too.

So basically:

- Documentation per tool in its own directory's ``README.rst``.

- Generic documentation in ``doc/source/``.


Documentation syntax
--------------------

Some handy sphinx links:

- https://www.sphinx-doc.org/en/master/markup/inline.html

- https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html

- https://www.sphinx-doc.org/en/master/domains.html#cross-referencing-python-objects
  for pointing at functions/modules/methods/classes. And at documentation files.

- https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
  for google-style argument lists in docstrings. This is nicer than the
  older ``:param:`` style.

Some hints:

- You can add a short docstring to a variable or constant with ``#:`` like this::

    #: Handy constant for building relative paths.
    PLUGIN_DIR = Path(__file__).parent

- Refer to it (:py:data:`threedi_results_analysis.PLUGIN_DIR`) like this::

    :py:data:`threedi_results_analysis.PLUGIN_DIR`

- From the regular documentation (so: mostly your ``README.rst`` files), try
  to refer to the implementation details to allow going back and forth between
  them. See `the sphinx documentation
  <https://www.sphinx-doc.org/en/master/domains.html#cross-referencing-python-objects>`_.
  For example, :py:class:`threedi_results_analysis.utils.qlogging.QgisLogHandler` is
  generated with this::

    :py:class:`threedi_results_analysis.utils.qlogging.QgisLogHandler`

- Point at documentation files (for example :doc:`documentation`) like this::

    :doc:`documentation`

Don't overdo it, because it can get quite tedious to point at everything. And
it takes a lot of time. But in some cases a direct link is the best
documentation.

A note on heading levels: inside a file, use ``======`` for the main title and
``------`` for subheadings. Those two levels are enough: we're not writing a
200 page PhD thesis :-)
