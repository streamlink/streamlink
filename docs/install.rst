.. _install:

.. |br| raw:: html

  <br />

Installation
============

Windows
-------

.. rst-class:: table-custom-layout

==================================== ===========================================
Method                               Installing
==================================== ===========================================
Installers                           See the `Windows binaries`_ section below

Portable                             See the `Windows portable version`_ section below

`Chocolatey`_                        .. code-block:: bat

                                        choco install streamlink

                                     `Installing Chocolatey packages`_

`Windows Package Manager`_           .. code-block:: bat

                                        winget install streamlink

                                     `Installing Winget packages`_
==================================== ===========================================

.. _Chocolatey: https://chocolatey.org/packages/streamlink

.. _Windows Package Manager: https://github.com/microsoft/winget-pkgs/tree/master/manifests/Streamlink/Streamlink

.. _Installing Chocolatey packages: https://chocolatey.org

.. _Installing Winget packages: https://docs.microsoft.com/en-us/windows/package-manager/

macOS
-----

.. rst-class:: table-custom-layout

==================================== ===========================================
Method                               Installing
==================================== ===========================================
Python pip                           See the `PyPI package and source code`_ section below

`Homebrew`_                          .. code-block:: bash

                                        brew install streamlink

                                     `Installing Homebrew packages`_
==================================== ===========================================

.. _Homebrew: https://github.com/Homebrew/homebrew-core/blob/master/Formula/streamlink.rb
.. _Installing Homebrew packages: https://brew.sh


Linux and BSD
-------------

.. rst-class:: table-custom-layout

==================================== ===========================================
Distribution                         Installing
==================================== ===========================================
`Arch Linux`_                        .. code-block:: bash

                                        sudo pacman -S streamlink

`Arch Linux (aur, git)`_             .. code-block:: bash

                                        git clone https://aur.archlinux.org/streamlink-git.git
                                        cd streamlink-git
                                        makepkg -si

                                     `Installing AUR packages`_

`Debian (sid, testing)`_             .. code-block:: bash

                                        sudo apt update
                                        sudo apt install streamlink

`Debian (stable)`_                   .. code-block:: bash

                                        # If you don't have Debian backports already (see link below):
                                        echo "deb http://deb.debian.org/debian buster-backports main" | sudo tee "/etc/apt/sources.list.d/streamlink.list"

                                        sudo apt update
                                        sudo apt install streamlink

                                     `Installing Debian backported packages`_

`Fedora`_                            .. code-block:: bash

                                        sudo dnf install streamlink

`Gentoo Linux`_                      .. code-block:: bash

                                        sudo emerge net-misc/streamlink

`NetBSD (pkgsrc)`_                   .. code-block:: bash

                                        cd /usr/pkgsrc/multimedia/streamlink
                                        sudo make install clean

`NixOS`_                             .. code-block:: bash

                                        nix-env -iA nixos.streamlink

                                     `NixOS channel`_

`OpenBSD`_                           .. code-block:: bash

                                        doas pkg_add streamlink

`Solus`_                             .. code-block:: bash

                                        sudo eopkg install streamlink

`Ubuntu`_                            .. code-block:: bash

                                        sudo add-apt-repository ppa:nilarimogard/webupd8
                                        sudo apt update
                                        sudo apt install streamlink

`Void`_                              .. code-block:: bash

                                        sudo xbps-install streamlink
==================================== ===========================================

.. _Arch Linux: https://www.archlinux.org/packages/community/any/streamlink/
.. _Arch Linux (aur, git): https://aur.archlinux.org/packages/streamlink-git/
.. _Debian (sid, testing): https://packages.debian.org/unstable/streamlink
.. _Debian (stable): https://packages.debian.org/unstable/streamlink
.. _Fedora: https://apps.fedoraproject.org/packages/python-streamlink
.. _Gentoo Linux: https://packages.gentoo.org/package/net-misc/streamlink
.. _NetBSD (pkgsrc): http://pkgsrc.se/multimedia/streamlink
.. _NixOS: https://github.com/NixOS/nixpkgs/tree/master/pkgs/applications/video/streamlink
.. _OpenBSD: http://openports.se/multimedia/streamlink
.. _Solus: https://dev.solus-project.com/source/streamlink/
.. _Ubuntu: http://ppa.launchpad.net/nilarimogard/webupd8/ubuntu/pool/main/s/streamlink/
.. _Void: https://github.com/void-linux/void-packages/tree/master/srcpkgs/streamlink

.. _Installing AUR packages: https://wiki.archlinux.org/index.php/Arch_User_Repository#Installing_packages
.. _Installing Debian backported packages: https://wiki.debian.org/Backports#Using_the_command_line
.. _NixOS channel: https://search.nixos.org/packages?show=streamlink&query=streamlink


Package maintainers
-------------------

.. rst-class:: table-custom-layout

==================================== ===========================================
Distribution/Platform                Maintainer
==================================== ===========================================
Arch                                 Giancarlo Razzolini <grazzolini at archlinux.org>
Arch (aur, git)                      Josip Ponjavic <josipponjavic at gmail.com>
Chocolatey                           Scott Walters <me at scowalt.com>
Debian                               Alexis Murzeau <amubtdx at gmail.com>
Fedora                               Mohamed El Morabity <melmorabity at fedoraproject.org>
Gentoo                               soredake <fdsfgs at krutt.org>
NetBSD                               Maya Rashish <maya at netbsd.org>
NixOS                                Tuomas Tynkkynen <tuomas.tynkkynen at iki.fi>
OpenBSD                              Brian Callahan <bcallah at openbsd.org>
Solus                                Bryan T. Meyers <bmeyers at datadrake.com>
Ubuntu                               Alin Andrei <andrew at webupd8.org>
Void                                 wkuipers <wietse at kuiprs.nl>
Windows binaries                     beardypig <beardypig at protonmail.com>
Windows port. version                RosadinTV <RosadinTV at outlook.com> |br|
                                     beardypig <beardypig at protonmail.com>
==================================== ===========================================


PyPI package and source code
----------------------------

If a package is not available on your platform, or if it's out of date,
Streamlink can be installed via `pip`_, the Python package manager.

In addition to using `pip`_, Streamlink can also be installed from source
via `setuptools`_ after cloning the `git`_ repository.

Before running :command:`pip`, make sure that it's the Python 3 version of `pip`_ (to check, run :command:`pip --version`).
On some systems, this isn't the case by default and an alternative, like :command:`pip3` for example, needs to be run instead.

.. note::

    On some Linux distributions, the Python headers package needs to be installed before installing Streamlink
    (``python-devel`` on RedHat, Fedora, etc.).

    Ensure that you are using an up-to-date version of `pip`_. At least version **6** is required.

.. note::

    On Linux, when not using a virtual environment, it is recommended to install custom python packages like this
    only for the current user (see the ``--user`` parameter below), since system-wide packages can cause conflicts with
    the system's regular package manager.

    Those user-packages will be installed into ``~/.local`` instead of ``/usr`` and entry-scripts for
    running the programs can be found in ``~/.local/bin``, eg. ``~/.local/bin/streamlink``.

    In order for the command line shell to be able to find these executables, the user's ``PATH`` environment variable
    needs to be extended. This can be done by adding ``export PATH="${HOME}/.local/bin:${PATH}"``
    to ``~/.profile`` or ``~/.bashrc``.

.. rst-class:: table-custom-layout

==================================== ===========================================
Version                              Installing
==================================== ===========================================
`Latest release (pip)`_              .. code-block:: bash

                                        # Current user
                                        pip install --upgrade --user streamlink

                                        # System wide
                                        sudo pip install --upgrade streamlink

`Development version (pip)`_         .. code-block:: bash

                                        # Current user
                                        pip install --upgrade --user git+https://github.com/streamlink/streamlink.git

                                        # System wide
                                        sudo pip install --upgrade git+https://github.com/streamlink/streamlink.git

`Development version (git)`_         .. code-block:: bash

                                        # Current user
                                        git clone https://github.com/streamlink/streamlink.git
                                        cd streamlink
                                        python setup.py install --user

                                        # System wide
                                        git clone https://github.com/streamlink/streamlink.git
                                        cd streamlink
                                        sudo python setup.py install
==================================== ===========================================

.. _pip: https://pip.readthedocs.org/en/latest/installing.html
.. _setuptools: https://setuptools.readthedocs.io/en/latest/
.. _git: https://git-scm.com/
.. _Latest release (pip): https://pypi.python.org/pypi/streamlink
.. _Latest release (easy_install): https://pypi.python.org/pypi/streamlink
.. _Development version (pip): https://github.com/streamlink/streamlink
.. _Development version (git): https://github.com/streamlink/streamlink

Virtual environment
^^^^^^^^^^^^^^^^^^^

Another method of installing Streamlink in a non-system-wide way is
using `virtualenv`_, which creates a user owned Python environment instead.

.. code-block:: bash

    # Create a new environment
    virtualenv ~/myenv

    # Activate the environment
    source ~/myenv/bin/activate

    # Install Streamlink in the environment
    pip install --upgrade streamlink

    # Use Streamlink in the environment
    streamlink ...

    # Deactivate the environment
    deactivate

    # Use Streamlink without activating the environment
    ~/myenv/bin/streamlink ...

.. note::

    This may also be required on some macOS versions that seem to have weird
    permission issues.

.. _virtualenv: https://virtualenv.readthedocs.io/en/latest/

Dependencies
^^^^^^^^^^^^

To install Streamlink from source you will need these dependencies.

.. rst-class:: table-custom-layout

==================================== ===========================================
Name                                 Notes
==================================== ===========================================
`Python`_                            At least version **2.7** or **3.5**.
`python-setuptools`_

**Automatically installed by the setup script**
--------------------------------------------------------------------------------
`python-futures`_                    Only needed on Python **2.7**.
`python-requests`_                   At least version **2.21.0**.
`python-singledispatch`_             Only needed on Python **2.7**.
`pycryptodome`_                      Required to play some encrypted streams
`iso-639`_                           Used for localization settings, provides language information
`iso3166`_                           Used for localization settings, provides country information
`isodate`_                           Used for MPEG-DASH streams
`PySocks`_                           Used for SOCKS Proxies
`websocket-client`_                  Used for some plugins
`shutil_get_terminal_size`_          Only needed on Python **2.7**.
`shutil_which`_                      Only needed on Python **2.7**.

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

.. _Python: https://www.python.org/
.. _python-setuptools: https://pypi.org/project/setuptools/
.. _python-futures: https://pypi.org/project/futures/
.. _python-requests: http://python-requests.org/
.. _python-singledispatch: https://pypi.org/project/singledispatch/
.. _RTMPDump: http://rtmpdump.mplayerhq.hu/
.. _pycountry: https://pypi.org/project/pycountry/
.. _pycrypto: https://www.dlitz.net/software/pycrypto/
.. _pycryptodome: https://pycryptodome.readthedocs.io/en/latest/
.. _ffmpeg: https://www.ffmpeg.org/
.. _iso-639: https://pypi.org/project/iso-639/
.. _iso3166: https://pypi.org/project/iso3166/
.. _isodate: https://pypi.org/project/isodate/
.. _PySocks: https://github.com/Anorov/PySocks
.. _websocket-client: https://pypi.org/project/websocket-client/
.. _shutil_get_terminal_size: https://pypi.org/project/backports.shutil_get_terminal_size/
.. _shutil_which: https://pypi.org/project/backports.shutil_which/


Windows binaries
----------------

.. rst-class:: table-custom-layout

==================================== ====================================
Release                              Notes
==================================== ====================================
`Stable release`_                    Download the installer from the `GitHub releases page`_.

`Development build`_                 For testing purposes only! Built each day at midnight (UTC). |br|
                                     Download the zipped installer from the `build artifacts`_ section of one of
                                     the recent scheduled builds. Build artifacts are stored by Github for 90 days. |br|
                                     See the `commit log`_ for a list of changes since the last stable release.
==================================== ====================================

.. _Stable release:
.. _GitHub releases page: https://github.com/streamlink/streamlink/releases/latest
.. _Development build:
.. _build artifacts: https://github.com/streamlink/streamlink/actions?query=event%3Aschedule+is%3Asuccess+branch%3Amaster
.. _commit log: https://github.com/streamlink/streamlink/commits/master

These installers contain:

- A compiled version of Streamlink that **does not require an existing Python
  installation**
- `RTMPDump`_ for viewing RTMP streams
- `ffmpeg`_ for muxing streams

and perform the following tasks:

- Add Streamlink to the system's list of installed applications. |br|
  An uninstaller will automatically be created during installation.
- Add Streamlink's installation directory to the system's ``PATH`` environment variable. |br|
  This allows the user to run the ``streamlink`` command globally
  from the command prompt or powershell without specifying its directory.

To build the installer on your own, ``NSIS`` and ``pynsist`` need to be installed.


Windows portable version
^^^^^^^^^^^^^^^^^^^^^^^^

.. rst-class:: table-custom-layout

==================================== ===========================================
Maintainer                           Links
==================================== ===========================================
RosadinTV                            `Latest precompiled stable release`__ |br|
                                     `Latest builder`__ |br|
                                     `More info`__

Beardypig                            `Latest precompiled stable release`__ |br|
                                     `Latest builder`__ |br|
                                     `More info`__
==================================== ===========================================

__ https://github.com/streamlink/streamlink-portable/releases/latest
__ https://github.com/streamlink/streamlink-portable/archive/master.zip
__ https://github.com/streamlink/streamlink-portable

__ https://github.com/beardypig/streamlink-portable/releases/latest
__ https://github.com/beardypig/streamlink-portable/archive/master.zip
__ https://github.com/beardypig/streamlink-portable
