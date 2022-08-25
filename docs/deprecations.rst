Deprecations
============

streamlink 5.0.0
----------------

Deprecation of Plugin.__init__(self, url)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

With the removal of the ``Plugin.bind()`` class method which was used for setting up the
:py:class:`Streamlink <streamlink.session.Streamlink>` session instance and module name in each plugin class,
the :py:class:`Plugin <streamlink.plugin.Plugin>` constructor's signature was changed and it now requires
the ``session`` and ``url`` arguments. Implementors of custom plugins should define variable positional arguments and keyword
arguments when subclassing and adding a custom constructor (``*args, **kwargs``), and the ``url`` should be accessed via
``self.url`` after calling the constructor of the super class.

Compatibility wrappers were added for old custom plugin implementations, and a deprecation message will be shown until
the compatibility wrappers will get removed in a future release.


Session.resolve_url() return type changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Due to the changes of the :py:class:`Plugin <streamlink.plugin.Plugin>` class mentioned above, the return value of
:py:meth:`Streamlink.resolve_url <streamlink.Streamlink.resolve_url>` and
:py:meth:`Streamlink.resolve_url_no_redirect <streamlink.Streamlink.resolve_url_no_redirect>` had to be changed
from ``tuple[type[Plugin], str]`` to ``tuple[str, type[Plugin], str]``, and both methods now return the resolved plugin name
as the first item, in addition to the plugin class and resolved URL.


streamlink 4.2.0
----------------

Deprecation of url_master in HLSStream
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``url_master`` parameter and attribute of the :py:class:`streamlink.stream.HLSStream`
and :py:class:`streamlink.stream.MuxedHLSStream` classes have been deprecated in favor of the ``multivariant`` parameter
and attribute. ``multivariant`` is an :py:class:`M3U8` reference of the parsed HLS multivariant playlist.


streamlink 4.0.0
----------------

Removal of streamlink.plugin.api.utils
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``streamlink.plugin.api.utils`` module including the ``itertags`` function and export aliases for ``streamlink.utils.parse``
has been removed. Import the parse functions directly and find data in XML/HTML by parsing it via ``parse_{xml,html}`` and
applying XPath queries to the parsed result via the available methods provided by the ``lxml.etree`` API. The
``streamlink.plugin.api.validate`` module also has the necessary validation schema functions for this.


streamlink 3.0.0
----------------

Removal of separate https-proxy option
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:ref:`HTTPS proxy CLI option <cli:HTTP options>` and the respective :ref:`Session options <api:Session>`
have been deprecated in favor of a single :option:`--http-proxy` that sets the proxy for all HTTP and
HTTPS requests, including WebSocket connections.


streamlink 2.4.0
----------------

Stream-type related CLI arguments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:ref:`Stream-type related CLI arguments <cli:Stream transport options>` and the respective :ref:`Session options <api:Session>`
have been deprecated in favor of existing generic arguments/options, to avoid redundancy and potential confusion.

- use :option:`--stream-segment-attempts` instead of ``--{dash,hds,hls}-segment-attempts``
- use :option:`--stream-segment-threads` instead of ``--{dash,hds,hls}-segment-threads``
- use :option:`--stream-segment-timeout` instead of ``--{dash,hds,hls}-segment-timeout``
- use :option:`--stream-timeout` instead of ``--{dash,hds,hls,rtmp,http-stream}-timeout``


streamlink 2.3.0
----------------

Plugin.can_handle_url() and Plugin.priority()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A new plugin URL matching API was introduced in 2.3.0 which will help Streamlink with static code analysis and an improved
plugin loading mechanism in the future. Plugins now define their matching URLs and priorities declaratively.

The old ``can_handle_url`` and ``priority`` classmethods have therefore been deprecated and will be removed in the future.
When side-loading plugins which don't implement the new ``@pluginmatcher`` but implement the old classmethods, a deprecation
message will be written to the info log output for the first plugin that gets resolved this way.

**Deprecated plugin URL matching**

.. code-block:: python

   import re
   from streamlink.plugin import Plugin
   from streamlink.plugin.plugin import HIGH_PRIORITY, NORMAL_PRIORITY

   class MyPlugin(Plugin):
       _re_url_one = re.compile(
           r"https?://pattern-(?P<param>one)"
       )
       _re_url_two = re.compile(r"""
           https?://pattern-(?P<param>two)
       """, re.VERBOSE)

       @classmethod
       def can_handle_url(cls, url: str) -> bool:
           return cls._re_url_one.match(url) is not None \
                  or cls._re_url_two.match(url) is not None

       @classmethod
       def priority(cls, url: str) -> int:
           if cls._re_url_two.match(url) is not None:
               return HIGH_PRIORITY
           else:
               return NORMAL_PRIORITY

       def _get_streams(self):
           match_one = self._re_url_one.match(self.url)
           match_two = self._re_url_two.match(self.url)
           match = match_one or match_two
           param = match.group("param")
           if match_one:
               yield ...
           elif match_two:
               yield ...

   __plugin__ = MyPlugin

**Migration**

.. code-block:: python

   import re
   from streamlink.plugin import HIGH_PRIORITY, Plugin, pluginmatcher

   @pluginmatcher(re.compile(
       r"https?://pattern-(?P<param>one)"
   ))
   @pluginmatcher(priority=HIGH_PRIORITY, pattern=re.compile(r"""
       https?://pattern-(?P<param>two)
   """, re.VERBOSE))
   class MyPlugin(Plugin):
      def _get_streams(self):
          param = self.match.group("param")
          if self.matches[0]:
              yield ...
          elif self.matches[1]:
              yield ...

   __plugin__ = MyPlugin

.. note::

   Plugins which have more sophisticated logic in their ``can_handle_url()`` classmethod need to be rewritten with
   multiple ``@pluginmatcher`` decorators and/or an improved ``_get_streams()`` method which returns ``None`` or raises a
   ``NoStreamsError`` when there are no streams to be found on that particular URL.


streamlink 2.2.0
----------------

Config file paths
^^^^^^^^^^^^^^^^^

Streamlink's default config file paths got updated and corrected on Linux/BSD, macOS and Windows.
Old and deprecated paths will be dropped in the future.

Only the first existing config file will be loaded. If a config file gets loaded from a deprecated path,
a deprecation message will be written to the info log output.

To resolve this, move the config file(s) to the correct location or copy the contents of the old file(s) to the new one(s).

.. note::

   Please note that this also affects all plugin config files, as they use the same path as the primary config file but with
   ``.pluginname`` appended to the file name, eg. ``config.twitch``.

.. warning::

   **On Windows**, when installing Streamlink via the Windows installer, a default config file gets created automatically due
   to technical reasons (bundled ffmpeg and rtmpdump dependencies). This means that the Windows installer will create a
   config file with the new name when upgrading from an earlier version to Streamlink 2.2.0+, and the old config file won't be
   loaded as a result of this.

   This is unfortunately a soft breaking change, as the Windows installer is not supposed to touch user config data and the
   users are required to update this by themselves.

**Deprecated paths**

.. rst-class:: table-custom-layout table-custom-layout-platform-locations

========= ========
Platform  Location
========= ========
Linux/BSD - ``${HOME}/.streamlinkrc``
macOS     - ``${XDG_CONFIG_HOME:-${HOME}/.config}/streamlink/config``
          - ``${HOME}/.streamlinkrc``
Windows   - ``%APPDATA%\streamlink\streamlinkrc``
========= ========

**Migration**

.. rst-class:: table-custom-layout table-custom-layout-platform-locations

========= ========
Platform  Location
========= ========
Linux/BSD ``${XDG_CONFIG_HOME:-${HOME}/.config}/streamlink/config``
macOS     ``${HOME}/Library/Application Support/streamlink/config``
Windows   ``%APPDATA%\streamlink\config``
========= ========


Custom plugins sideloading paths
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Streamlink's default custom plugins directory path got updated and corrected on Linux/BSD and macOS.
Old and deprecated paths will be dropped in the future.

**Deprecated paths**

.. rst-class:: table-custom-layout table-custom-layout-platform-locations

========= ========
Platform  Location
========= ========
Linux/BSD ``${XDG_CONFIG_HOME:-${HOME}/.config}/streamlink/plugins``
macOS     ``${XDG_CONFIG_HOME:-${HOME}/.config}/streamlink/plugins``
========= ========

**Migration**

.. rst-class:: table-custom-layout table-custom-layout-platform-locations

========= ========
Platform  Location
========= ========
Linux/BSD ``${XDG_DATA_HOME:-${HOME}/.local/share}/streamlink/plugins``
macOS     ``${HOME}/Library/Application Support/streamlink/plugins``
========= ========
