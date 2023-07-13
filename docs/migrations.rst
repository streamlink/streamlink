Migrations
==========

streamlink 6.0.0
----------------

Player-path-only --player CLI argument
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Despite having the dedicated CLI argument for setting custom player arguments :option:`--player-args`,
Streamlink used to support setting custom player arguments using the :option:`--player` CLI argument.

This meant that the :option:`--player` value had to be treated as a command line string rather than a player path.
As a result of this, player paths would need to be quoted if they contained whitespace characters. While the default config
file of Streamlink's Windows installer tried to teach this, it was often used incorrectly on command-line shells, especially
on Windows where escaping the CLI argument is more difficult compared to POSIX compliant command-line shells. Not quoting
the player path on Windows still worked, but at the cost of potentially resolving an incorrect or malicious executable.

The support for custom player arguments in :option:`--player` was a relic from the Livestreamer project and has finally
been removed. :option:`--player` now only accepts player executable path strings and any custom player arguments need to be set
using the :option:`--player-args` CLI argument where the argument value gets properly interpreted using shell-like syntax.

Streamlink's Windows installer has received a new default config file and users now also can choose to overwrite their existing
config file from previous installs. The default behavior remains the same with existing config files staying untouched.

| :octicon:`x-circle` #5305
| :octicon:`git-pull-request` #5310

.. admonition:: Migration
   :class: hint

   1. Move any custom player arguments from the value of :option:`--player` to :option:`--player-args`
   2. In config files, remove any quotation from the value of :option:`--player`
      (command-line shells will of course require quotation when the player path contains whitespace characters)

{filename} variable in --player-args
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :option:`--player-args`'s ``{filename}`` variable has been removed. This was kept as a fallback when
the ``{playerinput}`` variable as added to prevent confusion around the player's input argument
for various different stream transport methods, like stdin, named pipes, passthrough, etc.

| :octicon:`x-circle` #3313
| :octicon:`git-pull-request` #5310

.. admonition:: Migration
   :class: hint

   1. Rename ``{filename}`` to ``{playerinput}``

Plugin.can_handle_url() and Plugin.priority()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Streamlink 2.3.0 :ref:`deprecated <deprecations:Plugin.can_handle_url() and Plugin.priority()>`
the ``can_handle_url()`` and ``priority()`` classmethods of :py:class:`Plugin <streamlink.plugin.Plugin>` in favor of
the plugin matcher API. These deprecated classmethods have now been removed.

| :octicon:`x-circle` #3814
| :octicon:`git-pull-request` #5403

.. admonition:: Migration
   :class: hint

   1. Replace custom matching logic in ``Plugin.can_handle_url()`` with
      :py:meth:`pluginmatcher <streamlink.plugin.pluginmatcher>` decorators
   2. Replace custom plugin priority matching logic in ``Plugin.priority()`` with the ``priority`` argument
      of the :py:meth:`pluginmatcher <streamlink.plugin.pluginmatcher>` decorators

Plugin.__init__(self, url) compatibility wrapper
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Streamlink 5.0.0 :ref:`deprecated <deprecations:Plugin.__init__(self, url) compatibility wrapper>` the usage of the old
:py:class:`Plugin <streamlink.plugin.Plugin>` constructor without the :py:class:`Streamlink <streamlink.session.Streamlink>`
``session`` argument. ``session`` was added because the old ``Plugin.bind()`` classmethod got removed, which previously
bound the session instance to the entire ``Plugin`` class, rather than individual ``Plugin`` instances, causing Python's
garbage collector to not be able to let go of any loaded built-in plugins when initializing more than one session.

| :octicon:`x-circle` #4768
| :octicon:`git-pull-request` #5402

.. admonition:: Migration
   :class: hint

   1. Replace the arguments of custom constructors of each :py:class:`Plugin <streamlink.plugin.Plugin>` subclass with
      ``*args, **kwargs`` and call ``super().__init__(*args, **kwargs)``
   2. If needed, access the ``url`` using ``self.url``

Global plugin arguments
^^^^^^^^^^^^^^^^^^^^^^^

Streamlink 5.3.0 :ref:`deprecated <deprecations:Global plugin arguments>` the ``is_global=True`` argument
of the :py:meth:`pluginargument <streamlink.plugin.pluginargument>` decorator (as well as the
:py:class:`Argument <streamlink.options.Argument>` class), as global plugin arguments were deemed unnecessary.
The ``is_global`` argument has thus been removed now.

| :octicon:`x-circle` #5140
| :octicon:`git-pull-request` #5033

.. admonition:: Migration
   :class: hint

   1. Get the value of the global argument using :py:meth:`Streamlink.get_option() <streamlink.session.Streamlink.get_option>`
      instead of getting it from :py:attr:`Plugin.options <streamlink.plugin.Plugin.options>`

plugin.api.validate.text
^^^^^^^^^^^^^^^^^^^^^^^^

Streamlink 5.2.0 :ref:`deprecated <deprecations:plugin.api.validate.text>` the ``plugin.api.validate.text`` alias for ``str``.
This was a remnant of the Python 2 era and has been removed.

| :octicon:`x-circle` #5090
| :octicon:`git-pull-request` #5404

.. admonition:: Migration
   :class: hint

   1. Replace ``plugin.api.validate.text`` with ``str``

HTTPStream and HLSStream signature changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The signatures of the constructors of :py:class:`HTTPStream <streamlink.stream.HTTPStream>`
and :py:class:`HLSStream <streamlink.stream.HLSStream>`, as well as
the :py:meth:`HLSStream.parse_variant_playlist() <streamlink.stream.HLSStream.parse_variant_playlist>` classmethod
were changed and fixed.

| :octicon:`git-pull-request` #5429

.. admonition:: Migration
   :class: hint

   1. Set the :py:class:`Streamlink <streamlink.session.Streamlink>` session instance as a positional argument,
      or replace the ``session_`` keyword with ``session``


streamlink 5.0.0
----------------

Session.resolve_url() return type changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

With the removal of the ``Plugin.bind()`` classmethod, the return value of
:py:meth:`Streamlink.resolve_url() <streamlink.session.Streamlink.resolve_url>`
and :py:meth:`Streamlink.resolve_url_no_redirect() <streamlink.session.Streamlink.resolve_url_no_redirect>`
were changed. Both methods now return a three-element tuple of the resolved plugin name, plugin class and URL.

| :octicon:`git-pull-request` #4768

.. admonition:: Migration
   :class: hint

   1. Return type changed from ``tuple[type[Plugin], str]`` to ``tuple[str, type[Plugin], str]``


streamlink 4.0.0
----------------

streamlink.plugin.api.utils
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``streamlink.plugin.api.utils`` module has been removed, including the ``itertags`` function and the export aliases
for ``streamlink.utils.parse``.

| :octicon:`x-circle` #4455
| :octicon:`git-pull-request` #4467

.. admonition:: Migration
   :class: hint

   1. Write validation schemas using the ``parse_{html,json,xml}()`` validators.
      Parsed HTML/XML documents enable data extraction with XPath queries.
   2. Alternatively, import the ``parse_{html,json,qsd,xml}()`` utility functions from the ``streamlink.utils.parse`` module


streamlink 3.0.0
----------------

Plugin class returned by Session.resolve_url()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to enable :py:class:`Plugin <streamlink.plugin.Plugin>` constructors to have access to plugin options derived from
the resolved plugin arguments, ``Plugin`` instantiation moved from
:py:meth:`Streamlink.resolve_url() <streamlink.session.Streamlink.resolve_url>` to ``streamlink_cli``,
and the return value of :py:meth:`Streamlink.resolve_url() <streamlink.session.Streamlink.resolve_url>`
and :py:meth:`Streamlink.resolve_url_no_redirect() <streamlink.session.Streamlink.resolve_url_no_redirect>` were changed.

| :octicon:`git-pull-request` #4163

.. admonition:: Migration
   :class: hint

   1. Return type changed from ``Plugin`` to ``tuple[type[Plugin], str]``
