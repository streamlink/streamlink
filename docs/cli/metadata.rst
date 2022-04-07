Metadata
========

Variables
---------

Streamlink supports a number of metadata variables that can be used in the following CLI arguments:

- :option:`--title`
- :option:`--output`
- :option:`--record`
- :option:`--record-and-pipe`

Metadata variables are surrounded by curly braces and can be escaped by doubling the curly brace characters,
eg. ``{variable}`` and ``{{not-a-variable}}``.

The availability of each variable depends on the used plugin and whether that plugin supports this kind of metadata.
If a variable is unsupported or not available, then its substitution will either be a short placeholder text (:option:`--title`)
or an empty string (:option:`--output`, :option:`--record`, :option:`--record-and-pipe`).

The :option:`--json` argument always lists the standard plugin metadata: ``id``, ``author``, ``category`` and ``title``.

.. rst-class:: table-custom-layout table-custom-layout-platform-locations

============================== =================================================
Variable                       Description
============================== =================================================
``id``                         The unique ID of the stream, eg. an internal numeric ID or randomized string.
``plugin``                     The plugin name. See :ref:`Plugins <plugins:Plugins>` for the name of each built-in plugin.
``title``                      The stream's title, usually a short descriptive text.
``author``                     The stream's author, eg. a channel or broadcaster name.
``category``                   The stream's category, eg. the name of a game being played, a music genre, etc.
``game``                       Alias for ``category``.
``url``                        The resolved URL of the stream.
``time``                       The current timestamp. Can optionally be formatted via ``{time:format}``.

                               The format parameter string is passed to Python's `datetime.strftime()`_ method,
                               so all the usual time directives are available.

                               The default format is ``%Y-%m-%d_%H-%M-%S``.
============================== =================================================


Examples
--------

.. code-block:: console

    $ streamlink --title "{author} - {category} - {title}" <URL> [STREAM]
    $ streamlink --output "~/recordings/{author}/{category}/{id}-{time:%Y%m%d%H%M%S}.ts" <URL> [STREAM]

.. _datetime.strftime(): https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes
