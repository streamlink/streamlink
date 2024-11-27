from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable, Iterator, Mapping
from typing import Any, ClassVar, Dict, Literal, TypeVar


class Options(Dict[str, Any]):
    """
    For storing options to be used by the Streamlink session and plugins, with default values.

    Note: Option names are normalized by replacing "_" with "-".
          This means that the keys ``example_one`` and ``example-one`` are equivalent.
    """

    #: Optional getter mapping for :class:`Options` subclasses
    _MAP_GETTERS: ClassVar[Mapping[str, Callable[[Any, str], Any]]] = {}

    #: Optional setter mapping for :class:`Options` subclasses
    _MAP_SETTERS: ClassVar[Mapping[str, Callable[[Any, str, Any], None]]] = {}

    def __init__(self, defaults: Mapping[str, Any] | None = None):
        super().__init__()
        self._defaults = self._normalize_dict(defaults or {})
        super().update(self._defaults)

    @staticmethod
    def _normalize_key(name: str) -> str:
        return name.replace("_", "-")

    @classmethod
    def _normalize_dict(cls, src: Mapping[str, Any]) -> dict[str, Any]:
        normalize_key = cls._normalize_key
        return {normalize_key(key): value for key, value in src.items()}

    @property
    def defaults(self):
        return self._defaults

    def clear(self) -> None:
        """Restore default options"""

        super().clear()
        self.update(self._defaults)

    def get(self, key: str) -> Any:  # type: ignore[override]
        """Get the stored value of a specific key"""

        normalized = self._normalize_key(key)
        method = self._MAP_GETTERS.get(normalized)
        if method is not None:
            return method(self, normalized)
        else:
            return super().get(normalized)

    def get_explicit(self, key: str) -> Any:
        """Get the stored value of a specific key and ignore any get-mappings"""

        normalized = self._normalize_key(key)
        return super().get(normalized)

    def set(self, key: str, value: Any) -> None:
        """Set the value for a specific key"""

        normalized = self._normalize_key(key)
        method = self._MAP_SETTERS.get(normalized)
        if method is not None:
            method(self, normalized, value)
        else:
            super().__setitem__(normalized, value)

    def set_explicit(self, key: str, value: Any) -> None:
        """Set the value for a specific key and ignore any set-mappings"""

        normalized = self._normalize_key(key)
        super().__setitem__(normalized, value)

    # noinspection PyMethodOverriding
    def update(self, options: Mapping[str, Any]) -> None:  # type: ignore[override]
        """Merge options"""

        for key, value in options.items():
            self.set(key, value)

    def __getitem__(self, item):
        return self.get(item)

    def __setitem__(self, item, value):
        return self.set(item, value)


_TChoices = TypeVar("_TChoices", bound=Iterable)


class Argument:
    # noinspection PyShadowingBuiltins
    def __init__(
        self,
        name: str,
        # `ArgumentParser.add_argument()` keywords
        action: str | None = None,
        nargs: int | Literal["?", "*", "+"] | None = None,
        const: Any = None,
        default: Any = None,
        type: Callable[[Any], _TChoices | Any] | None = None,  # noqa: A002
        choices: _TChoices | None = None,
        required: bool = False,
        help: str | None = None,  # noqa: A002
        metavar: str | list[str] | tuple[str, ...] | None = None,
        dest: str | None = None,
        # additional `Argument()` keywords
        requires: str | list[str] | tuple[str, ...] | None = None,
        prompt: str | None = None,
        sensitive: bool = False,
        argument_name: str | None = None,
    ):
        """
        Accepts most of the parameters accepted by :meth:`argparse.ArgumentParser.add_argument()`, except that

        - ``name`` is the name relative to the plugin name (can be overridden by ``argument_name``)
          and that only one argument name is supported
        - ``action`` must be a string and can't be a custom :class:`Action <argparse.Action>`
        - ``required`` is a special case which is only enforced if the plugin is in use

        This class should not be instantiated directly.
        See the :func:`pluginargument <streamlink.plugin.pluginargument>` decorator for adding custom plugin arguments.

        :param name: Argument name, without leading ``--`` or plugin name prefixes, e.g. ``"username"``, ``"password"``, etc.
        :param action: See :meth:`ArgumentParser.add_argument()`
        :param nargs: See :meth:`ArgumentParser.add_argument()`
        :param const: See :meth:`ArgumentParser.add_argument()`
        :param default: See :meth:`ArgumentParser.add_argument()`
        :param type: See :meth:`ArgumentParser.add_argument()`
        :param choices: See :meth:`ArgumentParser.add_argument()`
        :param required: See :meth:`ArgumentParser.add_argument()`
        :param help: See :meth:`ArgumentParser.add_argument()`
        :param metavar: See :meth:`ArgumentParser.add_argument()`
        :param dest: See :meth:`ArgumentParser.add_argument()`
        :param requires: List of other arguments which this argument requires, e.g. ``["password"]``
        :param prompt: If the argument is required and not set, then this prompt message will be shown instead
        :param sensitive: Whether the argument is sensitive and should be masked (passwords, etc.)
        :param argument_name: Custom CLI argument name without the automatically added plugin name prefix
        """

        self.name = name

        self.action = action
        self.nargs = nargs
        self.const = const
        self.type = type
        self.choices: tuple[Any, ...] | None = tuple(choices) if choices else None
        self.required = required
        # argparse compares the object identity of argparse.SUPPRESS
        self.help = argparse.SUPPRESS if help == argparse.SUPPRESS else help
        self.metavar: str | tuple[str, ...] | None = (
            tuple(metavar)
            if metavar is not None and not isinstance(metavar, str)
            else metavar
        )  # fmt: skip

        self._default = default
        self._dest = self._normalize_dest(dest) if dest else None

        self.requires: tuple[str, ...] = (
            tuple(requires)
            if requires is not None and not isinstance(requires, str)
            else ((requires,) if requires is not None else ())
        )
        self.prompt = prompt
        self.sensitive = sensitive
        self._argument_name = self._normalize_name(argument_name) if argument_name else None

        # special cases for storing the default value to check whether a plugin argument was set or not
        if action == "store_true":
            self.const = True
            self._default = False if default is None else default
        elif action == "store_false":
            self.const = False
            self._default = True if default is None else default

    @staticmethod
    def _normalize_name(name: str) -> str:
        return name.replace("_", "-").strip("-")

    @staticmethod
    def _normalize_dest(name: str) -> str:
        return name.replace("-", "_")

    def _name(self, plugin):
        return self._argument_name or self._normalize_name(f"{plugin}-{self.name}")

    def argument_name(self, plugin):
        return f"--{self._name(plugin)}"

    def namespace_dest(self, plugin):
        return self._normalize_dest(self._name(plugin))

    @property
    def dest(self) -> str:
        return self._dest or self._normalize_dest(self.name)

    @property
    def default(self):  # read-only
        return self._default

    # `ArgumentParser.add_argument()` keywords, except `name_or_flags` and `required`
    _ARGPARSE_ARGUMENT_KEYWORDS: ClassVar[Mapping[str, str]] = {
        "action": "action",
        "nargs": "nargs",
        "const": "const",
        "default": "default",
        "type": "type",
        "choices": "choices",
        "help": "help",
        "metavar": "metavar",
        "dest": "_dest",
    }

    @property
    def options(self) -> Mapping[str, Any]:
        return {
            name: getattr(self, attr)
            for name, attr in self._ARGPARSE_ARGUMENT_KEYWORDS.items()
            # don't pass keywords with ``None`` values to ``ArgumentParser.add_argument()``
            if (
                getattr(self, attr) is not None
                # don't include the const option value if the action is store_true or store_false
                and not (name == "const" and self.action in ("store_true", "store_false"))
            )
        }

    def __hash__(self):
        return hash((
            self.name,
            self.action,
            self.nargs,
            self.const,
            self.type,
            self.choices,
            self.required,
            self.help,
            self.metavar,
            self._default,
            self._dest,
            self.requires,
            self.prompt,
            self.sensitive,
            self._argument_name,
        ))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and hash(self) == hash(other)


class Arguments(Dict[str, Argument]):
    """
    A collection of :class:`Argument` instances for :class:`Plugin <streamlink.plugin.Plugin>` classes.

    Should not be called directly, see the :func:`pluginargument <streamlink.plugin.pluginargument>` decorator.
    """

    def __init__(self, *args):
        # keep the initial arguments of the constructor in reverse order (see __iter__())
        super().__init__({arg.name: arg for arg in reversed(args)})

    def __iter__(self) -> Iterator[Argument]:  # type: ignore[override]
        # iterate in reverse order due to add() being called by multiple pluginargument decorators in reverse order
        return reversed(self.values())

    def __hash__(self):
        return hash(tuple(self.items()))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and hash(self) == hash(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def add(self, argument: Argument) -> None:
        self[argument.name] = argument

    def requires(self, name: str) -> Iterator[Argument]:
        """
        Find all :class:`Argument` instances required by name
        """

        results = {name}
        argument = self.get(name)
        for reqname in argument.requires if argument else []:
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


__all__ = [
    "Argument",
    "Arguments",
    "Options",
]
