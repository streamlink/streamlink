.. _install:

Installation
============

Arch Linux
----------

Livestreamer is available in the `community package repository
<https://www.archlinux.org/packages/community/any/livestreamer/>`_.

.. code-block:: console

    # pacman -S livestreamer

Debian Linux
------------

Livestreamer is available in `Debian Sid
<https://packages.debian.org/sid/livestreamer>`_.

.. code-block:: console

    # apt-get install livestreamer

FreeBSD
-------

Livestreamer is available in the `ports tree
<http://www.freshports.org/multimedia/livestreamer>`_ and also as a
`package <http://www.freshports.org/multimedia/livestreamer>`_.

**Via ports**

.. code-block:: console

    # cd /usr/ports/multimedia/livestreamer
    # make install clean

**Via package**

.. code-block:: console

    # pkg install multimedia/livestreamer

Gentoo Linux
------------

Livestreamer is available in the `official portage tree
<https://packages.gentoo.org/package/net-misc/livestreamer>`_:

.. code-block:: console

    # emerge net-misc/livestreamer

Mac OS X
--------

Mac OS X comes with Python and ``easy_install`` installed by default:

.. code-block:: console

    # easy_install -U livestreamer

OpenBSD
-------

Livestreamer is available in the `ports tree <http://openports.se/multimedia/livestreamer>`_:

.. code-block:: console

    # cd /usr/ports/multimedia/livestreamer
    # make install clean

Ubuntu Linux
-------------------

Install pip via APT first, then install Livestreamer via pip:

.. code-block:: console

    # apt-get install python-pip
    # pip install -U livestreamer

Windows
-------

Installer
^^^^^^^^^

This is a installer which contains and performs the following tasks:

- A compiled version of Livestreamer that does not require Python
- RTMPDump for viewing RTMP streams
- Generates a default :ref:`configuration file <cli-livestreamerrc>`
- Adds Livestreamer to your ``$PATH`` (making it possible to use
  :command:`livestreamer` directly from the command prompt without specifying
  its directory)

.. rst-class:: btn btn-neutral

   `livestreamer-v1.8.2-win32-setup.exe <https://github.com/chrippa/livestreamer/releases/download/v1.8.2/livestreamer-v1.8.2-win32-setup.exe>`_

ZIP Archive
^^^^^^^^^^^

This is minimal ZIP containing only a compiled version of Livestreamer
that does not require Python to be installed.

.. rst-class:: btn btn-neutral

   `livestreamer-v1.8.2-win32.zip <https://github.com/chrippa/livestreamer/releases/download/v1.8.2/livestreamer-v1.8.2-win32.zip>`_

Development build
^^^^^^^^^^^^^^^^^

This is an automatically generated build of the latest development code
from the git repo.

.. rst-class:: btn btn-neutral

   `livestreamer-latest-win32.zip <http://livestreamer-builds.s3.amazonaws.com/livestreamer-latest-win32.zip>`_



Other platforms/from source
---------------------------

Stable version
^^^^^^^^^^^^^^

The preferred way install Livestreamer is to use the Python package manager
`pip <http://www.pip-installer.org/>`_:

.. code-block:: console

    # pip install -U livestreamer

But it's also possible to use the old way of installing Python packages
via ``easy_install``:

.. code-block:: console

    # easy_install -U livestreamer

Development version
^^^^^^^^^^^^^^^^^^^

pip can download the latest source code and install it for you:

.. code-block:: console

    # pip install --upgrade git+https://github.com/chrippa/livestreamer.git#egg=livestreamer

or you can manually download the source using `Git <http://git-scm.com/>`_:

.. code-block:: console

    $ git clone git://github.com/chrippa/livestreamer.git
    $ cd livestreamer
    # python setup.py install


Dependencies
^^^^^^^^^^^^

Livestreamer currently depends on these libraries/programs to function.

To run the setup script you need:

- `Python <http://python.org/>`_ (2.6+ or 3.3+)
- `python-setuptools <http://pypi.python.org/pypi/setuptools>`_


These will be installed automatically by the setup script if they are missing:

- `python-argparse <http://pypi.python.org/pypi/argparse>`_ (only needed on Python 2.6)
- `python-requests <http://docs.python-requests.org/>`_ (at least version 1.0)
- `python-singledispatch <http://pypi.python.org/pypi/singledispatch>`_ (only needed on Python version <3.4)


`The Hitchhiker’s Guide to Python <http://docs.python-guide.org/>`_ has guides
helping you install Python on most common operating systems.

Optional dependencies
^^^^^^^^^^^^^^^^^^^^^

For RTMP based plugins:

- `RTMPDump <http://rtmpdump.mplayerhq.hu/>`_

For decrypting encrypted HLS streams:

- `PyCrypto <https://www.dlitz.net/software/pycrypto/>`_

For the ``ustreamtv`` plugin to be able to use non-mobile streams:

- `python-librtmp <https://github.com/chrippa/python-librtmp>`_


