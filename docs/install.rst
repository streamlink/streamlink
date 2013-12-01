.. _install:

Installing
==========

Source
------

The latest stable version is available to install using `pip <http://www.pip-installer.org/>`_:

.. code-block:: console

    # pip install livestreamer

But you can also get the development version using `Git <http://git-scm.com/>`_:

.. code-block:: console

    $ git clone git://github.com/chrippa/livestreamer.git
    $ cd livestreamer
    # python setup.py install

`The Hitchhiker’s Guide to Python <http://docs.python-guide.org/>`_ has guides
helping you install Python + pip on the most common operating systems.

Dependencies
^^^^^^^^^^^^

Livestreamer currently depends on these libraries/programs to function.

To run the setup script you need:

- `Python <http://python.org/>`_ (at least version 2.6) or `PyPy <http://pypy.org/>`_
- `python-setuptools <http://pypi.python.org/pypi/setuptools>`_


These will be installed automatically by the setup script if they are missing:

- `python-argparse <http://pypi.python.org/pypi/argparse>`_ (only needed on Python version <2.7 and <3.2)
- `python-requests <http://docs.python-requests.org/>`_ (at least version 1.0)

Optional dependencies
^^^^^^^^^^^^^^^^^^^^^

For RTMP based plugins:

- `RTMPDump <http://rtmpdump.mplayerhq.hu/>`_ (Twitch/Justin.tv streams require at least version 2.4-20111222)

For decrypting encrypted HLS streams:

- `PyCrypto <https://www.dlitz.net/software/pycrypto/>`_

For full UStream.tv support:

- `python-librtmp <https://github.com/chrippa/python-librtmp>`_

Distribution packages
---------------------

Livestreamer is also available in these package repositories:

- `Arch Linux <https://www.archlinux.org/packages/community/any/livestreamer/>`_
- `FreeBSD <http://www.freshports.org/multimedia/livestreamer>`_
- `Gentoo Linux <https://packages.gentoo.org/package/net-misc/livestreamer>`_
- `OpenBSD <http://openports.se/multimedia/livestreamer>`_

Windows
^^^^^^^
Livestreamer is primarily developed for Unix-like operating systems where using a CLI is common. There is however a installer available for brave Windows users who don't mind using the command prompt.

The installer can be `downloaded from Github <https://github.com/chrippa/livestreamer/releases>`_. It contains a precompiled version of Livestreamer that does not require you to install any of the dependencies.

