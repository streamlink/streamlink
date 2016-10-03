.. _install:

.. Warning::
    The information contained in this page is misleading. Streamlink has not yet
    been packaged and distributed. This page was simply converted from the
    previous documentation.

Installation
============

Linux and BSD packages
----------------------

==================================== ===========================================
Distribution                         Installing
==================================== ===========================================
`Arch Linux (package)`_              .. code-block:: console

                                        # pacman -S streamlink
`Arch Linux (aur, git)`_             `Installing AUR packages`_
`CRUX`_                              .. code-block:: console

                                        $ cd /usr/ports/contrib/streamlink
                                        # pkgmk -d -i
`Debian`_                            .. code-block:: console

                                        # apt-get install streamlink
`Exherbo Linux`_
`Fedora`_                            .. code-block:: console

                                        # dnf install streamlink
`FreeBSD (package)`_                 .. code-block:: console

                                        # pkg install multimedia/streamlink
`FreeBSD (ports)`_                   .. code-block:: console

                                        $ cd /usr/ports/multimedia/streamlink
                                        # make install clean
`Gentoo Linux`_                      .. code-block:: console

                                        # emerge net-misc/streamlink
`NetBSD (pkgsrc)`_                   .. code-block:: console

                                        $ cd /usr/pkgsrc/multimedia/streamlink
                                        # make install clean
`OpenBSD (package)`_                 .. code-block:: console

                                        # pkg_add streamlink
`OpenBSD (ports)`_                   .. code-block:: console

                                        $ cd /usr/ports/multimedia/streamlink
                                        # make install clean
`Slackware Linux`_                   `Installing Slackbuilds`_
`Ubuntu`_                            .. code-block:: console

                                        # apt-get install streamlink
==================================== ===========================================

.. _Arch Linux (package): https://archlinux.org/packages/?q=streamlink
.. _Arch Linux (aur, git): https://aur.archlinux.org/packages/streamlink-git/
.. _CRUX: http://crux.nu/portdb/?a=search&q=streamlink
.. _Debian: https://packages.debian.org/search?keywords=streamlink&searchon=names&exact=1&suite=all&section=all
.. _Exherbo Linux: http://git.exherbo.org/summer/packages/media/streamlink/index.html
.. _Fedora: https://admin.fedoraproject.org/pkgdb/package/streamlink/
.. _FreeBSD (package): http://www.freshports.org/multimedia/streamlink
.. _FreeBSD (ports): http://www.freshports.org/multimedia/streamlink
.. _Gentoo Linux: https://packages.gentoo.org/package/net-misc/streamlink
.. _NetBSD (pkgsrc): http://pkgsrc.se/multimedia/streamlink
.. _OpenBSD (package): http://openports.se/multimedia/streamlink
.. _OpenBSD (ports): http://openports.se/multimedia/streamlink
.. _Slackware Linux: http://slackbuilds.org/result/?search=streamlink
.. _Ubuntu: http://packages.ubuntu.com/search?keywords=streamlink&searchon=names&exact=1&suite=all&section=all

.. _Installing AUR packages: https://wiki.archlinux.org/index.php/Arch_User_Repository#Installing_packages
.. _Installing Slackbuilds: http://slackbuilds.org/howto/

Other platforms
---------------

==================================== ===========================================
Platform                             Installing
==================================== ===========================================
Mac OS X                             .. code-block:: console

                                        # easy_install -U streamlink
Microsoft Windows                    See `Windows binaries`_.
==================================== ===========================================


Source code
-----------

If a package is not available for your platform (or it's out of date) you
can install Streamlink via source.

There are a few different methods to do this,
`pip <http://pip.readthedocs.org/en/latest/installing.html>`_ the Python package
manager, :command:`easy_install` the older package manager included with
`python-setuptools`_ or by checking out the latest code with
`Git <http://git-scm.com/downloads>`_.

The commands listed here will also upgrade any existing version of Streamlink.

==================================== ===========================================
Version                              Installing
==================================== ===========================================
`Latest release (pip)`_              .. code-block:: console

                                        # pip install -U streamlink
`Latest release (easy_install)`_     .. code-block:: console

                                        # easy_install -U streamlink
`Development version (pip)`_         .. code-block:: console

                                        # pip install -U git+https://github.com/streamlink/streamlink.git

`Development version (git)`_         .. code-block:: console

                                        $ git clone git://github.com/streamlink/streamlink.git
                                        $ cd streamlink
                                        # python setup.py install
==================================== ===========================================

.. _Latest release (pip): https://pypi.python.org/pypi/streamlink
.. _Latest release (easy_install): https://pypi.python.org/pypi/streamlink
.. _Development version (pip): https://github.com/streamlink/streamlink
.. _Development version (git): https://github.com/streamlink/streamlink

Dependencies
^^^^^^^^^^^^

To install Streamlink from source you will need these dependencies.

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

If you do not wish to install Streamlink globally on your system it's
recommended to use `virtualenv`_ to create a user owned Python environment
instead.

.. code-block:: console

    Creating an environment
    $ virtualenv ~/myenv

    Activating the environment
    $ source ~/myenv/bin/activate

    Installing streamlink into the environment
    (myenv)$ pip install streamlink

    Using streamlink in the enviroment
    (myenv)$ streamlink ...

    Deactivating the enviroment
    (myenv)$ deactivate

    Using streamlink without activating the environment
    $ ~/myenv/bin/streamlink ...

.. note::

    This may also be required on some OS X versions that seems to have weird
    permission issues (see issue #401).


.. _virtualenv: http://virtualenv.readthedocs.org/en/latest/


Windows binaries
----------------

:releaseref:`Installer <https://github.com/streamlink/streamlink/releases/download/v|release|/streamlink-v|release|-win32-setup.exe>`
^^^^^^^^^^^^^^^^^^^^^^

This is a installer which contains:

- A compiled version of Streamlink that does not require an existing Python
  installation
- `RTMPDump`_ for viewing RTMP streams

and performs the following tasks:

- Generates a default :ref:`configuration file <cli-streamlinkrc>`
- Adds Streamlink to your ``$PATH`` (making it possible to use
  :command:`streamlink` directly from the command prompt without specifying
  its directory)

:releaseref:`Zip archive <https://github.com/streamlink/streamlink/releases/download/v|release|/streamlink-v|release|-win32.zip>`
^^^^^^^^^^^^^^^^^^^^^^^^

This is minimal zip archive containing a compiled version of Streamlink that
does not require an existing Python installation.

`Nightly build`_
^^^^^^^^^^^^^^^^

This is an automatically generated build of the latest development code
from the git repo.

.. _Nightly build: http://streamlink-builds.s3.amazonaws.com/streamlink-latest-win32.zip


.. note::

    The binaries requires `Microsoft Visual C++ 2008 Redistributable
    Package <http://www.microsoft.com/en-us/download/details.aspx?id=29>`_ to
    be installed.
