Plugin sideloading
==================

Streamlink will attempt to load standalone plugins from these directories:

.. rst-class:: table-custom-layout table-custom-layout-platform-locations

.. list-table::
    :header-rows: 1
    :width: 100%

    * - Platform
      - Location
    * - Linux, BSD
      - :bdg-primary:`Path`

        - ``${XDG_DATA_HOME:-${HOME}/.local/share}/streamlink/plugins``

        :bdg-info-line:`Example`

        - ``/home/USERNAME/.local/share/streamlink/plugins``

        :bdg-danger-line:`Deprecated`

        - ``${XDG_CONFIG_HOME:-${HOME}/.config}/streamlink/plugins``
    * - macOS
      - :bdg-primary:`Path`

        - ``${HOME}/Library/Application Support/streamlink/plugins``

        :bdg-info-line:`Example`

        - ``/Users/USERNAME/Library/Application Support/streamlink/plugins``

        :bdg-danger-line:`Deprecated`

        - ``${XDG_CONFIG_HOME:-${HOME}/.config}/streamlink/plugins``
    * - Windows
      - :bdg-primary:`Path`

        - ``%APPDATA%\streamlink\plugins``

        :bdg-info-line:`Example`

        - ``C:\Users\USERNAME\AppData\Roaming\streamlink\plugins``

.. note::

    If a plugin is added with the same name as a built-in plugin, then
    the added plugin will take precedence. This is useful if you want
    to upgrade plugins independently of the Streamlink version.

    In this case, a log message will be written to log level :option:`debug <--loglevel>`:

        [session][debug] Plugin PLUGINNAME is being overridden by PATH-TO-PLUGIN-FILE

.. warning::

    If one of the sideloaded plugins fails to load, e.g. due to a
    ``SyntaxError`` being raised by the parser, then this exception won't
    get caught by Streamlink and the execution will stop, even if
    the input stream URL does not match the faulty plugin.
