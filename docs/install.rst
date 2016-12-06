.. _install:

Installation
============

Linux and BSD packages
----------------------

==================================== ===========================================
Distribution                         Installing
==================================== ===========================================
`Arch Linux (aur)`_                  .. code-block:: console

                                        # pacaur -S streamlink

`Arch Linux (aur, git)`_             .. code-block:: console

                                        # pacaur -S streamlink-git

                                     `Installing AUR packages`_
`Gentoo Linux`_                      .. code-block:: console

                                        # emerge net-misc/streamlink
`NetBSD (pkgsrc)`_                   .. code-block:: console

                                        $ cd /usr/pkgsrc/multimedia/streamlink
                                        # make install clean
`Solus`_                             .. code-block:: console

                                        # eopkg install streamlink
`Ubuntu`_                            .. code-block:: console

                                        # add-apt-repository ppa:nilarimogard/webupd8
                                        # apt update
                                        # apt install streamlink
`Void`_                              .. code-block:: console

                                        # xbps-install streamlink
==================================== ===========================================

.. _Arch Linux (aur): https://aur.archlinux.org/packages/streamlink/
.. _Arch Linux (aur, git): https://aur.archlinux.org/packages/streamlink-git/
.. _Gentoo Linux: https://packages.gentoo.org/package/net-misc/streamlink
.. _NetBSD (pkgsrc): http://pkgsrc.se/multimedia/streamlink
.. _Solus: https://git.solus-project.com/packages/streamlink/
.. _Ubuntu: http://ppa.launchpad.net/nilarimogard/webupd8/ubuntu/pool/main/s/streamlink/
.. _Void: https://github.com/voidlinux/void-packages/tree/master/srcpkgs/streamlink

.. _Installing AUR packages: https://wiki.archlinux.org/index.php/Arch_User_Repository#Installing_packages

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
`pycryptodome`_                      Required to play some encrypted streams

**Optional**
--------------------------------------------------------------------------------
`RTMPDump`_                          Required to play RTMP streams.
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
.. _pycryptodome: https://pycryptodome.readthedocs.io/en/latest/
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

You can download the latest stable Windows installer `here <https://github.com/streamlink/streamlink/releases>`_.

You can download the latest nightly Windows installer `here <https://streamlink-builds.s3.amazonaws.com/nightly/windows/streamlink-latest.exe>`_.

This is a installer which contains:

- A compiled version of Streamlink that does not require an existing Python
  installation
- `RTMPDump`_ for viewing RTMP streams

and performs the following tasks:

- Adds Streamlink to your ``$PATH`` (making it possible to use
  :command:`streamlink` directly from the command prompt without specifying
  its directory)

To build the installer, you need to have NSIS and pynsist installed on your
system.
