Plugin sideloading
==================

Streamlink supports overriding its :ref:`built-in plugins <plugins:Plugins>` or loading custom third party plugins
without having to modify its sources or its built and installed `Python distribution`_. This is called plugin sideloading.

Those additional plugin modules will automatically be loaded `from the paths listed below <Sideloading locations_>`_,
or from the path(s) of the :option:`--plugin-dir` CLI argument, if it is set.

.. attention::

    **Do not** attempt to modify :ref:`built-in plugins <plugins:Plugins>` or to add custom plugins to Streamlink's
    built `Python distribution`_. In order to keep loading times low, Streamlink implements a lazy plugin-loading system
    for its built-in plugins, which means that :func:`pluginmatcher <streamlink.plugin.pluginmatcher>`
    and :func:`pluginargument <streamlink.plugin.pluginargument>` data is pre-computed and cached,
    thus making modifications to plugin modules or adding new plugin modules pointless. Instead, sideload plugins.

.. warning::

    If one of the sideloaded plugins fails to load and execute, e.g. due to a ``SyntaxError`` being raised by the parser,
    then this exception won't be caught by Streamlink and the execution will stop, even if the input stream URL
    does not match the faulty plugin.

.. note::

    Custom plugin modules will always be loaded and executed at once, increasing the load and initialization time
    of the :class:`Streamlink session <streamlink.session.Streamlink>`. :ref:`Built-in plugins <plugins:Plugins>`
    on the other hand are loaded lazily, unless overridden.

.. _Python distribution: https://packaging.python.org/en/latest/glossary/#term-Built-Distribution

Overriding
----------

If a plugin is added with the same name as a built-in plugin, then the added plugin will take precedence.
This can be useful for upgrading or modifying plugins independently of the Streamlink version.

In this case, a log message will be written to log level :option:`debug <--loglevel>`:

.. code-block:: text

    [session][debug] Plugin PLUGINNAME is being overridden by PATH-TO-PLUGIN-FILE (sha256:CHECKSUM)

Sideloading locations
---------------------

.. rst-class:: table-custom-layout table-custom-layout-platform-locations

.. list-table::
    :header-rows: 1
    :width: 100%

    * - Platform
      - Location
    * - Linux, BSD
      - | **Path**
        | ``${XDG_DATA_HOME:-${HOME}/.local/share}/streamlink/plugins``
        | **Example**
        | ``/home/USERNAME/.local/share/streamlink/plugins``
    * - macOS
      - | **Path**
        | ``${HOME}/Library/Application Support/streamlink/plugins``
        | **Example**
        | ``/Users/USERNAME/Library/Application Support/streamlink/plugins``
    * - Windows
      - | **Path**
        | ``%APPDATA%\streamlink\plugins``
        | **Example**
        | ``C:\Users\USERNAME\AppData\Roaming\streamlink\plugins``
