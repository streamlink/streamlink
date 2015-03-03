.. _install:

Installation
============

Linux and BSD packages
----------------------

==================================== ===========================================
Distribution                         Installing
==================================== ===========================================
`Arch Linux (package)`_              .. code-block:: console

                                        # pacman -S livestreamer
`Arch Linux (aur, git)`_             `Installing AUR packages`_
`CRUX`_                              .. code-block:: console

                                        $ cd /usr/ports/contrib/livestreamer
                                        # pkgmk -d -i
`Debian`_                            .. code-block:: console

                                        # apt-get install livestreamer
`Exherbo Linux`_
`Fedora`_                            .. code-block:: console

                                        # yum install livestreamer
`FreeBSD (package)`_                 .. code-block:: console

                                        # pkg install multimedia/livestreamer
`FreeBSD (ports)`_                   .. code-block:: console

                                        $ cd /usr/ports/multimedia/livestreamer
                                        # make install clean
`Gentoo Linux`_                      .. code-block:: console

                                        # emerge net-misc/livestreamer
`NetBSD (pkgsrc)`_                   .. code-block:: console

                                        $ cd /usr/pkgsrc/multimedia/livestreamer
                                        # make install clean
`OpenBSD (package)`_                 .. code-block:: console

                                        # pkg_add livestreamer
`OpenBSD (ports)`_                   .. code-block:: console

                                        $ cd /usr/ports/multimedia/livestreamer
                                        # make install clean
`Slackware Linux`_                   `Installing Slackbuilds`_
`Ubuntu`_                            .. code-block:: console

                                        # apt-get install livestreamer
==================================== ===========================================

.. _Arch Linux (package): https://archlinux.org/packages/?q=livestreamer
.. _Arch Linux (aur, git): https://aur.archlinux.org/packages/livestreamer-git/
.. _CRUX: http://crux.nu/portdb/?a=search&q=livestreamer
.. _Debian: https://packages.debian.org/search?keywords=livestreamer&searchon=names&exact=1&suite=all&section=all
.. _Exherbo Linux: http://git.exherbo.org/summer/packages/media/livestreamer/index.html
.. _Fedora: https://admin.fedoraproject.org/pkgdb/package/livestreamer/
.. _FreeBSD (package): http://www.freshports.org/multimedia/livestreamer
.. _FreeBSD (ports): http://www.freshports.org/multimedia/livestreamer
.. _Gentoo Linux: https://packages.gentoo.org/package/net-misc/livestreamer
.. _NetBSD (pkgsrc): http://pkgsrc.se/multimedia/livestreamer
.. _OpenBSD (package): http://openports.se/multimedia/livestreamer
.. _OpenBSD (ports): http://openports.se/multimedia/livestreamer
.. _Slackware Linux: http://slackbuilds.org/result/?search=livestreamer
.. _Ubuntu: http://packages.ubuntu.com/search?keywords=livestreamer&searchon=names&exact=1&suite=all&section=all

.. _Installing AUR packages: https://wiki.archlinux.org/index.php/Arch_User_Repository#Installing_packages
.. _Installing Slackbuilds: http://slackbuilds.org/howto/

Other platforms
---------------

==================================== ===========================================
Platform                             Installing
==================================== ===========================================
Mac OS X                             .. code-block:: console

                                        # easy_install -U livestreamer
Microsoft Windows                    See `Windows binaries`_.
==================================== ===========================================


Source code
-----------

If a package is not available for your platform (or it's out of date) you
can install Livestreamer via source.

There are a few different methods to do this,
`pip <http://pip.readthedocs.org/en/latest/installing.html>`_ the Python package
manager, :command:`easy_install` the older package manager included with
`python-setuptools`_ or by checking out the latest code with
`Git <http://git-scm.com/downloads>`_.

The commands listed here will also upgrade any existing version of Livestreamer.

==================================== ===========================================
Version                              Installing
==================================== ===========================================
`Latest release (pip)`_              .. code-block:: console

                                        # pip install -U livestreamer
`Latest release (easy_install)`_     .. code-block:: console

                                        # easy_install -U livestreamer
`Development version (pip)`_         .. code-block:: console

                                        # pip install -U git+https://github.com/chrippa/livestreamer.git

`Development version (git)`_         .. code-block:: console

                                        $ git clone git://github.com/chrippa/livestreamer.git
                                        $ cd livestreamer
                                        # python setup.py install
==================================== ===========================================

.. _Latest release (pip): https://pypi.python.org/pypi/livestreamer
.. _Latest release (easy_install): https://pypi.python.org/pypi/livestreamer
.. _Development version (pip): https://github.com/chrippa/livestreamer
.. _Development version (git): https://github.com/chrippa/livestreamer

Dependencies
^^^^^^^^^^^^

To install Livestreamer from source you will need these dependencies.

==================================== ===========================================
Name                                 Notes
==================================== ===========================================
`Python`_                            At least version **2.6** or **3.3**.
`python-setuptools`_

**Automatically installed by the setup script**
--------------------------------------------------------------------------------
`python-argparse`_                   Only needed on Python **2.6**.
`python-futures`_                    Only needed on Python **2.x**.
`python-requests`_                   At least version **1.0**.
`python-singledispatch`_             Only needed on Python versions older than **3.4**.

**Optional**
--------------------------------------------------------------------------------
`RTMPDump`_                          Required to play RTMP streams.
`PyCrypto`_                          Required to play some encrypted streams.
`python-librtmp`_                    Required by the *ustreamtv* plugin to be
                                     able to use non-mobile streams.
==================================== ===========================================

.. _Python: http://python.org/
.. _python-setuptools: http://pypi.python.org/pypi/setuptools
.. _python-argparse: http://pypi.python.org/pypi/argparse
.. _python-futures: http://pypi.python.org/pypi/futures
.. _python-requests: http://python-requests.org/
.. _python-singledispatch: http://pypi.python.org/pypi/singledispatch
.. _RTMPDump: http://rtmpdump.mplayerhq.hu/
.. _PyCrypto: https://www.dlitz.net/software/pycrypto/
.. _python-librtmp: https://github.com/chrippa/python-librtmp


Installing without root permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you do not wish to install Livestreamer globally on your system it's
recommended to use `virtualenv`_ to create a user owned Python environment
instead.

.. code-block:: console

    Creating an environment
    $ virtualenv ~/myenv

    Activating the environment
    $ source ~/myenv/bin/activate

    Installing livestreamer into the environment
    (myenv)$ pip install livestreamer

    Using livestreamer in the enviroment
    (myenv)$ livestreamer ...

    Deactivating the enviroment
    (myenv)$ deactivate

    Using livestreamer without activating the environment
    $ ~/myenv/bin/livestreamer ...

.. note::

    This may also be required on some OS X versions that seems to have weird
    permission issues (see issue #401).


.. _virtualenv: http://virtualenv.readthedocs.org/en/latest/


Windows binaries
----------------

:releaseref:`Installer <https://github.com/chrippa/livestreamer/releases/download/v|release|/livestreamer-v|release|-win32-setup.exe>`
^^^^^^^^^^^^^^^^^^^^^^

This is a installer which contains:

- A compiled version of Livestreamer that does not require an existing Python
  installation
- `RTMPDump`_ for viewing RTMP streams

and performs the following tasks:

- Generates a default :ref:`configuration file <cli-livestreamerrc>`
- Adds Livestreamer to your ``$PATH`` (making it possible to use
  :command:`livestreamer` directly from the command prompt without specifying
  its directory)

:releaseref:`Zip archive <https://github.com/chrippa/livestreamer/releases/download/v|release|/livestreamer-v|release|-win32.zip>`
^^^^^^^^^^^^^^^^^^^^^^^^

This is minimal zip archive containing a compiled version of Livestreamer that
does not require an existing Python installation.

`Nightly build`_
^^^^^^^^^^^^^^^^

This is an automatically generated build of the latest development code
from the git repo.

.. _Nightly build: http://livestreamer-builds.s3.amazonaws.com/livestreamer-latest-win32.zip


.. note::

    The binaries requires `Microsoft Visual C++ 2008 Redistributable
    Package <http://www.microsoft.com/en-us/download/details.aspx?id=29>`_ to
    be installed.


