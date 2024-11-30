.. |br| raw:: html

  <br />

Installation
============

.. sphinx-design currently doesn't support autosectionlabel, so set labels for the following sections explicitly

.. grid:: 4
    :padding: 0
    :class-container: installation-grid

    .. grid-item-card::
        :link: windows
        :link-type: ref
        :link-alt: Windows
        :padding: 3
        :text-align: center

        :fab:`windows`

    .. grid-item-card::
        :link: macos
        :link-type: ref
        :link-alt: macOS
        :padding: 3
        :text-align: center

        :fab:`apple`

    .. grid-item-card::
        :link: linux-and-bsd
        :link-type: ref
        :link-alt: Linux and BSD
        :padding: 3
        :text-align: center

        :fab:`linux`

    .. grid-item-card::
        :link: pypi-package-and-source-code
        :link-type: ref
        :link-alt: PyPI package and source code
        :padding: 3
        :text-align: center

        :fab:`python`


.. _windows:

Windows
-------

.. list-table::
    :header-rows: 1
    :class: table-custom-layout

    * - Method
      - Installing
    * - :octicon:`verified` Installers
      - See the `Windows binaries`_ section below
    * - :octicon:`verified` Portable
      - See the `Windows binaries`_ section below
    * - :octicon:`verified` Nightly builds
      - See the `Windows binaries`_ section below
    * - :octicon:`verified` Python pip
      - See the `PyPI package and source code`_ section below
    * - :octicon:`package` `Chocolatey`_
      - .. code-block:: bat

            choco install streamlink

        `Installing Chocolatey packages`_
    * - :octicon:`package-dependents` `Scoop`_
      - .. code-block::

            scoop bucket add extras
            scoop install streamlink

        `Installing Scoop packages`_
    * - :octicon:`package-dependents` `Windows Package Manager`_
      - .. code-block:: bat

            winget install streamlink

        `Installing Winget packages`_

.. _Chocolatey: https://chocolatey.org/packages/streamlink
.. _Scoop: https://scoop.sh/#/apps?q=streamlink&s=0&d=1&o=true
.. _Windows Package Manager: https://github.com/microsoft/winget-pkgs/tree/master/manifests/s/Streamlink/Streamlink
.. _Installing Chocolatey packages: https://chocolatey.org
.. _Installing Scoop packages: https://scoop.sh
.. _Installing Winget packages: https://docs.microsoft.com/en-us/windows/package-manager/


.. _macos:

macOS
-----

.. list-table::
    :header-rows: 1
    :class: table-custom-layout

    * - Method
      - Installing
    * - :octicon:`verified` Python pip
      - See the `PyPI package and source code`_ section below
    * - :octicon:`package-dependents` `Homebrew`_
      - .. code-block:: bash

            brew install streamlink

        `Installing Homebrew packages`_

.. _Homebrew: https://formulae.brew.sh/formula/streamlink
.. _Installing Homebrew packages: https://brew.sh


.. _linux-and-bsd:

Linux and BSD
-------------

.. list-table::
    :header-rows: 1
    :class: table-custom-layout

    * - Method / Distribution
      - Installing
    * - :octicon:`verified` AppImage
      - See the `Linux AppImages`_ section below
    * - :octicon:`verified` AppImage nightly builds
      - See the `Linux AppImages`_ section below
    * - :octicon:`verified` Python pip
      - See the `PyPI package and source code`_ section below
    * - :octicon:`package-dependents` `Alpine Linux (edge)`_
      - .. code-block:: bash

            sudo apk add streamlink
    * - :octicon:`package-dependents` `ALT Linux (Sisyphus)`_
      - .. code-block:: bash

            sudo apt-get install streamlink
    * - :octicon:`package-dependents` `Arch Linux`_
      - .. code-block:: bash

            sudo pacman -S streamlink
    * - :octicon:`package-dependents` `Arch Linux (aur, git)`_
      - .. code-block:: bash

            git clone https://aur.archlinux.org/streamlink-git.git
            cd streamlink-git
            makepkg -si

        `Installing AUR packages`_
    * - :octicon:`package-dependents` `Debian (sid, testing)`_
      - .. code-block:: bash

            sudo apt update
            sudo apt install streamlink
    * - :octicon:`package-dependents` `Debian (stable)`_
      - .. code-block:: bash

            # If you don't have Debian backports already (see link below):
            echo "deb http://deb.debian.org/debian bookworm-backports main" | sudo tee "/etc/apt/sources.list.d/streamlink.list"

            sudo apt update
            sudo apt -t bookworm-backports install streamlink

        `Installing Debian backported packages`_
    * - :octicon:`package-dependents` `Fedora`_
      - .. code-block:: bash

            sudo dnf install streamlink
    * - :octicon:`package-dependents` `FreeBSD (pkg)`_
      - .. code-block:: bash

            pkg install multimedia/streamlink

    * - :octicon:`package-dependents` `FreeBSD (ports)`_
      - .. code-block:: bash

            cd /usr/ports/multimedia/streamlink
            make config install clean
    * - :octicon:`package-dependents` `Gentoo Linux`_
      - .. code-block:: bash

            sudo emerge net-misc/streamlink
    * - :octicon:`package-dependents` `NixOS`_
      - .. code-block:: bash

            nix-env -iA nixos.streamlink

        `NixOS channel`_
    * - :octicon:`package-dependents` `openSUSE`_
      - .. code-block:: bash

            sudo zypper install streamlink
    * - :octicon:`package-dependents` `Ubuntu`_
      - Not recommended.

        Ubuntu inherits the ``streamlink`` package from Debian, but doesn't maintain or update it.

        See `Package availability`_.
    * - :octicon:`package-dependents` `Solus`_
      - .. code-block:: bash

            sudo eopkg install streamlink
    * - :octicon:`package-dependents` `Void`_
      - .. code-block:: bash

            sudo xbps-install streamlink

.. _Alpine Linux (edge): https://pkgs.alpinelinux.org/packages?name=streamlink
.. _ALT Linux (Sisyphus): https://packages.altlinux.org/en/sisyphus/srpms/streamlink/
.. _Arch Linux: https://archlinux.org/packages/extra/any/streamlink/
.. _Arch Linux (aur, git): https://aur.archlinux.org/packages/streamlink-git/
.. _Debian (sid, testing): https://packages.debian.org/sid/streamlink
.. _Debian (stable): https://packages.debian.org/bookworm-backports/streamlink
.. _Fedora: https://src.fedoraproject.org/rpms/python-streamlink
.. _FreeBSD (pkg): https://ports.freebsd.org/cgi/ports.cgi?query=streamlink&stype=name
.. _FreeBSD (ports): https://www.freshports.org/multimedia/streamlink
.. _Gentoo Linux: https://packages.gentoo.org/package/net-misc/streamlink
.. _NixOS: https://github.com/NixOS/nixpkgs/tree/master/pkgs/by-name/st/streamlink
.. _openSUSE: https://build.opensuse.org/package/show/multimedia:apps/streamlink
.. _Ubuntu: https://packages.ubuntu.com/noble/streamlink
.. _Solus: https://github.com/getsolus/packages/tree/main/packages/s/streamlink
.. _Void: https://github.com/void-linux/void-packages/tree/master/srcpkgs/streamlink

.. _Installing AUR packages: https://wiki.archlinux.org/index.php/Arch_User_Repository
.. _Installing Debian backported packages: https://wiki.debian.org/Backports
.. _NixOS channel: https://search.nixos.org/packages?show=streamlink&query=streamlink


Package maintainers
-------------------

.. list-table::
    :header-rows: 1
    :class: table-custom-layout

    * - Distribution / Platform
      - Maintainer
    * - Alpine Linux
      - Hoang Nguyen <folliekazetani at protonmail.com>
    * - ALT Linux
      - Vitaly Lipatov <lav at altlinux.ru>
    * - Arch
      - Giancarlo Razzolini <grazzolini at archlinux.org>
    * - Arch (aur, git)
      - Josip Ponjavic <josipponjavic at gmail.com>
    * - Chocolatey
      - Scott Walters <me at scowalt.com>
    * - Debian
      - Alexis Murzeau <amubtdx at gmail.com>
    * - Fedora
      - Mohamed El Morabity <melmorabity at fedoraproject.org>
    * - FreeBSD
      - Takefu <takefu at airport.fm>
    * - Gentoo
      - soredake <fdsfgs at krutt.org>
    * - NixOS
      - Tuomas Tynkkynen <tuomas.tynkkynen at iki.fi>
    * - openSUSE
      - Simon Puchert <simonpuchert at alice.de>
    * - Solus
      - Joey Riches <josephriches at gmail.com>
    * - Void
      - Tom Strausbaugh <tstrausbaugh at straustech.net>
    * - Windows binaries
      - Sebastian Meyer <mail at bastimeyer.de>
    * - Linux AppImages
      - Sebastian Meyer <mail at bastimeyer.de>


Package availability
--------------------

Packaging is not done by the Streamlink maintainers themselves except for
the `PyPI package <pypi-package-and-source-code_>`_,
the `Windows installers + portable builds <Windows binaries_>`_,
and the `Linux AppImages <Linux AppImages_>`_.

If a packaged release of Streamlink is not available for your operating system / distro or your system's architecture,
or if it's out of date or broken, then please contact the respective package maintainers or package-repository maintainers
of your operating system / distro, as it's up to them to add, update, or fix those packages.

Users of glibc-based Linux distros can find up-to-date Streamlink releases via the available `AppImages <Linux AppImages_>`_.

Please open an issue or pull request on GitHub if an **available**, **maintained** and **up-to-date** package is missing
from the install docs.


.. _pypi-package-and-source-code:

PyPI package and source code
----------------------------

If a package is not available on your platform, or if it's out of date,
then Streamlink can be installed via `pip`_, the Python package manager.

Before running :command:`pip`, make sure that it's the Python 3 version of `pip`_ (to check, run :command:`pip --version`).
On some systems, this isn't the case by default and an alternative, like :command:`pip3` for example, needs to be run instead.

.. warning::

    On Linux, when not using a virtual environment, it is recommended to **install custom python packages like this
    only for the current user** (see the ``--user`` parameter below), since system-wide packages can cause conflicts with
    the system's regular package manager.

    Those user-packages will be installed into ``~/.local`` instead of ``/usr``, and entry-scripts for
    running the programs can be found in ``~/.local/bin``, e.g. ``~/.local/bin/streamlink``.

    In order for the command line shell to be able to find these executables, the user's ``PATH`` environment variable
    needs to be extended. This can be done by adding ``export PATH="${HOME}/.local/bin:${PATH}"``
    to ``~/.profile`` or ``~/.bashrc``.

.. list-table::
    :header-rows: 1
    :class: table-custom-layout

    * - Version
      - Installing
    * - :octicon:`verified` `Latest release`_
      - .. code-block:: bash

            pip install --user -U streamlink
    * - :octicon:`verified` `Master branch`_
      - .. code-block:: bash

            pip install --user -U git+https://github.com/streamlink/streamlink.git
    * - :octicon:`unverified` `Specific tag/branch/commit`_
      - .. code-block:: bash

            pip install --user -U git+https://github.com/USERNAME/streamlink.git@REVISION

.. _pip: https://pip.pypa.io/en/stable/
.. _Latest release: https://pypi.python.org/pypi/streamlink
.. _Master branch: https://github.com/streamlink/streamlink/commits/master
.. _Specific tag/branch/commit: https://pip.pypa.io/en/stable/reference/pip_install/#git


Virtual environment
-------------------

Another way of installing Streamlink in a non-system-wide way is using the `venv`_ or `virtualenv`_ Python packages,
which both create a user-owned Python environment which is isolated from the system's main Python package environment.

While `venv`_ is part of Python's standard library since ``3.3``, `virtualenv`_ is the project which `venv`_ was built from,
but it first needs to be installed, either via `pip`_ or from the system's package manager. It also implements more features,
so depending on your needs, you may want to use `virtualenv`_ instead of `venv`_.

Install using ``venv`` and ``pip``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Create a new environment
    python -m venv ~/myenv

    # Activate the environment
    # note: non-POSIX compliant shells like FISH or PowerShell have different activation script file names
    # note: on Windows, the `bin` subdirectory is called `Scripts`
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

Install using ``pipx``
^^^^^^^^^^^^^^^^^^^^^^

The `pipx`_ project combines the functionality of both ``venv`` and ``pip``. It may be necessary to
install it first, either with a system package manager, or using ``pip``, as detailed in the `documentation <pipx_>`_.

.. code-block:: bash

    # *Either* install the latest Streamlink release from PyPI in a virtual environment
    pipx install streamlink

    # *Or*, install the most up-to-date development version from master on GitHub
    pipx install git+https://github.com/streamlink/streamlink.git

    # Use Streamlink
    streamlink ...

.. _venv: https://docs.python.org/3/library/venv.html
.. _virtualenv: https://virtualenv.pypa.io/en/stable/
.. _pipx: https://pypa.github.io/pipx/


Source distribution
-------------------

In addition to the pre-built wheels uploaded to PyPI, Streamlink's source distribution tarballs get uploaded
to both PyPI and GitHub releases. These tarballs are meant for packagers and are signed using the following PGP key:

:bdg-link-primary-line:`44448A298D5C3618 <https://keyserver.ubuntu.com/pks/lookup?search=44448A298D5C3618&fingerprint=on&op=index>`

Please be aware that PyPI has dropped support for uploading new release file signatures in May 2023, so those can only be found
on `GitHub releases`_ now.

See the `Dependencies`_ section down below for the required build- and runtime-requirements.

.. warning::

    Please avoid building Streamlink from tarballs generated by GitHub from (tagged) git commits,
    as they are lacking the built-in release version string. The ``versioningit`` build-requirement also won't be able
    to find the correct version, as the content is not part of a git repository.

    Instead, build from Streamlink's signed source-distribution tarballs which are uploaded to PyPI and GitHub releases,
    or from the cloned git repository.

.. _GitHub Releases: https://github.com/streamlink/streamlink/releases

Dependencies
^^^^^^^^^^^^

To install Streamlink from source, you will need these dependencies.

Since :ref:`4.0.0 <changelog:streamlink 4.0.0 (2022-05-01)>`,
Streamlink defines a `build system <pyproject.toml_>`__ according to `PEP-517`_ / `PEP-518`_.

.. list-table::
    :header-rows: 1
    :class: table-custom-layout table-custom-layout-dependencies

    * - Type
      - Name
      - Notes
    * - python
      - `Python`_
      - At least version **3.9**
    * - build
      - `setuptools`_
      - At least version **65.6.0** |br|
        Used as build backend
    * - build
      - `wheel`_
      - Used by the build frontend for creating Python wheels
    * - build
      - `versioningit`_
      - At least version **2.0.0** |br|
        Used for generating the version string from git when building, or when running in an editable install.
        Not needed when building wheels and installing from the source distribution.
    * - runtime
      - `certifi`_
      - Used for loading the CA bundle extracted from the Mozilla Included CA Certificate List
    * - runtime
      - `exceptiongroup`_
      - Only required when ``python_version<"3.11"`` |br|
        Used for ``ExceptionGroup`` handling
    * - runtime
      - `isodate`_
      - Used for parsing ISO8601 strings
    * - runtime
      - `lxml`_
      - Used for processing HTML and XML data
    * - runtime
      - `pycountry`_
      - Used for localization settings, provides country and language data
    * - runtime
      - `pycryptodome`_
      - Used for decrypting encrypted streams
    * - runtime
      - `PySocks`_
      - Used for SOCKS Proxies
    * - runtime
      - `requests`_
      - Used for making any kind of HTTP/HTTPS request
    * - runtime
      - `trio`_
      - Used for async concurrency and I/O in some parts of Streamlink
    * - runtime
      - `trio-websocket`_
      - Used for WebSocket connections on top of the async trio framework
    * - runtime
      - `urllib3`_
      - Used internally by `requests`_, defined as direct dependency
    * - runtime
      - `websocket-client`_
      - Used for making websocket connections
    * - optional
      - `FFmpeg`_
      - Required for `muxing`_ multiple video/audio/subtitle streams into a single output stream.

        - DASH streams with video and audio content always have to get remuxed.
        - HLS streams optionally need to get remuxed depending on the stream selection.

.. _pyproject.toml: https://github.com/streamlink/streamlink/blob/master/pyproject.toml
.. _PEP-517: https://peps.python.org/pep-0517/
.. _PEP-518: https://peps.python.org/pep-0518/

.. _Python: https://www.python.org/
.. _setuptools: https://setuptools.pypa.io/en/latest/
.. _wheel: https://wheel.readthedocs.io/en/stable/
.. _versioningit: https://versioningit.readthedocs.io/en/stable/

.. _certifi: https://certifiio.readthedocs.io/en/latest/
.. _exceptiongroup: https://github.com/agronholm/exceptiongroup
.. _isodate: https://pypi.org/project/isodate/
.. _lxml: https://lxml.de/
.. _pycountry: https://pypi.org/project/pycountry/
.. _pycryptodome: https://pycryptodome.readthedocs.io/en/latest/
.. _PySocks: https://github.com/Anorov/PySocks
.. _requests: https://requests.readthedocs.io/en/latest/
.. _trio: https://trio.readthedocs.io/en/stable/
.. _trio-websocket: https://trio-websocket.readthedocs.io/en/stable/
.. _urllib3: https://urllib3.readthedocs.io/en/stable/
.. _websocket-client: https://pypi.org/project/websocket-client/

.. _FFmpeg: https://www.ffmpeg.org/
.. _muxing: https://en.wikipedia.org/wiki/Multiplexing#Video_processing


Windows binaries
----------------

.. grid:: 2
    :padding: 0
    :class-container: grid-with-icons

    .. grid-item-card::
        :padding: 3
        :link: https://github.com/streamlink/windows-builds/releases
        :link-alt: Windows stable releases
        :text-align: center

        **Windows stable releases**
        ^^^
        :fas:`download` GitHub releases page

        The most recent Streamlink release

    .. grid-item-card::
        :padding: 3
        :link: https://github.com/streamlink/windows-builds/actions?query=event%3Aschedule+is%3Asuccess+branch%3Amaster
        :link-alt: Windows nightly builds
        :text-align: center

        **Windows nightly builds**
        ^^^
        :fas:`download` GitHub actions build artifacts

        Built once each day at midnight UTC |br| :sub:`GitHub account required`

**Flavors**

.. grid:: 2
    :padding: 0
    :class-container: grid-with-icons

    .. grid-item-card::
        :padding: 3
        :class-header: sd-text-center
        :class-body: sd-py-0
        :class-footer: sd-text-center sd-bg-transparent sd-border-0 sd-pt-0 sd-pb-3

        :fas:`gears` **Installer**
        ^^^

        - Windows 10+
        - Adds itself to the system's ``PATH`` env var
        - Automatically creates a :ref:`config file <cli/config:Configuration file>`
        - Sets :option:`--ffmpeg-ffmpeg` in config file

        +++
        :bdg-link-success-line:`x86_64 <https://github.com/streamlink/windows-builds/releases>`

    .. grid-item-card::
        :padding: 3
        :class-header: sd-text-center
        :class-body: sd-py-0
        :class-footer: sd-text-center sd-bg-transparent sd-border-0 sd-pt-0 sd-pb-3

        :fas:`file-zipper` **Portable archive**
        ^^^

        - Windows 10+
        - No :ref:`config file <cli/config:Configuration file>` created automatically
        - :option:`--ffmpeg-ffmpeg` must be set manually
        - No pre-compiled Python bytecode

        +++
        :bdg-link-success-line:`x86_64 <https://github.com/streamlink/windows-builds/releases>`

**Contents**

.. grid:: 3
    :padding: 0
    :class-container: grid-with-images

    .. grid-item-card::
        :padding: 3
        :link: https://github.com/streamlink/python-windows-embed
        :link-alt: Embedded Python build
        :text-align: center

        .. image:: _static/icon-python.svg
            :alt: Python

        Python |br| :sub:`embedded build`

    .. grid-item-card::
        :padding: 3
        :link: https://github.com/streamlink/streamlink
        :link-alt: Streamlink and its runtime dependencies
        :text-align: center

        .. image:: _static/icon.svg
            :alt: Streamlink

        Streamlink |br| :sub:`and dependencies`

    .. grid-item-card::
        :padding: 3
        :link: https://github.com/streamlink/FFmpeg-Builds
        :link-alt: FFmpeg, required for muxing streams
        :text-align: center

        .. image:: _static/icon-ffmpeg.svg
            :alt: FFmpeg

        FFmpeg |br| :sub:`for muxing streams`


Linux AppImages
---------------

.. grid:: 2
    :padding: 0
    :class-container: grid-with-icons

    .. grid-item-card::
        :padding: 3
        :link: https://github.com/streamlink/streamlink-appimage/releases
        :link-alt: AppImage stable releases
        :text-align: center

        **AppImage stable releases**
        ^^^
        :fas:`download` GitHub releases page

        The most recent Streamlink release

    .. grid-item-card::
        :padding: 3
        :link: https://github.com/streamlink/streamlink-appimage/actions?query=event%3Aschedule+is%3Asuccess+branch%3Amaster
        :link-alt: AppImage nightly builds
        :text-align: center

        **AppImage nightly builds**
        ^^^
        :fas:`download` GitHub actions build artifacts

        Built once each day at midnight UTC |br| :sub:`GitHub account required`

**Architectures**

.. grid:: 2
    :padding: 0

    .. grid-item-card::
        :padding: 3
        :text-align: center

        :bdg-link-success-line:`x86_64 <https://github.com/streamlink/streamlink-appimage/releases>`

    .. grid-item-card::
        :padding: 3
        :text-align: center

        :bdg-link-success-line:`aarch64 <https://github.com/streamlink/streamlink-appimage/releases>`

**Contents**

.. grid:: 2
    :padding: 0
    :class-container: grid-with-images

    .. grid-item-card::
        :padding: 3
        :link: https://github.com/streamlink/appimage-buildenv
        :link-alt: Python from the pypa/manulinux docker images
        :text-align: center

        .. image:: _static/icon-python.svg
            :alt: Python

        Python |br| :sub:`from the pypa/manylinux docker images`

    .. grid-item-card::
        :padding: 3
        :link: https://github.com/streamlink/streamlink
        :link-alt: Streamlink and its runtime dependencies
        :text-align: center

        .. image:: _static/icon.svg
            :alt: Streamlink

        Streamlink |br| :sub:`and dependencies`

**How-To**

1. Verify that the system is running on at least
   `glibc <glibc-wikipedia_>`_ `2.28 (Aug 2018) <glibc-release-distro-mapping_>`_ (see :command:`ld.so --version`)

2. Download the AppImage file matching the system's CPU architecture (see :command:`uname --machine`)

3. Set the executable flag via a file browser or :command:`chmod +x filename` from a command-line shell

   .. code-block:: bash

      # AppImage file names include the release version,
      # the Python version, platform name and CPU architecture
      chmod +x streamlink-7.0.0-1-cp312-cp312-manylinux_2_28_x86_64.AppImage

4. Run the AppImage with any command-line parameters supported by Streamlink

   .. code-block:: bash

      ./streamlink-7.0.0-1-cp312-cp312-manylinux_2_28_x86_64.AppImage --loglevel=debug

.. _glibc-wikipedia: https://en.wikipedia.org/wiki/Glibc
.. _glibc-release-distro-mapping: https://sourceware.org/glibc/wiki/Release#Distribution_Branch_Mapping


What are AppImages?
^^^^^^^^^^^^^^^^^^^

AppImages are portable applications which are independent of the Linux distribution in use and its package management.
Just set the executable flag on the AppImage file and run it.

The only requirement is having `FUSE`_ installed for being able to mount the contents of the AppImage's SquashFS,
which is done automatically. Also, only glibc-based systems are currently supported.

Note: Check out `AppImageLauncher`_, which automates the setup and system
integration of AppImages. AppImageLauncher may also be available via your
distro's package management.

Additional information, like for example how to inspect the AppImage contents or
how to extract the contents if `FUSE`_ is not available on your system, can be
found in the `AppImage documentation`_.

.. _AppImageLauncher: https://github.com/TheAssassin/AppImageLauncher
.. _FUSE: https://docs.appimage.org/user-guide/troubleshooting/fuse.html
.. _AppImage documentation: https://docs.appimage.org/user-guide/run-appimages.html

.. _streamlink-master: https://github.com/streamlink/streamlink/commits/master
