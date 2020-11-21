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
    flake8

    # build the documentation
    make --directory=docs clean html
    $BROWSER ./docs/_build/html/index.html


Plugins
-------

Adding plugins
^^^^^^^^^^^^^^

1. Implement the plugin in ``src/streamlink/plugins/``, similar to already existing plugins. Check the git log for recently
   added or modified plugins to help you get an overview of what's needed to properly implement a plugin. A complete guide
   is currently not available.
2. Add at least tests for the URL regex matching in ``tests/plugins/``. Once again, check other plugin tests from the git log.

Removing plugins
^^^^^^^^^^^^^^^^

1. Remove the plugin file in ``src/streamlink/plugins/`` and the test file in ``tests/plugins/``
2. Remove the plugin entry from the documentation in ``docs/plugin_matrix.rst``
3. Add an entry to ``src/streamlink/plugins/.removed``
