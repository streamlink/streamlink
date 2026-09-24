Developing
==========

Setup
-----

Setting up the repository
^^^^^^^^^^^^^^^^^^^^^^^^^

In order to start working on Streamlink, you must first install the latest stable version of ``git``, optionally fork the
repository on GitHub onto your account if you want to submit changes in a pull request, and then locally clone the repository.

.. code-block:: bash

    mkdir streamlink
    cd streamlink
    git clone --origin=upstream 'https://github.com/streamlink/streamlink.git' .
    git remote add fork 'git@github.com:<YOUR-USERNAME>/streamlink.git'
    git remote -v
    git fetch --all

When submitting a pull request, commit and push your changes onto a different branch.

.. code-block:: bash

    git checkout master
    git pull upstream master
    git checkout -b new/feature/or/bugfix/branch
    git add ./foo
    git commit
    git push fork new/feature/or/bugfix/branch


Setting up a new environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before starting any work on the project, a virtual environment must be set up which is isolated from
the Python environment of the host system. This ensures that development can be done in a clean space which is free of version
conflicts and other unrelated packages.

First, make sure that you have the latest stable versions of Python and `uv`_ installed.
Depending on the host system and developer preferences, `uv`_ may be used to install Python itself (see its own docs).

`uv`_ is not a strict requirement. Other Python package managers like `pip`_ for example can be used,
but since Streamlink pins its dependencies in a `uv`_ lock file, dependency issues can be fully avoided this way.

.. code-block:: bash

    python --version
    uv --version

Now create a virtual environment by syncing all dependencies from Streamlink's ``uv.lock`` dependency lock file:

.. code-block:: bash

    uv sync --all-extras --all-groups

Alternatively, a custom, self-managed Python environment can be set up by using Python's own `venv`_ and then activating it:

.. code-block:: bash

    # replace ~/venvs/streamlink with your path of choice and give it a proper name
    python -m venv ~/venvs/streamlink

    # POSIX compliant shells on non-Windows systems
    source ~/venvs/streamlink/bin/activate
    # non-POSIX shells have their own activation script, e.g. FISH
    source ~/venvs/streamlink/bin/activate.fish
    # on Windows, activation scripts are located in the Scripts/ subdirectory instead of bin/
    ~\venvs\streamlink\Scripts\Activate.ps1

    # sync to the active environment instead (--active)
    uv sync --active --all-extras --all-groups

Verify that Streamlink is working and that all dependencies have been installed:

.. code-block:: bash

    streamlink --loglevel=debug

Please remember to always re-sync the environment when fetching/pulling new commits or when switching branches.

.. _uv: https://docs.astral.sh/uv/
.. _pip: https://pip.pypa.io/en/stable/
.. _venv: https://docs.python.org/3/library/venv.html


Validating changes
------------------

Before submitting a pull request, please run tests, perform code linting and build the documentation on your system first,
to see if your changes contain any mistakes or errors. This will be done automatically for each pull request on each change,
but performing these checks locally avoids unnecessary build failures.

The ``uv run`` command prefix will ensure that all dependency requirements are met before running the actual command.
In an activated custom environment, the ``uv run`` command wrapper must be removed, or `uv`_ will use its own environment.

.. code-block:: bash

    # run automated tests
    uv run pytest
    # or just run a subset of all tests
    uv run pytest path/to/test-file.py::TestClassName::test_method_name ...

    # check code for linting errors
    uv run ruff check
    # check code for formatting errors
    uv run ruff format --diff
    # check code for typing errors
    uv run ty check
    uv run mypy

    # build the documentation
    uv run make --directory=docs clean html

    # check the documentation
    python -m http.server 8000 --bind '127.0.0.1' --directory 'docs/_build/html/'
    "${BROWSER}" http://127.0.0.1:8000/


Code style
----------

Streamlink uses `Ruff`_ as primary code `linting <Ruff-linter_>`_ and `formatting <Ruff-formatter_>`_ tool.

The project aims to use best practices for achieving great code readability with minimal git diffs,
as detailed in :pep:`8` and implemented in related linting and formatting tools, such as `Black`_.

For detailed linting and formatting configurations specific to Streamlink, please have a look at `pyproject.toml`_.

It might be helpful to new plugin authors to pick a small and recently modified existing plugin to use as an initial
template from which to work. If care is taken to preserve existing blank lines during modification, the main plugin
structure should be compliant-ready for `linting <Validating changes_>`_.

.. _Ruff: https://github.com/astral-sh/ruff
.. _Ruff-linter: https://docs.astral.sh/ruff/linter/
.. _Ruff-formatter: https://docs.astral.sh/ruff/formatter/
.. _Black: https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html
.. _pyproject.toml: https://github.com/streamlink/streamlink/blob/master/pyproject.toml


Git commit style
----------------

To improve git history and changelog legibility, Streamlink enforces a specific commit message format.
It is a variation of `conventional commits`_ using component/package prefixes instead of conventional types and scopes.

Commit messages must begin with a lowercase prefix, followed by a colon and a space, and end with a subject description.
The target line length is 50 characters, with a hard maximum of 72 characters.

The prefix must be a dot-separated pseudo-Python-import-path of the modified file path,
ignoring the ``streamlink`` namespace (while renaming ``streamlink_cli`` to ``cli``).
Non-code changes should use an equivalent pseudo-path.
If not applicable, standard conventional commit types must be used instead.
If a commit affects multiple components, the primary one should be chosen, or a second prefix should be added
using the same separator format.

Subject descriptions must start with a lowercase imperative verb (e.g. "add", "remove", "refactor")
communicating the nature of the change, and end without punctuation.

For example:

.. code-block:: text

    session.http: fix set_interface on macOS
    plugins.twitch: switch to usher v2 endpoints
    ci.github: run preview-builds on uv.lock updates

Optional message bodies must be separated from the subject by a blank line, with lines wrapped at 72 characters.
Markdown formatting is supported. Standardized footers (e.g. ``Co-Authored-By: name <email-address>``)
may be included at the end of the body.

``@`` user-references must not be included in commit messages.

.. _conventional commits: https://www.conventionalcommits.org/

.. Commit subject format:
   All commit message subjects must end with a formatting delimiter mark (U+200B) for downstream git log parser compatibility.


Plugins
-------

Adding plugins
^^^^^^^^^^^^^^

1. Implement the plugin in ``src/streamlink/plugins/pluginname.py``, similar to already existing plugins.

   Check the git log for recently added or modified plugins to help you get an overview of what's needed to properly implement
   a plugin. A complete guide is currently not available.

   Each plugin class requires at least one ``pluginmatcher`` decorator which defines the URL regex, matching priority
   and an optional name.

   Plugins need to implement the :meth:`_get_streams() <streamlink.plugin.Plugin._get_streams>` method which must return
   ``Mapping[str,Stream] | Iterable[Tuple[str,Stream]] | Iterator[Tuple[str,Stream]] | None``.
   ``Stream`` is the base class of :class:`HTTPStream <streamlink.stream.HTTPStream>`,
   :class:`HLSStream <streamlink.stream.HLSStream>` and :class:`DASHStream <streamlink.stream.DASHStream>`.

   Plugins also require metadata which will be read when building the documentation. This metadata contains information about
   the plugin, e.g. which URLs it accepts, which kind of streams it returns, whether content is region-locked, or if any kind of
   account or subscription is needed for watching the content, etc. This metadata needs to be set as a header comment at
   the beginning of the plugin file, in the following format (order of items is important):

   .. code-block:: python

      """
      $description A brief description of the website, streaming service, etc.
      $url A URL which matches the plugin. No http:// or https:// scheme prefixes allowed.
      $url Multiple URLs can be set. Duplicates are not allowed.
      $type The type of content. Needs to be either "live", "vod", or "live, vod", without quotes.
      $region A comma-separated list of countries if region-lock applies. (optional)
      $account A brief note about account or subscription requirements. (optional)
      $notes Further short notes that may be useful. (optional)
      """

2. Add at least tests for the URL regex matching in ``tests/plugins/test_pluginname.py``.

   To do so, import the ``PluginCanHandleUrl`` test base class from ``tests.plugins``, subclass it with a proper name, add
   the ``__plugin__`` class attribute and add all URLs required for testing the plugin matchers to the ``should_match`` list.

   The optional ``should_not_match`` negative matching list should only contain URLs which the plugin should actively not match,
   which means generic negative-matches are not allowed here, as they will already get added by the plugin test configuration.

   In addition to the positive matching list, ``should_match_groups`` is an optional list for testing capture groups values for
   given URL inputs. It's a list of tuples where the first tuple item is a URL and the second item either a dictionary of regex
   capture group names and values (excluding ``None`` values), or a tuple of unnamed capture group values. URLs from the
   ``should_match_groups`` list automatically get added to ``should_match`` and don't need to be added twice.

   If the plugin defines named matchers, then URLs in the test fixtures must be tuples of the matcher name and the URL itself.
   Unnamed matchers must not match named URL test fixtures and vice versa.

   Every plugin matcher must have at least one URL test fixture that matches.

   .. code-block:: python

      from streamlink.plugins.pluginfile import MyPluginClassName
      from tests.plugins import PluginCanHandleUrl


      class TestPluginCanHandleUrlMyPluginClassName(PluginCanHandleUrl):
          __plugin__ = MyPluginClassName

          should_match = [
              "https://host/path/one",
              ("specific-path-matcher", "https://host/path/two"),
          ]

          should_match_groups = [
              ("https://host/stream/123", {"stream": "123"}),
              ("https://host/stream/456/foo", ("456", "foo")),
              (("user-matcher", "https://host/user/one"), {"user": "one"}),
              (("user-matcher", "https://host/user/two"), ("two", None)),
              (("user-matcher", "https://host/user/two/foo"), ("two", "foo")),
          ]

          should_not_match = [
              "https://host/path/three",
          ]

Removing plugins
^^^^^^^^^^^^^^^^

1. Remove the plugin file from ``src/streamlink/plugins/`` and the test file from ``tests/plugins/``
