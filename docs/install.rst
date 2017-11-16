.. _install:

Installation
============

Linux and BSD packages
----------------------

==================================== ===========================================
Distribution                         Installing
==================================== ===========================================
`Arch Linux`_                        .. code-block:: console

                                        # pacman -S streamlink

`Arch Linux (aur, git)`_             .. code-block:: console

                                        # pacaur -S streamlink-git

                                     `Installing AUR packages`_
`Fedora`_                            .. code-block:: console

                                        # dnf install streamlink
`Gentoo Linux`_                      .. code-block:: console

                                        # emerge net-misc/streamlink
`NetBSD (pkgsrc)`_                   .. code-block:: console

                                        $ cd /usr/pkgsrc/multimedia/streamlink
                                        # make install clean
`NixOS`_                             `Installing NixOS packages`_
`Solus`_                             .. code-block:: console

                                        # eopkg install streamlink
`Ubuntu`_                            .. code-block:: console

                                        # add-apt-repository ppa:nilarimogard/webupd8
                                        # apt update
                                        # apt install streamlink
`Void`_                              .. code-block:: console

                                        # xbps-install streamlink
==================================== ===========================================

.. _Arch Linux: https://www.archlinux.org/packages/community/any/streamlink/
.. _Arch Linux (aur, git): https://aur.archlinux.org/packages/streamlink-git/
.. _Fedora: https://apps.fedoraproject.org/packages/python-streamlink
.. _Gentoo Linux: https://packages.gentoo.org/package/net-misc/streamlink
.. _NetBSD (pkgsrc): http://pkgsrc.se/multimedia/streamlink
.. _NixOS: https://github.com/NixOS/nixpkgs/tree/master/pkgs/applications/video/streamlink
.. _Solus: https://git.solus-project.com/packages/streamlink/
.. _Ubuntu: http://ppa.launchpad.net/nilarimogard/webupd8/ubuntu/pool/main/s/streamlink/
.. _Void: https://github.com/voidlinux/void-packages/tree/master/srcpkgs/streamlink

.. _Installing AUR packages: https://wiki.archlinux.org/index.php/Arch_User_Repository#Installing_packages
.. _Installing NixOS packages: https://nixos.org/wiki/Install/remove_software#How_to_install_software

Other platforms
---------------

==================================== ===========================================
Platform                             Installing
==================================== ===========================================
Mac OS X                             .. code-block:: console

                                        # easy_install -U streamlink
`Homebrew`_                          .. code-block:: console

                                        # brew install streamlink

                                     `Installing Homebrew packages`_
Microsoft Windows                    See `Windows binaries`_ and `Windows portable version`_.

`Chocolatey`_                        .. code-block:: console

                                        C:\> choco install streamlink

                                     `Installing Chocolatey packages`_
==================================== ===========================================

.. _Homebrew: https://github.com/Homebrew/homebrew-core/blob/master/Formula/streamlink.rb
.. _Chocolatey: https://chocolatey.org/packages/streamlink

.. _Installing Homebrew packages: https://brew.sh
.. _Installing Chocolatey packages: https://chocolatey.org

Package maintainers
-------------------
==================================== ===========================================
Distribution/Platform                Maintainer
==================================== ===========================================
Arch                                 Giancarlo Razzolini <grazzolini at archlinux.org>
Arch (aur, git)                      Josip Ponjavic <josipponjavic at gmail.com>
Chocolatey                           Scott Walters <me at scowalt.com>
Fedora                               Mohamed El Morabity <melmorabity at fedoraproject.org>
Gentoo                               soredake <fdsfgs at krutt.org>
NetBSD                               Maya Rashish <maya at netbsd.org>
NixOS                                Tuomas Tynkkynen <tuomas.tynkkynen at iki.fi>
Solus                                Bryan T. Meyers <bmeyers at datadrake.com>
Ubuntu                               Alin Andrei <andrew at webupd8.org>
Void                                 wkuipers <wietse at kuiprs.nl>
Windows binaries                     beardypig <beardypig at protonmail.com>
Windows port. version                RosadinTV <RosadinTV at outlook.com>, beardypig <beardypig at protonmail.com>
==================================== ===========================================


Source code
-----------

If a package is not available for your platform (or it's out of date) you
can install Streamlink via source.

There are a few different methods to do this,
`pip <http://pip.readthedocs.org/en/latest/installing.html>`_ the Python package
manager, or by checking out the latest code with
`Git <http://git-scm.com/downloads>`_. Using :command:`easy_install` is no longer recommended.

.. note::

    For some Linux distributions the Python headers package needs to be installed before installing streamlink
    (``python-devel`` in RedHat, Fedora, etc.).

    Ensure that you are using an up-to-date version of :command:`pip`, at least version **6** is recommended.


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
`Python`_                            At least version **2.7** or **3.3**.
`python-setuptools`_

**Automatically installed by the setup script**
--------------------------------------------------------------------------------
`python-argparse`_                   Only needed on Python versions older than **2.7**.
`python-futures`_                    Only needed on Python **2.x**.
`python-requests`_                   At least version **1.0**.
`python-singledispatch`_             Only needed on Python versions older than **3.4**.
`pycryptodome`_                      Required to play some encrypted streams
`iso-639`_                           Used for localization settings, provides language information
`iso3166`_                           Used for localization settings, provides country information

**Optional**
--------------------------------------------------------------------------------
`RTMPDump`_                          Required to play RTMP streams.
`ffmpeg`_                            Required to play streams that are made up of separate
                                     audio and video streams, eg. YouTube 1080p+
==================================== ===========================================

Using pycrypto and pycountry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

With these two environment variables it is possible to use `pycrypto`_ instead of
`pycryptodome`_ and `pycountry`_ instead of `iso-639`_ and `iso3166`_.

.. code-block:: console

    $ export STREAMLINK_USE_PYCRYPTO="true"
    $ export STREAMLINK_USE_PYCOUNTRY="true"

.. _Python: http://python.org/
.. _python-setuptools: http://pypi.python.org/pypi/setuptools
.. _python-argparse: http://pypi.python.org/pypi/argparse
.. _python-futures: http://pypi.python.org/pypi/futures
.. _python-requests: http://python-requests.org/
.. _python-singledispatch: http://pypi.python.org/pypi/singledispatch
.. _RTMPDump: http://rtmpdump.mplayerhq.hu/
.. _pycountry: https://pypi.python.org/pypi/pycountry
.. _pycrypto: https://www.dlitz.net/software/pycrypto/
.. _pycryptodome: https://pycryptodome.readthedocs.io/en/latest/
.. _ffmpeg: https://www.ffmpeg.org/
.. _iso-639: https://pypi.python.org/pypi/iso-639
.. _iso3166: https://pypi.python.org/pypi/iso3166


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

.. important::

    Windows XP is not supported.
    Windows Vista requires at least SP2 to be installed. 

A Windows installer of the latest **stable release** can be found on the `GitHub releases page <https://github.com/streamlink/streamlink/releases/latest>`__.

Alternatively, a Windows installer of the `latest development build <https://dl.bintray.com/streamlink/streamlink-nightly/streamlink-latest.exe>`__ for testing purposes is available,
with a summary of the changes in the `release notes <https://bintray.com/streamlink/streamlink-nightly/streamlink/latest#release>`__. This development build is updated once per day,
and a list of `previous builds <https://dl.bintray.com/streamlink/streamlink-nightly/>`__ is provided.

This is an installer which contains:

- A compiled version of Streamlink that does not require an existing Python
  installation
- `RTMPDump`_ for viewing RTMP streams
- `ffmpeg`_ for muxing streams

and performs the following tasks:

- Adds Streamlink to your ``$PATH`` (making it possible to use
  :command:`streamlink` directly from the command prompt without specifying
  its directory)

To build the installer, you need to have ``NSIS`` and ``pynsist`` installed on your
system.


Windows portable version
^^^^^^^^^^^^^^^^^^^^^^^^

==================================== ===========================================
Maintainer                           Links
==================================== ===========================================
RosadinTV                            `Latest precompiled stable release`__

                                     `Latest builder`__
                                     
                                     `More info`__

Beardypig                            `Latest precompiled stable release`__

                                     `Latest builder`__

                                     `More info`__
==================================== ===========================================

__ https://github.com/streamlink/streamlink-portable/releases/latest
__ https://github.com/streamlink/streamlink-portable/archive/master.zip
__ https://github.com/streamlink/streamlink-portable

__ https://github.com/beardypig/streamlink-portable/releases/latest
__ https://github.com/beardypig/streamlink-portable/archive/master.zip
__ https://github.com/beardypig/streamlink-portable
