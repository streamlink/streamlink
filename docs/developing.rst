Developing
==========

Setup
-----

Setting up the repository
^^^^^^^^^^^^^^^^^^^^^^^^^

In order to start working on Streamlink, you must first install the latest stable version of ``git``, optionally fork the
repository on Github onto your account if you want to submit changes in a pull request, and then locally clone the repository.

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

While working on any kind of python-based project, it is usually best to do this in a virtual environment which is isolated from
the Python environment of the host system. This ensures that development can be done in a clean space which is free of version
conflicts and other unrelated packages.

First, make sure that you have the latest stable versions of Python and `pip`_ installed:

.. code-block:: bash

    python --version
    pip --version

Then set up a new virtual environment using `venv`_ of the Python standard library:

.. code-block:: bash

    # replace ~/venvs/streamlink with your path of choice and give it a proper name
    python -m venv ~/venvs/streamlink

Now activate the virtual environment by sourcing the activation shell script:

.. code-block:: bash

    source ~/venvs/streamlink/bin/activate

    # non-POSIX shells have their own activation script, e.g. FISH
    source ~/venvs/streamlink/bin/activate.fish

.. code-block:: pwsh

    # on Windows, activation scripts are located in the Scripts/ subdirectory instead of bin/
    ~\venvs\streamlink\Scripts\Activate.ps1

.. _pip: https://pip.pypa.io/en/stable/
.. _venv: https://docs.python.org/3/library/venv.html


Installing Streamlink
^^^^^^^^^^^^^^^^^^^^^

After activating the new virtual environment, Streamlink's development dependencies and Streamlink itself need to be installed.
Regular development dependencies and documentation related dependencies are listed in the text files shown below and need to
be installed separately.

.. code-block:: bash

    # install additional dependencies
    pip install -U -r dev-requirements.txt
    pip install -U -r docs-requirements.txt

    # install Streamlink in "editable" mode
    pip install -e .

    # validate that Streamlink is working
    streamlink --loglevel=debug


Validating changes
------------------

Before submitting a pull request, run tests, perform code linting and build the documentation on your system first, to see if
your changes contain any mistakes or errors. This will be done automatically for each pull request on each change, but
performing these checks locally avoids unnecessary build failures.

.. code-block:: bash

    # run automated tests
    pytest
    # or just run a subset of all tests
    pytest path/to/test-file.py::TestClassName::test_method_name ...

    # check code for linting errors
    ruff check .
    # check code for formatting errors
    ruff format --diff .
    # check code for typing errors
    mypy

    # build the documentation
    make --directory=docs clean html

    # check the documentation
    python -m http.server 8000 --bind '127.0.0.1' --directory 'docs/_build/html/'
    "${BROWSER}" http://127.0.0.1:8000/


Code style
----------

Streamlink uses `Ruff`_ as primary code `linting <Ruff-linter>`_ and `formatting <Ruff-formatter>`_ tool.

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
