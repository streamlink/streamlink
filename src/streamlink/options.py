from typing import Any, Callable, ClassVar, Dict, Iterator, Mapping, Optional, Sequence, Union


class Options:
    """
    For storing options to be used by the Streamlink session and plugins, with default values.

    Note: Option names are normalized by replacing "_" with "-".
          This means that the keys ``example_one`` and ``example-one`` are equivalent.
    """

    _MAP_GETTERS: ClassVar[Mapping[str, Callable[[Any, str], Any]]] = {}
    _MAP_SETTERS: ClassVar[Mapping[str, Callable[[Any, str, Any], None]]] = {}

    def __init__(self, defaults: Optional[Mapping[str, Any]] = None):
        if not defaults:
            defaults = {}

        self.defaults = self._normalize_dict(defaults)
        self.options = self.defaults.copy()

    @staticmethod
    def _normalize_key(name: str) -> str:
        return name.replace("_", "-")

    @classmethod
    def _normalize_dict(cls, src: Mapping[str, Any]) -> Dict[str, Any]:
        normalize_key = cls._normalize_key
        return {normalize_key(key): value for key, value in src.items()}

    def clear(self) -> None:
        self.options.clear()
        self.options.update(self.defaults.copy())

    def get(self, key: str) -> Any:
        normalized = self._normalize_key(key)
        method = self._MAP_GETTERS.get(normalized)
        if method is not None:
            return method(self, normalized)
        else:
            return self.options.get(normalized)

    def get_explicit(self, key: str) -> Any:
        normalized = self._normalize_key(key)
        return self.options.get(normalized)

    def set(self, key: str, value: Any) -> None:
        normalized = self._normalize_key(key)
        method = self._MAP_SETTERS.get(normalized)
        if method is not None:
            method(self, normalized, value)
        else:
            self.options[normalized] = value

    def set_explicit(self, key: str, value: Any) -> None:
        normalized = self._normalize_key(key)
        self.options[normalized] = value

    def update(self, options: Mapping[str, Any]) -> None:
        for key, value in options.items():
            self.set(key, value)


class Argument:
    """
    Accepts most of the parameters accepted by :meth:`ArgumentParser.add_argument`,
    except that ``requires`` is a special case which is only enforced if the plugin is in use.
    In addition, the ``name`` parameter is the name relative to the plugin name, but can be overridden by ``argument_name``.

    Should not be called directly, see the :func:`pluginargument <streamlink.plugin.pluginargument>` decorator.
    """

    def __init__(
        self,
        name: str,
        required: bool = False,
        requires: Optional[Union[str, Sequence[str]]] = None,
        prompt: Optional[str] = None,
        sensitive: bool = False,
        argument_name: Optional[str] = None,
        dest: Optional[str] = None,
        is_global: bool = False,
        **options
    ):
        """
        :param name: Argument name, without leading ``--`` or plugin name prefixes, e.g. ``"username"``, ``"password"``, etc.
        :param required: Whether the argument is required for the plugin
        :param requires: List of arguments which this argument requires, eg ``["password"]``
        :param prompt: If the argument is required and not set, this prompt message will be shown instead
        :param sensitive: Whether the argument is sensitive (passwords, etc.) and should be masked
        :param argument_name: Custom CLI argument name without plugin name prefix
        :param dest: Custom plugin option name
        :param is_global: Whether this plugin argument refers to a global CLI argument
        :param options: Arguments passed to :meth:`ArgumentParser.add_argument`, excluding ``requires`` and ``dest``
        """

        self.required = required
        self.name = name
        self.options = options
        self._argument_name = self._normalize_name(argument_name) if argument_name else None
        self._dest = self._normalize_dest(dest) if dest else None
        requires = requires or []
        self.requires = list(requires) if isinstance(requires, (list, tuple)) else [requires]
        self.prompt = prompt
        self.sensitive = sensitive
        self._default = options.get("default")
        self.is_global = is_global

    @staticmethod
    def _normalize_name(name: str) -> str:
        return name.replace("_", "-").strip("-")

    @staticmethod
    def _normalize_dest(name: str) -> str:
        return name.replace("-", "_")

    def _name(self, plugin):
        return self._argument_name or self._normalize_name(f"{plugin}-{self.name}")

    def argument_name(self, plugin):
        return f"--{self.name if self.is_global else self._name(plugin)}"

    def namespace_dest(self, plugin):
        return self._normalize_dest(self._name(plugin))

    @property
    def dest(self):
        return self._dest or self._normalize_dest(self.name)

    @property
    def default(self):  # read-only
        return self._default


class Arguments:
    """
    A collection of :class:`Argument` instances for :class:`Plugin <streamlink.plugin.Plugin>` classes.

    Should not be called directly, see the :func:`pluginargument <streamlink.plugin.pluginargument>` decorator.
    """

    def __init__(self, *args):
        # keep the initial arguments of the constructor in reverse order (see __iter__())
        self.arguments = {arg.name: arg for arg in reversed(args)}

    def __iter__(self) -> Iterator[Argument]:
        # iterate in reverse order due to add() being called by multiple pluginargument decorators in reverse order
        # TODO: Python 3.7 removal: remove list()
        return reversed(list(self.arguments.values()))

    def add(self, argument: Argument) -> None:
        self.arguments[argument.name] = argument

    def get(self, name: str) -> Optional[Argument]:
        return self.arguments.get(name)

    def requires(self, name: str) -> Iterator[Argument]:
        """
        Find all :class:`Argument` instances required by name
        """

        results = {name}
        argument = self.get(name)
        for reqname in (argument.requires if argument else []):
            required = self.get(reqname)
            if not required:
                raise KeyError(f"{reqname} is not a valid argument for this plugin")

            if required.name in results:
                raise RuntimeError("cycle detected in plugin argument config")
            results.add(required.name)
            yield required

            for r in self.requires(required.name):
                if r.name in results:
                    raise RuntimeError("cycle detected in plugin argument config")
                results.add(r.name)
                yield r


__all__ = ["Options", "Arguments", "Argument"]
