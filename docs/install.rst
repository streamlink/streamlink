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

Portable                             See the `Windows binaries`_ section below

Nightly builds                       See the `Windows nightly builds`_ section below

Python pip                           See the `PyPI package and source code`_ section below

`Chocolatey`_                        .. code-block:: bat

                                        choco install streamlink

                                     `Installing Chocolatey packages`_

`Scoop`_                             .. code-block::

                                        scoop bucket add extras
                                        scoop install streamlink

                                     `Installing Scoop packages`_

`Windows Package Manager`_           .. code-block:: bat

                                        winget install streamlink

                                     `Installing Winget packages`_
==================================== ===========================================

.. _Chocolatey: https://chocolatey.org/packages/streamlink
.. _Scoop: https://scoop.sh/#/apps?q=streamlink&s=0&d=1&o=true
.. _Windows Package Manager: https://github.com/microsoft/winget-pkgs/tree/master/manifests/s/Streamlink/Streamlink
.. _Installing Chocolatey packages: https://chocolatey.org
.. _Installing Scoop packages: https://scoop.sh
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

.. _Homebrew: https://formulae.brew.sh/formula/streamlink
.. _Installing Homebrew packages: https://brew.sh


Linux and BSD
-------------

.. rst-class:: table-custom-layout

==================================== ===========================================
Distribution                         Installing
==================================== ===========================================
AppImage                             See the `AppImages`_ section below

Python pip                           See the `PyPI package and source code`_ section below

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
                                        echo "deb http://deb.debian.org/debian bullseye-backports main" | sudo tee "/etc/apt/sources.list.d/streamlink.list"

                                        sudo apt update
                                        sudo apt -t bullseye-backports install streamlink

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

`openSUSE`_                          .. code-block:: bash

                                        sudo zypper install streamlink

`Solus`_                             .. code-block:: bash

                                        sudo eopkg install streamlink

`Void`_                              .. code-block:: bash

                                        sudo xbps-install streamlink
==================================== ===========================================

.. _Arch Linux: https://www.archlinux.org/packages/community/any/streamlink/
.. _Arch Linux (aur, git): https://aur.archlinux.org/packages/streamlink-git/
.. _Debian (sid, testing): https://packages.debian.org/unstable/streamlink
.. _Debian (stable): https://packages.debian.org/unstable/streamlink
.. _Fedora: https://src.fedoraproject.org/rpms/python-streamlink
.. _Gentoo Linux: https://packages.gentoo.org/package/net-misc/streamlink
.. _NetBSD (pkgsrc): https://pkgsrc.se/multimedia/streamlink
.. _NixOS: https://github.com/NixOS/nixpkgs/tree/master/pkgs/applications/video/streamlink
.. _openSUSE: https://build.opensuse.org/package/show/multimedia:apps/streamlink
.. _Solus: https://dev.getsol.us/source/streamlink/
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
openSUSE                             Simon Puchert <simonpuchert at alice.de>
Solus                                Joey Riches <josephriches at gmail.com>
Void                                 Michal Vasilek <michal at vasilek.cz>
Windows binaries                     Sebastian Meyer <mail at bastimeyer.de>
Linux AppImages                      Sebastian Meyer <mail at bastimeyer.de>
==================================== ===========================================


Package availability
--------------------

Packaging is not done by the Streamlink maintainers themselves except for
the `PyPI package <PyPI package and source code_>`_,
the `Windows installers + portable builds <Windows binaries_>`_,
and the `Linux AppImages <AppImages_>`_.

If a packaged release of Streamlink is not available for your operating system / distro or your system's architecture,
or if it's out of date or broken, then please contact the respective package maintainers or package-repository maintainers
of your operating system / distro, as it's up to them to add, update, or fix those packages.

Users of glibc-based Linux distros can find up-to-date Streamlink releases via the available `AppImages`_.

Please open an issue or pull request on GitHub if an **available**, **maintained** and **up-to-date** package is missing
from the install docs.


PyPI package and source code
----------------------------

If a package is not available on your platform, or if it's out of date,
Streamlink can be installed via `pip`_, the Python package manager.

Before running :command:`pip`, make sure that it's the Python 3 version of `pip`_ (to check, run :command:`pip --version`).
On some systems, this isn't the case by default and an alternative, like :command:`pip3` for example, needs to be run instead.

.. note::

    On some Linux distributions, the Python headers package needs to be installed before installing Streamlink
    (``python-devel`` on RedHat, Fedora, etc.).

    Ensure that you are using an up-to-date version of `pip`_. At least version **6** is required.

.. warning::

    On Linux, when not using a virtual environment, it is recommended to **install custom python packages like this
    only for the current user** (see the ``--user`` parameter below), since system-wide packages can cause conflicts with
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
`Latest release`_                    .. code-block:: bash

                                        pip install --user --upgrade streamlink

`Master branch`_                     .. code-block:: bash

                                        pip install --user --upgrade git+https://github.com/streamlink/streamlink.git

`Specific tag/branch or commit`_     .. code-block:: bash

                                        pip install --user --upgrade git+https://github.com/USERNAME/streamlink.git@BRANCH-OR-COMMIT
==================================== ===========================================

.. _pip: https://pip.pypa.io/en/stable/
.. _Latest release: https://pypi.python.org/pypi/streamlink
.. _Master branch: https://github.com/streamlink/streamlink/commits/master
.. _Specific tag/branch or commit: https://pip.pypa.io/en/stable/reference/pip_install/#git

Virtual environment
-------------------

Another method of installing Streamlink in a non-system-wide way is
using `virtualenv`_, which creates a user owned Python environment instead.

Install with ``virtualenv`` and ``pip`` commands
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Create a new environment
    virtualenv ~/myenv

    # Activate the environment
    source ~/myenv/bin/activate

    # *Either* install the latest Streamlink release from PyPI in the virtual environment
    pip install --upgrade streamlink

    # *Or*, install the most up-to-date development version from master on GitHub
    pip install --upgrade git+https://github.com/streamlink/streamlink.git

    # Use Streamlink in the environment
    streamlink ...

    # Deactivate the environment
    deactivate

    # Use Streamlink without activating the environment
    ~/myenv/bin/streamlink ...

Install with ``pipx`` command
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `pipx`_ command combines the functionality of the ``virtualenv`` and ``pip`` commands. It may be necessary to
install it first, either with a system package manager, or using ``pip``, as detailed in the `documentation <pipx_>`_.

.. code-block:: bash

    # *Either* install the latest Streamlink release from PyPI in a virtual environment
    pipx install streamlink

    # *Or*, install the most up-to-date development version from master on GitHub
    pipx install git+https://github.com/streamlink/streamlink.git

    # Use Streamlink
    streamlink ...

.. _virtualenv: https://virtualenv.readthedocs.io/en/latest/
.. _pipx: https://pypa.github.io/pipx/

Dependencies
^^^^^^^^^^^^

To install Streamlink from source you will need these dependencies.

Since :ref:`4.0.0 <changelog:streamlink 4.0.0 (2022-05-01)>`,
Streamlink defines a `build system <pyproject.toml_>`__ according to `PEP-517`_ / `PEP-518`_.

.. rst-class:: table-custom-layout table-custom-layout-dependencies

========= ========================= ===========================================
Type      Name                       Notes
========= ========================= ===========================================
python    `Python`_                 At least version **3.7**.

build     `setuptools`_             At least version **45.0.0**. |br| Used as build backend.
build     `wheel`_                  Used by the build frontend for creating Python wheels.
build     `versioningit`_           At least version **2.0.0**. |br| Used for generating the version string from git
                                    when building, or when running in an editable install.

runtime   `certifi`_                Used for loading the CA bundle extracted from the Mozilla Included CA Certificate List
runtime   `isodate`_                Used for parsing ISO8601 strings
runtime   `lxml`_                   Used for processing HTML and XML data
runtime   `pycountry`_              Used for localization settings, provides country and language data
runtime   `pycryptodome`_           Used for decrypting encrypted streams
runtime   `PySocks`_                Used for SOCKS Proxies
runtime   `requests`_               Used for making any kind of HTTP/HTTPS request
runtime   `urllib3`_                Used internally by `requests`_, defined as direct dependency
runtime   `websocket-client`_       Used for making websocket connections

optional  `FFmpeg`_                 Required for `muxing`_ multiple video/audio/subtitle streams into a single output stream.

                                     - DASH streams with video and audio content always have to get remuxed.
                                     - HLS streams optionally need to get remuxed depending on the stream selection.
========= ========================= ===========================================

.. _pyproject.toml: https://github.com/streamlink/streamlink/blob/master/pyproject.toml
.. _PEP-517: https://peps.python.org/pep-0517/
.. _PEP-518: https://peps.python.org/pep-0518/

.. _Python: https://www.python.org/
.. _setuptools: https://setuptools.pypa.io/en/latest/
.. _wheel: https://wheel.readthedocs.io/en/stable/
.. _versioningit: https://versioningit.readthedocs.io/en/stable/

.. _certifi: https://certifiio.readthedocs.io/en/latest/
.. _isodate: https://pypi.org/project/isodate/
.. _lxml: https://lxml.de/
.. _pycountry: https://pypi.org/project/pycountry/
.. _pycryptodome: https://pycryptodome.readthedocs.io/en/latest/
.. _PySocks: https://github.com/Anorov/PySocks
.. _requests: https://requests.readthedocs.io/en/latest/
.. _urllib3: https://urllib3.readthedocs.io/en/stable/
.. _websocket-client: https://pypi.org/project/websocket-client/

.. _FFmpeg: https://www.ffmpeg.org/
.. _muxing: https://en.wikipedia.org/wiki/Multiplexing#Video_processing


Windows binaries
----------------

Windows installers and portable builds for Streamlink can be found at `streamlink/windows-builds`_,
with support for different architectures and different Python versions.

These installers and portable builds contain:

- an embedded Python version, built at `streamlink/python-windows-embed`_
- Streamlink and its dependencies
- FFmpeg, required for muxing streams, built at `streamlink/FFmpeg-Builds`_

and they are available in the following flavors:

- Python 3.10 - x86_64 (64 bit)
- Python 3.10 - x86 (32 bit)
- Python 3.8 - x86_64 (64 bit) - for Windows 7
- Python 3.8 - x86 (32 bit) - for Windows 7

For further information, please see the README in the `streamlink/windows-builds`_ repository.

Windows stable builds
^^^^^^^^^^^^^^^^^^^^^

Stable installers and stable portable builds of Streamlink's latest release can be
`downloaded from the releases page of the streamlink/windows-builds <windows-stable_>`_ repository.

Windows nightly builds
^^^^^^^^^^^^^^^^^^^^^^

Built once each day at midnight UTC from Streamlink's master branch. |br|
This includes the most recent changes, but is not considered "stable". |br|
Download from the build-artifacts of the `scheduled nightly build runs <windows-nightly_>`_ (requires a GitHub login). |br|
See the `commit log <streamlink-master_>`_ of Steamlink's master branch for all the recent changes.

.. _streamlink/windows-builds: https://github.com/streamlink/windows-builds
.. _streamlink/python-windows-embed: https://github.com/streamlink/python-windows-embed
.. _streamlink/FFmpeg-Builds: https://github.com/streamlink/FFmpeg-Builds
.. _windows-stable: https://github.com/streamlink/windows-builds/releases
.. _windows-nightly: https://github.com/streamlink/windows-builds/actions?query=event%3Aschedule+is%3Asuccess+branch%3Amaster
.. _streamlink-master: https://github.com/streamlink/streamlink/commits/master


AppImages
---------

Download & Setup
^^^^^^^^^^^^^^^^

First, download the latest `Streamlink AppImage`_ which matches your system's
architecture from the `Streamlink AppImage releases page`_. Then simply set the
executable flag and run the app.

.. code-block:: bash

   # Set the executable flag. Note that all AppImage release file names include
   # the release version, Python version, platform name and CPU architecture
   chmod +x streamlink-2.0.0-1-cp39-cp39-manylinux2014_x86_64.AppImage

   # Run the Streamlink AppImage with any parameter supported by Streamlink
   ./streamlink-2.0.0-1-cp39-cp39-manylinux2014_x86_64.AppImage --version

What are AppImages?
^^^^^^^^^^^^^^^^^^^

AppImages are portable apps for Linux which are independent of the distro and
package management.

Note: Check out `AppImageLauncher`_, which automates the setup and system
integration of AppImages. AppImageLauncher may also be available via your
distro's package management.

Additional information, like for example how to inspect the AppImage contents or
how to extract the contents if `FUSE`_ is not available on your system, can be
found in the `AppImage documentation`_.

.. _Streamlink AppImage: https://github.com/streamlink/streamlink-appimage
.. _Streamlink AppImage releases page: https://github.com/streamlink/streamlink-appimage/releases
.. _AppImageLauncher: https://github.com/TheAssassin/AppImageLauncher
.. _FUSE: https://docs.appimage.org/user-guide/troubleshooting/fuse.html
.. _AppImage documentation: https://docs.appimage.org/user-guide/run-appimages.html
