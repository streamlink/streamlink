Deprecations
============

streamlink 2.27.0.0
-------------------

Removal of separate https-proxy option
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:ref:`HTTPS proxy CLI option <cli:HTTP options>` and the respective :ref:`Session options <api:Session>`
have been deprecated in favor of a single :option:`--http-proxy` that sets the proxy for all HTTP and
HTTPS requests, including WebSocket connections.

Stream-type related CLI arguments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:ref:`Stream-type related CLI arguments <cli:Stream transport options>` and the respective :ref:`Session options <api:Session>`
have been deprecated in favor of existing generic arguments/options, to avoid redundancy and potential confusion.

- use :option:`--stream-segment-attempts` instead of ``--{dash,hds,hls}-segment-attempts``
- use :option:`--stream-segment-threads` instead of ``--{dash,hds,hls}-segment-threads``
- use :option:`--stream-segment-timeout` instead of ``--{dash,hds,hls}-segment-timeout``
- use :option:`--stream-timeout` instead of ``--{dash,hds,hls,rtmp,http-stream}-timeout``


streamlink 1.27.6.0
-------------------

Plugin.can_handle_url() and Plugin.priority()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A new plugin URL matching API was introduced in 1.27.6.0 which will help Streamlink with static code analysis and an improved
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
