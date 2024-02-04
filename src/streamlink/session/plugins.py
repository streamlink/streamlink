import logging
import pkgutil
from importlib.abc import PathEntryFinder
from pathlib import Path
from types import ModuleType
from typing import Dict, Iterator, List, Optional, Tuple, Type, Union

import streamlink.plugins
from streamlink.options import Arguments

# noinspection PyProtectedMember
from streamlink.plugin.plugin import NO_PRIORITY, Matchers, Plugin
from streamlink.utils.module import exec_module


log = logging.getLogger(".".join(__name__.split(".")[:-1]))

# The path to Streamlink's built-in plugins
_PLUGINS_PATH = Path(streamlink.plugins.__path__[0])


class StreamlinkPlugins:
    """
    Streamlink's session-plugins implementation. This class is responsible for loading plugins and resolving them from URLs.

    See the :attr:`Streamlink.plugins <streamlink.session.Streamlink.plugins>` attribute.
    """

    def __init__(self, builtin: bool = True):
        self._plugins: Dict[str, Type[Plugin]] = {}

        if builtin:
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
        """Get a list of the names of all loaded plugins"""
        return sorted(self._plugins.keys())

    def get_loaded(self) -> Dict[str, Type[Plugin]]:
        """Get a mapping of all loaded plugins"""
        return dict(self._plugins)

    def load_builtin(self) -> bool:
        """Load Streamlink's built-in plugins"""
        return self.load_path(_PLUGINS_PATH)

    def load_path(self, path: Union[Path, str]) -> bool:
        """Load plugins from a custom directory"""
        plugins = self._load_from_path(path)
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

    def iter_matchers(self) -> Iterator[Tuple[str, Matchers]]:
        """Iterate through all plugins and their :class:`Matchers <streamlink.plugin.plugin.Matchers>`"""
        yield from (
            (name, plugin.matchers)
            for name, plugin in self._plugins.items()
            if plugin.matchers
        )

    def match_url(self, url: str) -> Optional[Tuple[str, Type[Plugin]]]:
        """Find a matching plugin by URL"""
        match: Optional[str] = None
        priority: int = NO_PRIORITY

        for name, matchers in self.iter_matchers():
            for matcher in matchers:
                if matcher.priority > priority and matcher.pattern.match(url) is not None:
                    match = name
                    priority = matcher.priority

        if match is None:
            return None

        return match, self._plugins[match]

    def _load_from_path(self, path: Union[Path, str]) -> Dict[str, Type[Plugin]]:
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
