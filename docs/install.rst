.. _install:

Installing
==========

Arch Linux
----------

Livestreamer is available in the `community package repository <https://www.archlinux.org/packages/community/any/livestreamer/>`_.

.. code-block:: console

    # pacman -S livestreamer

Debian/Ubuntu Linux
-------------------

Install pip via APT first, then install Livestreamer via pip:

.. code-block:: console

    # apt-get install python-pip
    # pip install livestreamer

FreeBSD
-------

Livestreamer is available in the `ports tree <http://www.freshports.org/multimedia/livestreamer>`_ and also as a `package <http://www.freshports.org/multimedia/livestreamer>`_.

**Via ports**

.. code-block:: console

    # cd /usr/ports/multimedia/livestreamer
    # make install clean

**Via package**

.. code-block:: console

    # pkg install multimedia/livestreamer

Gentoo Linux
------------

Livestreamer is available in the `official portage tree <https://packages.gentoo.org/package/net-misc/livestreamer>`_:

.. code-block:: console

    # emerge net-misc/livestreamer

Mac OS X
--------

Mac OS X comes with Python and ``easy_install`` installed by default:

.. code-block:: console

    # easy_install livestreamer

OpenBSD
-------

Livestreamer is available in the `ports tree <http://openports.se/multimedia/livestreamer>`_:

.. code-block:: console

    # cd /usr/ports/multimedia/livestreamer
    # make install clean

Windows
-------
Livestreamer is primarily developed for Unix-like operating systems where using a CLI is common. There is however a installer available for brave Windows users who don't mind using the command prompt.

The installer can be `downloaded from Github <https://github.com/chrippa/livestreamer/releases>`_. It contains a precompiled version of Livestreamer that does not require you to install any of the dependencies.

Development builds
^^^^^^^^^^^^^^^^^^

There are development builds available for Windows `here <http://livestreamer-builds.s3.amazonaws.com/builds.html>`_.


Other OSs/from source
---------------------

**Stable version**

The preferred way install Livestreamer is to use the Python package manager `pip <http://www.pip-installer.org/>`_:

.. code-block:: console

    # pip install livestreamer

But it is also possible to use the old way of installing Python packages via ``easy_install``:

.. code-block:: console

    # easy_install livestreamer

**Development version**

You can get the latest development version using `Git <http://git-scm.com/>`_:

.. code-block:: console

    $ git clone git://github.com/chrippa/livestreamer.git
    $ cd livestreamer
    # python setup.py install


Dependencies
^^^^^^^^^^^^

Livestreamer currently depends on these libraries/programs to function.

To run the setup script you need:

- `Python <http://python.org/>`_ (at least version 2.6) or `PyPy <http://pypy.org/>`_
- `python-setuptools <http://pypi.python.org/pypi/setuptools>`_


These will be installed automatically by the setup script if they are missing:

- `python-argparse <http://pypi.python.org/pypi/argparse>`_ (only needed on Python version <2.7 and <3.2)
- `python-requests <http://docs.python-requests.org/>`_ (at least version 1.0)


`The Hitchhiker’s Guide to Python <http://docs.python-guide.org/>`_ has guides
helping you install Python on most common operating systems.

Optional dependencies
^^^^^^^^^^^^^^^^^^^^^

For RTMP based plugins:

- `RTMPDump <http://rtmpdump.mplayerhq.hu/>`_

For decrypting encrypted HLS streams:

- `PyCrypto <https://www.dlitz.net/software/pycrypto/>`_

For full UStream.tv support:

- `python-librtmp <https://github.com/chrippa/python-librtmp>`_


