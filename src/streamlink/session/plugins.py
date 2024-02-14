import base64
import hashlib
import importlib.metadata
import json
import logging
import pkgutil
import re
from contextlib import suppress
from importlib.abc import PathEntryFinder
from pathlib import Path
from types import ModuleType
from typing import Dict, Iterator, List, Literal, Optional, Tuple, Type, Union

import streamlink.plugins
from streamlink.options import Argument, Arguments

# noinspection PyProtectedMember
from streamlink.plugin.plugin import _PLUGINARGUMENT_TYPE_REGISTRY, NO_PRIORITY, NORMAL_PRIORITY, Matcher, Matchers, Plugin
from streamlink.utils.module import exec_module, get_finder


try:
    from typing import TypeAlias, TypedDict  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    from typing_extensions import TypeAlias, TypedDict


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
        self._plugins: Dict[str, Type[Plugin]] = {}

        # Data of built-in plugins which can be loaded lazily
        self._matchers: Dict[str, Matchers] = {}
        self._arguments: Dict[str, Arguments] = {}

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

    def __getitem__(self, item: str) -> Type[Plugin]:
        """Access a loaded plugin class by name"""
        return self._plugins[item]

    def __setitem__(self, key: str, value: Type[Plugin]) -> None:
        """Add/override a plugin class by name"""
        self._plugins[key] = value

    def __delitem__(self, key: str) -> None:
        """Remove a loaded plugin by name"""
        self._plugins.pop(key, None)

    def __contains__(self, item: str) -> bool:
        """Check if a plugin is loaded"""
        return item in self._plugins

    def get_names(self) -> List[str]:
        """Get a list of the names of all available plugins"""
        return sorted(self._plugins.keys() | self._matchers.keys())

    def get_loaded(self) -> Dict[str, Type[Plugin]]:
        """Get a mapping of all loaded plugins"""
        return dict(self._plugins)

    def load_builtin(self) -> bool:
        """Load Streamlink's built-in plugins"""
        return self.load_path(_PLUGINS_PATH)

    def load_path(self, path: Union[Path, str]) -> bool:
        """Load plugins from a custom directory"""
        plugins = self._load_plugins_from_path(path)
        self.update(plugins)

        return bool(plugins)

    def update(self, plugins: Dict[str, Type[Plugin]]):
        """Add/override loaded plugins"""
        self._plugins.update(plugins)

    def clear(self):
        """Remove all loaded plugins from the session"""
        self._plugins.clear()

    def iter_arguments(self) -> Iterator[Tuple[str, Arguments]]:
        """Iterate through all plugins and their :class:`Arguments <streamlink.options.Arguments>`"""
        yield from (
            (name, plugin.arguments)
            for name, plugin in self._plugins.items()
            if plugin.arguments
        )
        yield from (
            (name, arguments)
            for name, arguments in self._arguments.items()
            if arguments and name not in self._plugins
        )

    def iter_matchers(self) -> Iterator[Tuple[str, Matchers]]:
        """Iterate through all plugins and their :class:`Matchers <streamlink.plugin.plugin.Matchers>`"""
        yield from (
            (name, plugin.matchers)
            for name, plugin in self._plugins.items()
            if plugin.matchers
        )
        yield from (
            (name, matchers)
            for name, matchers in self._matchers.items()
            if matchers and name not in self._plugins
        )

    def match_url(self, url: str) -> Optional[Tuple[str, Type[Plugin]]]:
        """Find a matching plugin by URL and load plugins which haven't been loaded yet"""
        match: Optional[str] = None
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

    def _load_plugin_from_path(self, name: str, path: Path) -> Optional[Tuple[ModuleType, Type[Plugin]]]:
        finder = get_finder(path)

        return self._load_plugin_from_finder(name, finder)

    def _load_plugins_from_path(self, path: Union[Path, str]) -> Dict[str, Type[Plugin]]:
        plugins: Dict[str, Type[Plugin]] = {}
        for finder, name, _ in pkgutil.iter_modules([str(path)]):
            lookup = self._load_plugin_from_finder(name, finder=finder)  # type: ignore[arg-type]
            if lookup is None:
                continue
            mod, plugin = lookup
            if name in self._plugins:
                log.info(f"Plugin {name} is being overridden by {mod.__file__}")
            plugins[name] = plugin

        return plugins

    @staticmethod
    def _load_plugin_from_finder(name: str, finder: PathEntryFinder) -> Optional[Tuple[ModuleType, Type[Plugin]]]:
        try:
            # set the full plugin module name, even for sideloaded plugins
            mod = exec_module(finder, f"streamlink.plugins.{name}")
        except ImportError as err:
            log.exception(f"Failed to load plugin {name} from {err.path}\n")
            return None

        if not hasattr(mod, "__plugin__") or not issubclass(mod.__plugin__, Plugin):
            return None

        return mod, mod.__plugin__


_TListOfConstants: TypeAlias = List[Union[None, bool, int, float, str]]
_TConstantOrListOfConstants: TypeAlias = Union[None, bool, int, float, str, _TListOfConstants]
_TMappingOfConstantOrListOfConstants: TypeAlias = Dict[str, _TConstantOrListOfConstants]


class _TPluginMatcherData(TypedDict):
    pattern: str
    flags: Optional[int]
    priority: Optional[int]
    name: Optional[str]


class _TPluginArgumentData(TypedDict):
    name: str
    action: Optional[str]
    nargs: Optional[Union[int, Literal["*", "?", "+"]]]
    const: _TConstantOrListOfConstants
    default: _TConstantOrListOfConstants
    type: Optional[str]
    type_args: Optional[_TListOfConstants]
    type_kwargs: Optional[_TMappingOfConstantOrListOfConstants]
    choices: Optional[_TListOfConstants]
    required: Optional[bool]
    help: Optional[str]
    metavar: Optional[Union[str, List[str]]]
    dest: Optional[str]
    requires: Optional[Union[str, List[str]]]
    prompt: Optional[str]
    sensitive: Optional[bool]
    argument_name: Optional[str]


class _TPluginData(TypedDict):
    matchers: List[_TPluginMatcherData]
    arguments: List[_TPluginArgumentData]


class StreamlinkPluginsData:
    @classmethod
    def load(cls) -> Optional[Tuple[Dict[str, Matchers], Dict[str, Arguments]]]:
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
    def _parse(cls, content: bytes) -> Tuple[Dict[str, Matchers], Dict[str, Arguments]]:
        data: Dict[str, _TPluginData] = json.loads(content)

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
    def _build_matchers(cls, data: Dict[str, _TPluginData]) -> Dict[str, Matchers]:
        res = {}
        for pluginname, plugindata in data.items():
            matchers = Matchers()
            for m in plugindata.get("matchers") or []:
                matcher = cls._build_matcher(m)
                matchers.register(matcher)

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
    def _build_arguments(cls, data: Dict[str, _TPluginData]) -> Dict[str, Arguments]:
        res = {}
        for pluginname, plugindata in data.items():
            if not plugindata.get("arguments"):
                continue
            arguments = Arguments()
            for a in plugindata.get("arguments") or []:
                if argument := cls._build_argument(a):
                    arguments.add(argument)

            res[pluginname] = arguments

        return res

    @staticmethod
    def _build_argument(data: _TPluginArgumentData) -> Optional[Argument]:
        name: str = data.get("name")  # type: ignore[assignment]
        _typedata = data.get("type")
        if not _typedata:
            _type = None
        elif _type := _PLUGINARGUMENT_TYPE_REGISTRY.get(_typedata):
            _type_args = data.get("type_args") or ()
            _type_kwargs = data.get("type_kwargs") or {}
            if _type_args or _type_kwargs:
                _type = _type(*_type_args, **_type_kwargs)
        else:
            return None

        return Argument(
            name=name,
            action=data.get("action"),
            nargs=data.get("nargs"),
            const=data.get("const"),
            default=data.get("default"),
            type=_type,
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
