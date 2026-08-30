Configuration file
==================

Writing the command-line options every time is inconvenient, that's why Streamlink
is capable of reading options from a configuration file instead.

Location
--------

Streamlink will look for config files in different locations depending on
your platform:

.. rst-class:: table-custom-layout table-custom-layout-platform-locations

.. list-table::
    :header-rows: 1
    :width: 100%

    * - Platform
      - Location
    * - Linux, BSD
      - | **Path**
        | ``${XDG_CONFIG_HOME:-${HOME}/.config}/streamlink/config``
        | **Example**
        | ``/home/USERNAME/.config/streamlink/config``
    * - macOS
      - | **Path**
        | ``${HOME}/Library/Application Support/streamlink/config``
        | **Example**
        | ``/Users/USERNAME/Library/Application Support/streamlink/config``
    * - Windows
      - | **Path**
        | ``%APPDATA%\streamlink\config``
        | **Example**
        | ``C:\Users\USERNAME\AppData\Roaming\streamlink\config``

You can also specify the location yourself using the :option:`--config` option.

Loading config files can be suppressed using the :option:`--no-config` option.

.. warning::

  Streamlink's Windows installers automatically create a config file if it doesn't exist yet, but on any
  other platform or installation method, you must create the file yourself.

.. note::

   The ``XDG_CONFIG_HOME`` environment variable is part of the `XDG base directory specification`_ (`Arch Linux Wiki <xdg-base-dir-arch-wiki_>`_).

   The ``${VARIABLENAME:-DEFAULTVALUE}`` syntax is explained `here <Parameter expansion_>`_.

.. _XDG base directory specification: https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
.. _xdg-base-dir-arch-wiki: https://wiki.archlinux.org/title/XDG_Base_Directory
.. _Parameter expansion: https://www.gnu.org/software/bash/manual/bash.html#Shell-Parameter-Expansion


Syntax
------

The config file is a simple text file and should contain one
:ref:`command-line option <cli:Command-line usage>` (omitting the leading dashes) per
line in the format::

  option=value

or for an option without value::

  option

.. warning::

    Any quotes will be used as part of the argument value.

Example
^^^^^^^

.. code-block:: bash

    # Player options
    player=mpv
    player-args=--cache 2048
    player-no-close


Plugin specific configuration file
----------------------------------

You may want to use specific options for some plugins only. This can be accomplished by setting these options
in plugin-specific config files. Options defined in plugin-specific config files override options of the main
config file when a URL matching the plugin is used.

Streamlink expects these configs to be named like the main config but with ``.<plugin name>`` attached to the end.

.. rst-class:: table-custom-layout table-custom-layout-platform-locations

.. list-table::
    :header-rows: 1
    :width: 100%

    * - Platform
      - Location
    * - Linux, BSD
      - | **Path**
        | ``${XDG_CONFIG_HOME:-${HOME}/.config}/streamlink/config.pluginname``
        | **Example**
        | ``/home/USERNAME/.config/streamlink/config.twitch``
    * - macOS
      - | **Path**
        | ``${HOME}/Library/Application Support/streamlink/config.pluginname``
        | **Example**
        | ``/Users/USERNAME/Library/Application Support/streamlink/config.twitch``
    * - Windows
      - | **Path**
        | ``%APPDATA%\streamlink\config.pluginname``
        | **Example**
        | ``C:\Users\USERNAME\AppData\Roaming\streamlink\config.twitch``

Have a look at the :ref:`list of plugins <plugins:Plugins>`, or
check the :option:`--plugins` option to see the name of each built-in plugin.
