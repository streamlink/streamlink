Plugin sideloading
==================

Streamlink will attempt to load standalone plugins from these directories:

.. rst-class:: table-custom-layout table-custom-layout-platform-locations

================= ====================================================
Platform          Location
================= ====================================================
Linux, BSD        - ``${XDG_DATA_HOME:-${HOME}/.local/share}/streamlink/plugins``

                  Deprecated:

                  - ``${XDG_CONFIG_HOME:-${HOME}/.config}/streamlink/plugins``
macOS             - ``${HOME}/Library/Application Support/streamlink/plugins``

                  Deprecated:

                  - ``${XDG_CONFIG_HOME:-${HOME}/.config}/streamlink/plugins``
Windows           - ``%APPDATA%\streamlink\plugins``
================= ====================================================

.. note::

    If a plugin is added with the same name as a built-in plugin, then
    the added plugin will take precedence. This is useful if you want
    to upgrade plugins independently of the Streamlink version.

.. warning::

    If one of the sideloaded plugins fails to load, eg. due to a
    ``SyntaxError`` being raised by the parser, this exception will
    not get caught by Streamlink and the execution will stop, even if
    the input stream URL does not match the faulty plugin.
