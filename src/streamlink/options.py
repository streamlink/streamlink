from typing import Iterator, Optional, Sequence, Union


def _normalise_option_name(name):
    return name.replace('-', '_')


def _normalise_argument_name(name):
    return name.replace('_', '-').strip("-")


class Options:
    """
    For storing options to be used by plugins, with default values.

    Note: Option names are normalised by replacing "-" with "_". This means that the keys
    ``example-one`` and ``example_one`` are equivalent.
    """

    def __init__(self, defaults=None):
        if not defaults:
            defaults = {}

        self.defaults = self._normalise_dict(defaults)
        self.options = self.defaults.copy()

    @classmethod
    def _normalise_dict(cls, src):
        return {_normalise_option_name(key): value for key, value in src.items()}

    def clear(self):
        self.options = self.defaults.copy()

    def set(self, key, value):
        self.options[_normalise_option_name(key)] = value

    def get(self, key):
        key = _normalise_option_name(key)
        if key in self.options:
            return self.options[key]

    def update(self, options):
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
        self._argument_name = argument_name  # override the cli argument name
        self._dest = dest  # override for the plugin option name
        requires = requires or []
        self.requires = list(requires) if isinstance(requires, (list, tuple)) else [requires]
        self.prompt = prompt
        self.sensitive = sensitive
        self._default = options.get("default")
        self.is_global = is_global

    def _name(self, plugin):
        return self._argument_name or _normalise_argument_name("{0}-{1}".format(plugin, self.name))

    def argument_name(self, plugin):
        return f"--{self.name if self.is_global else self._name(plugin)}"

    def namespace_dest(self, plugin):
        return _normalise_option_name(self._name(plugin))

    @property
    def dest(self):
        return self._dest or _normalise_option_name(self.name)

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
