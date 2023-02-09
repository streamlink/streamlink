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

First, make sure that you have the latest stable versions of Python and pip installed.

.. code-block:: bash

    python --version
    pip --version

As the second preparation step, install the latest version of ``virtualenv``, either via your system's package manager or pip,
and create a new virtual environment. These environments can be created separately for different Python versions. Please refer
to the `virtualenv documentation`_ for all available parameters. There are also several wrappers around virtualenv available.

.. code-block:: bash

    pip install --upgrade --user virtualenv
    virtualenv --version

    # replace ~/venvs/streamlink with your path of choice and give it a proper name
    virtualenv --download --verbose ~/venvs/streamlink

Now activate the virtual environment by sourcing the activation shell script.

.. code-block:: bash

    source ~/venvs/streamlink/bin/activate

    # non-POSIX shells have their own activation script, eg. FISH
    source ~/venvs/streamlink/bin/activate.fish

    # on Windows, activation scripts are located in the Scripts/ subdirectory instead of bin/
    source ~/venvs/streamlink/Scripts/activate

.. _virtualenv documentation: https://virtualenv.pypa.io/en/latest/


Installing Streamlink
^^^^^^^^^^^^^^^^^^^^^

After activating the new virtual environment, Streamlink's build dependencies and Streamlink itself need to be installed.
Regular development dependencies and documentation related dependencies are listed in the text files shown below and need to
be installed separately.

.. code-block:: bash

    # install additional dependencies
    pip install -r dev-requirements.txt
    pip install -r docs-requirements.txt

    # install Streamlink from source
    # check setup.py for optional dependencies and install those manually if you need to
    pip install -e .

    # validate that Streamlink is working
    which streamlink
    streamlink --version


Validating changes
------------------

Before submitting a pull request, run tests, perform code linting and build the documentation on your system first, to see if
your changes contain any mistakes or errors. This will be done automatically for each pull request on each change, but
performing these checks locally avoids unnecessary build failures.

.. code-block:: bash

    # run automated tests
    python -m pytest -ra
    # or just run a subset of all tests
    python -m pytest -ra path/to/test-file.py::TestClassName::test_method_name ...

    # check code for linting errors
    ruff .
    # check code for typing errors
    mypy
    # optionally check for typing errors if changes were made to the docs extensions
    mypy docs

    # build the documentation
    make --directory=docs clean html
    $BROWSER ./docs/_build/html/index.html


Code style
----------

Streamlink uses `Ruff`_ as primary code linting tool and the project aims to use best practices for achieving great
code readability with minimal git diffs, as detailed in :pep:`8` and implemented in related linting tools, such as `Black`_.

These are the best practices most likely to be relevant to plugin authors:

1. `Import order according to PEP8 <pep8-imports_>`_

2. `Indentation of 4 spaces per level <pep8-indentation_>`_

3. `Double quotes for all string literals <black-quotes_>`_

4. `Line length of at most 128 characters <pyproject.toml_>`_

5. `Balanced line wrapping for readability <black-line-wrapping_>`_

6. `Blank lines <pep8-blank-lines_>`_

7. `Comments <pep8-comments_>`_

8. `Line breaks and binary operators <pep8-binary-operators_>`_

9. New indented line for each bracket item (args, lists, etc.) in multi-line definitions, with trailing comma

   .. code-block:: python

      # incorrect:
      schema=validate.Schema(
          validate.parse_json(), [{
              "foo": {"bar": validate.url(schema="https", path=validate.endswith(".m3u8"))}, "baz": str
          }]
      )

      # correct:
      schema=validate.Schema(
          validate.parse_json(),
          [{
              "foo": {
                  "bar": validate.url(schema="https", path=validate.endswith(".m3u8")),
              },
              "baz": str,
          }],
      )

It might be helpful to new plugin authors to pick a small and recently modified existing plugin to use as an initial
template from which to work. If care is taken to preserve existing blank lines during modification, the main plugin
structure should be compliant-ready for `linting <Validating changes_>`_.

.. _Ruff: https://github.com/charliermarsh/ruff#readme
.. _Black: https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html
.. _pyproject.toml: https://github.com/streamlink/streamlink/blob/master/pyproject.toml
.. _pep8-binary-operators: https://peps.python.org/pep-0008/#should-a-line-break-before-or-after-a-binary-operator
.. _pep8-blank-lines: https://peps.python.org/pep-0008/#blank-lines
.. _pep8-comments: https://peps.python.org/pep-0008/#comments
.. _pep8-imports: https://peps.python.org/pep-0008/#imports
.. _pep8-indentation: https://peps.python.org/pep-0008/#indentation
.. _black-line-wrapping: https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html#how-black-wraps-lines
.. _black-quotes: https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html#strings


Plugins
-------

Adding plugins
^^^^^^^^^^^^^^

1. Implement the plugin in ``src/streamlink/plugins/pluginname.py``, similar to already existing plugins.

   Check the git log for recently added or modified plugins to help you get an overview of what's needed to properly implement
   a plugin. A complete guide is currently not available.

   Each plugin class requires at least one ``pluginmatcher`` decorator which defines the URL regex, matching priority
   and an optional name.

   Plugins need to implement the ``_get_streams()`` method which either returns a list of ``Stream`` instances or which yields
   ``Stream`` instances. ``Stream`` is the base class of ``HTTPStream``, ``HLSStream`` and ``DASHStream``.

   Plugins also require metadata which will be read when building the documentation. This metadata contains information about
   the plugin, eg. which URLs it accepts, which kind of streams it returns, whether content is region-locked, or if any kind of
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
