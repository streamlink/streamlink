from __future__ import annotations

import base64
import hashlib
import importlib.metadata
import json
import logging
import pkgutil
import re
from collections.abc import Iterator, Mapping
from contextlib import suppress
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Literal, TypedDict

import streamlink.plugins
from streamlink.options import Argument, Arguments

# noinspection PyProtectedMember
from streamlink.plugin.plugin import _PLUGINARGUMENT_TYPE_REGISTRY, NO_PRIORITY, NORMAL_PRIORITY, Matcher, Matchers, Plugin
from streamlink.utils.module import exec_module, get_finder


if TYPE_CHECKING:
    try:
        from typing import TypeAlias  # type: ignore[attr-defined]
    except ImportError:
        from typing_extensions import TypeAlias

    from _typeshed.importlib import PathEntryFinderProtocol


log = logging.getLogger(".".join(__name__.split(".")[:-1]))

# The path to Streamlink's built-in plugins
_PLUGINS_PATH = Path(streamlink.plugins.__path__[0])

# Hardcoded plugins JSON file path
_PLUGINSDATA_PATH = _PLUGINS_PATH / "_plugins.json"
# Hardcoded package name to look up metadata
_PLUGINSDATA_PACKAGENAME = "streamlink"
# The `parts` value of the plugins JSON file contained in the package's `RECORD` metadata file
_PLUGINSDATA_PACKAGEPATH = "streamlink", "plugins", "_plugins.json"


class StreamlinkPlugins:
    """
    Streamlink's session-plugins implementation. This class is responsible for loading plugins and resolving them from URLs.

    See the :attr:`Streamlink.plugins <streamlink.session.Streamlink.plugins>` attribute.

    Unless disabled by the user, Streamlink will try to load built-in plugins lazily, when accessing them for the first time
    while resolving input URLs. This is done by reading and interpreting serialized data of each plugin's
    :func:`pluginmatcher <streamlink.plugin.pluginmatcher>` and :func:`pluginargument <streamlink.plugin.pluginargument>`
    data from a pre-built plugins JSON file which is included in Streamlink's wheel packages.

    Plugins which are sideloaded, either from specific user directories or custom input directories,
    always have a higher priority than built-in plugins.
    """

    def __init__(self, builtin: bool = True, lazy: bool = True):
        # Loaded plugins
        self._plugins: dict[str, type[Plugin]] = {}

        # Data of built-in plugins which can be loaded lazily
        self._matchers: dict[str, Matchers] = {}
        self._arguments: dict[str, Arguments] = {}

        # Attempt to load built-in plugins lazily first
        if builtin and lazy:
            data = StreamlinkPluginsData.load()
            if data:
                self._matchers, self._arguments = data
            else:
                lazy = False

        # Load built-ins if lazy-loading is disabled or if loading plugins data has failed
        if builtin and not lazy:
            self.load_builtin()

    def __getitem__(self, item: str) -> type[Plugin]:
        """Access a loaded plugin class by name"""
        return self._plugins[item]

    def __setitem__(self, key: str, value: type[Plugin]) -> None:
        """Add/override a plugin class by name"""
        self._plugins[key] = value

    def __delitem__(self, key: str) -> None:
        """Remove a loaded plugin by name"""
        self._plugins.pop(key, None)

    def __contains__(self, item: str) -> bool:
        """Check if a plugin is loaded"""
        return item in self._plugins

    def get_names(self) -> list[str]:
        """Get a list of the names of all available plugins"""
        return sorted(self._plugins.keys() | self._matchers.keys())

    def get_loaded(self) -> dict[str, type[Plugin]]:
        """Get a mapping of all loaded plugins"""
        return dict(self._plugins)

    def load_builtin(self) -> bool:
        """Load Streamlink's built-in plugins"""
        return self.load_path(_PLUGINS_PATH)

    def load_path(self, path: str | Path) -> bool:
        """Load plugins from a custom directory"""
        plugins = self._load_plugins_from_path(path)
        self.update(plugins)

        return bool(plugins)

    def update(self, plugins: Mapping[str, type[Plugin]]):
        """Add/override loaded plugins"""
        self._plugins.update(plugins)

    def clear(self):
        """Remove all loaded plugins from the session"""
        self._plugins.clear()

    def iter_arguments(self) -> Iterator[tuple[str, Arguments]]:
        """Iterate through all plugins and their :class:`Arguments <streamlink.options.Arguments>`"""
        yield from (
            (name, plugin.arguments)
            for name, plugin in self._plugins.items()
            if plugin.arguments
        )  # fmt: skip
        yield from (
            (name, arguments)
            for name, arguments in self._arguments.items()
            if arguments and name not in self._plugins
        )  # fmt: skip

    def iter_matchers(self) -> Iterator[tuple[str, Matchers]]:
        """Iterate through all plugins and their :class:`Matchers <streamlink.plugin.plugin.Matchers>`"""
        yield from (
            (name, plugin.matchers)
            for name, plugin in self._plugins.items()
            if plugin.matchers
        )  # fmt: skip
        yield from (
            (name, matchers)
            for name, matchers in self._matchers.items()
            if matchers and name not in self._plugins
        )  # fmt: skip

    def match_url(self, url: str) -> tuple[str, type[Plugin]] | None:
        """Find a matching plugin by URL and load plugins which haven't been loaded yet"""
        match: str | None = None
        priority: int = NO_PRIORITY

        for name, matchers in self.iter_matchers():
            for matcher in matchers:
                if matcher.priority > priority and matcher.pattern.match(url) is not None:
                    match = name
                    priority = matcher.priority

        if match is None:
            return None

        # plugin not loaded yet?
        # if a custom plugin with the same name has already been loaded, skip loading the built-in plugin
        if match not in self._plugins:
            log.debug(f"Loading plugin: {match}")
            lookup = self._load_plugin_from_path(match, _PLUGINS_PATH)
            if not lookup:
                return None
            self._plugins[match] = lookup[1]

        return match, self._plugins[match]

    def _load_plugin_from_path(self, name: str, path: Path) -> tuple[ModuleType, type[Plugin]] | None:
        finder = get_finder(path)

        return self._load_plugin_from_finder(name, finder)

    def _load_plugins_from_path(self, path: str | Path) -> dict[str, type[Plugin]]:
        plugins: dict[str, type[Plugin]] = {}
        for finder, name, _ in pkgutil.iter_modules([str(path)]):
            lookup = self._load_plugin_from_finder(name, finder=finder)  # type: ignore[arg-type]
            if lookup is None:
                continue
            mod, plugin = lookup
            if (name in self._plugins or name in self._matchers) and mod.__file__:
                with open(mod.__file__, "rb") as fh:
                    sha256 = hashlib.sha256(fh.read())
                log.info(f"Plugin {name} is being overridden by {mod.__file__} (sha256:{sha256.hexdigest()})")
            plugins[name] = plugin

        return plugins

    @staticmethod
    def _load_plugin_from_finder(name: str, finder: PathEntryFinderProtocol) -> tuple[ModuleType, type[Plugin]] | None:
        try:
            # set the full plugin module name, even for sideloaded plugins
            mod = exec_module(finder, f"streamlink.plugins.{name}", override=True)
        except ImportError as err:
            log.exception(f"Failed to load plugin {name} from {err.path}\n")
            return None

        if not hasattr(mod, "__plugin__") or not issubclass(mod.__plugin__, Plugin):
            return None

        return mod, mod.__plugin__


_RE_STRIP_JSON_COMMENTS = re.compile(rb"^(?:\s*//[^\n]*\n+)+")

_TListOfConstants: TypeAlias = "list[bool | int | float | str | None]"
_TConstantOrListOfConstants: TypeAlias = "bool | int | float | str | _TListOfConstants | None"
_TMappingOfConstantOrListOfConstants: TypeAlias = "dict[str, _TConstantOrListOfConstants]"


class _TPluginMatcherData(TypedDict):
    pattern: str
    flags: int | None
    priority: int | None
    name: str | None


class _TPluginArgumentData(TypedDict):
    name: str
    action: str | None
    nargs: int | Literal["*", "?", "+"] | None
    const: _TConstantOrListOfConstants
    default: _TConstantOrListOfConstants
    type: str | None
    type_args: _TListOfConstants | None
    type_kwargs: _TMappingOfConstantOrListOfConstants | None
    choices: _TListOfConstants | None
    required: bool | None
    help: str | None
    metavar: str | list[str] | None
    dest: str | None
    requires: str | list[str] | None
    prompt: str | None
    sensitive: bool | None
    argument_name: str | None


class _TPluginData(TypedDict):
    matchers: list[_TPluginMatcherData]
    arguments: list[_TPluginArgumentData]


class StreamlinkPluginsData:
    @classmethod
    def load(cls) -> tuple[dict[str, Matchers], dict[str, Arguments]] | None:
        # specific errors get logged, others are ignored intentionally
        with suppress(Exception):
            content = _PLUGINSDATA_PATH.read_bytes()

            cls._validate(content)

            return cls._parse(content)

        return None

    @staticmethod
    def _validate(content: bytes) -> None:
        # find plugins JSON checksum in package metadata
        # https://packaging.python.org/en/latest/specifications/recording-installed-packages/#the-record-file
        mode, filehash = next(
            (packagepath.hash.mode, packagepath.hash.value)
            for packagepath in importlib.metadata.files(_PLUGINSDATA_PACKAGENAME) or []
            if packagepath.hash is not None and packagepath.parts == _PLUGINSDATA_PACKAGEPATH
        )
        if mode not in hashlib.algorithms_guaranteed or not filehash:
            log.error("Unknown plugins data hash mode, falling back to loading all plugins")
            raise Exception

        # compare checksums
        hashalg = getattr(hashlib, mode)
        hashobj = hashalg(content)
        digest = base64.urlsafe_b64encode(hashobj.digest()).decode("utf-8").rstrip("=")
        if digest != filehash:
            log.error("Plugins data checksum mismatch, falling back to loading all plugins")
            raise Exception

    @classmethod
    def _parse(cls, content: bytes) -> tuple[dict[str, Matchers], dict[str, Arguments]]:
        content = _RE_STRIP_JSON_COMMENTS.sub(b"", content)
        data: dict[str, _TPluginData] = json.loads(content)

        try:
            matchers = cls._build_matchers(data)
        except Exception:
            log.exception("Error while loading pluginmatcher data from JSON")
            raise

        try:
            arguments = cls._build_arguments(data)
        except Exception:
            log.exception("Error while loading pluginargument data from JSON")
            raise

        return matchers, arguments

    @classmethod
    def _build_matchers(cls, data: dict[str, _TPluginData]) -> dict[str, Matchers]:
        res = {}
        for pluginname, plugindata in data.items():
            matchers = Matchers()
            for m in plugindata.get("matchers") or []:
                matcher = cls._build_matcher(m)
                matchers.add(matcher)

            res[pluginname] = matchers

        return res

    @staticmethod
    def _build_matcher(data: _TPluginMatcherData) -> Matcher:
        return Matcher(
            pattern=re.compile(data.get("pattern"), data.get("flags") or 0),
            priority=data.get("priority") or NORMAL_PRIORITY,
            name=data.get("name"),
        )

    @classmethod
    def _build_arguments(cls, data: dict[str, _TPluginData]) -> dict[str, Arguments]:
        res = {}
        for pluginname, plugindata in data.items():
            if not plugindata.get("arguments"):
                continue
            arguments = Arguments()
            for a in reversed(plugindata.get("arguments") or []):
                if argument := cls._build_argument(a):
                    arguments.add(argument)

            res[pluginname] = arguments

        return res

    @staticmethod
    def _build_argument(data: _TPluginArgumentData) -> Argument | None:
        name: str = data.get("name")  # type: ignore[assignment]
        type_data = data.get("type")
        if not type_data:
            argument_type = None
        elif argument_type := _PLUGINARGUMENT_TYPE_REGISTRY.get(type_data):
            type_args = data.get("type_args") or ()
            type_kwargs = data.get("type_kwargs") or {}
            if type_args or type_kwargs:
                argument_type = argument_type(*type_args, **type_kwargs)
        else:
            return None

        return Argument(
            name=name,
            action=data.get("action"),
            nargs=data.get("nargs"),
            const=data.get("const"),
            default=data.get("default"),
            type=argument_type,
            choices=data.get("choices"),
            required=data.get("required") or False,
            help=data.get("help"),
            metavar=data.get("metavar"),
            dest=data.get("dest"),
            requires=data.get("requires"),
            prompt=data.get("prompt"),
            sensitive=data.get("sensitive") or False,
            argument_name=data.get("argument_name"),
        )
