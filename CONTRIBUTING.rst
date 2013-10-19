============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/chrippa/livestreamer/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug"
is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "feature"
is open to whoever wants to implement it.

Adding Plugins
~~~~~~~~~~~~~~

Livestreamer can always use more plugins. Look through the GitHub issues
if you are looking for something to implement.

There is no plugin documentation at the moment, but look at the existing
plugins to get an idea of how it works. 

Write Documentation
~~~~~~~~~~~~~~~~~~~

Livestreamer could always use more documentation, whether as part of the
official Livestreamer docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/chrippa/livestreamer/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `livestreamer` for local development.

1. Fork the `livestreamer` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/livestreamer.git

3. Install your local copy into a virtualenv. Assuming you have virtualenvwrapper installed, this is how you set up your fork for local development::

    $ mkvirtualenv livestreamer
    $ cd livestreamer/
    $ python setup.py develop

4. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

  Now you can make your changes locally.

5. When you're done making changes, check that your changes pass the
tests, including testing other Python versions with tox::

    $ python setup.py test
    $ tox

  To get tox, just pip install it into your virtualenv.

6. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests if it's a core feature.
2. If the pull request adds functionality, the docs should be updated.
3. When creating a pull request, make sure it's on the correct branch.
   These branches are currently used:

   - master: Only critical fixes that needs to be released ASAP.
   - develop: Everything else.

4. The pull request should work for Python 2.6, 2.7, and 3.3, and for PyPy. Check 
   https://travis-ci.org/chrippa/livestreamer/pull_requests
   and make sure that the tests pass for all supported Python versions.

