from __future__ import annotations

import ast
import logging
import operator
import re
import time
from collections.abc import Callable, Iterable, Mapping
from contextlib import suppress
from functools import partial
from http.cookiejar import Cookie
from typing import TYPE_CHECKING, Any, ClassVar, List, Literal, NamedTuple, Type, TypeVar, Union

import requests.cookies

import streamlink.utils.args
import streamlink.utils.times
from streamlink.cache import Cache
from streamlink.exceptions import FatalPluginError, NoStreamsError, PluginError
from streamlink.options import Argument, Arguments, Options
from streamlink.user_input import UserInputRequester


if TYPE_CHECKING:  # pragma: no cover
    from streamlink.session.session import Streamlink


#: See the :func:`~.pluginargument` decorator
_PLUGINARGUMENT_TYPE_REGISTRY: Mapping[str, Callable[[Any], Any]] = {
    "int": int,
    "float": float,
    "bool": streamlink.utils.args.boolean,
    "comma_list": streamlink.utils.args.comma_list,
    "comma_list_filter": streamlink.utils.args.comma_list_filter,
    "filesize": streamlink.utils.args.filesize,
    "keyvalue": streamlink.utils.args.keyvalue,
    "num": streamlink.utils.args.num,
    "hours_minutes_seconds": streamlink.utils.times.hours_minutes_seconds,
    "hours_minutes_seconds_float": streamlink.utils.times.hours_minutes_seconds_float,
}


log = logging.getLogger(__name__)

# FIXME: This is a crude attempt at making a bitrate's
# weight end up similar to the weight of a resolution.
# Someone who knows math, please fix.
BIT_RATE_WEIGHT_RATIO = 2.8

ALT_WEIGHT_MOD = 0.01

QUALITY_WEIGHTS_EXTRA = {
    "other": {
        "live": 1080,
    },
    "tv": {
        "hd": 1080,
        "sd": 576,
    },
    "quality": {
        "ehq": 720,
        "hq": 576,
        "sq": 360,
    },
}

FILTER_OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}

PARAMS_REGEX = r"(\w+)=({.+?}|\[.+?\]|\(.+?\)|'(?:[^'\\]|\\')*'|\"(?:[^\"\\]|\\\")*\"|\S+)"

HIGH_PRIORITY = 30
NORMAL_PRIORITY = 20
LOW_PRIORITY = 10
NO_PRIORITY = 0

_COOKIE_KEYS = (
    "version",
    "name",
    "value",
    "port",
    "domain",
    "path",
    "secure",
    "expires",
    "discard",
    "comment",
    "comment_url",
    "rfc2109",
)


def stream_weight(stream):
    for group, weights in QUALITY_WEIGHTS_EXTRA.items():
        if stream in weights:
            return weights[stream], group

    match = re.match(r"^(\d+)(k|p)?(\d+)?(\+)?(?:[a_](\d+)k)?(?:_(alt)(\d)?)?$", stream)

    if match:
        weight = 0

        if match.group(6):
            if match.group(7):
                weight -= ALT_WEIGHT_MOD * int(match.group(7))
            else:
                weight -= ALT_WEIGHT_MOD

        name_type = match.group(2)
        if name_type == "k":  # bit rate
            bitrate = int(match.group(1))
            weight += bitrate / BIT_RATE_WEIGHT_RATIO

            return weight, "bitrate"

        elif name_type == "p":  # resolution
            weight += int(match.group(1))

            if match.group(3):  # fps eg. 60p or 50p
                weight += int(match.group(3))

            if match.group(4) == "+":
                weight += 1

            if match.group(5):  # bit rate classifier for resolution
                weight += int(match.group(5)) / BIT_RATE_WEIGHT_RATIO

            return weight, "pixels"

    return 0, "none"


def iterate_streams(streams):
    for name, stream in streams:
        if isinstance(stream, list):
            for sub_stream in stream:
                yield name, sub_stream
        else:
            yield name, stream


def stream_type_priority(stream_types, stream):
    stream_type = type(stream[1]).shortname()

    try:
        prio = stream_types.index(stream_type)
    except ValueError:
        try:
            prio = stream_types.index("*")
        except ValueError:
            prio = 99

    return prio


def stream_sorting_filter(expr, stream_weight):
    match = re.match(r"(?P<op><=|>=|<|>)?(?P<value>[\w+]+)", expr)

    if not match:
        raise PluginError("Invalid filter expression: {0}".format(expr))

    op, value = match.group("op", "value")
    op = FILTER_OPERATORS.get(op, operator.eq)
    filter_weight, filter_group = stream_weight(value)

    def func(quality):
        weight, group = stream_weight(quality)

        if group == filter_group:
            return not op(weight, filter_weight)

        return True

    return func


def parse_params(params: str | None = None) -> dict[str, Any]:
    rval: dict[str, Any] = {}
    if not params:
        return rval

    matches = re.findall(PARAMS_REGEX, params)

    for key, value in matches:
        with suppress(Exception):
            value = ast.literal_eval(value)
        rval[key] = value

    return rval


class Matcher(NamedTuple):
    pattern: re.Pattern
    priority: int
    name: str | None = None


MType = TypeVar("MType")


class _MCollection(List[MType]):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._names: dict[str, MType] = {}

    def __getitem__(self, item):
        return self._names[item] if isinstance(item, str) else super().__getitem__(item)


class Matchers(_MCollection[Matcher]):
    def __init__(self, *matchers):
        super().__init__(matchers)
        for matcher in matchers:
            self._add_named_matcher(matcher)

    def add(self, matcher: Matcher) -> None:
        super().insert(0, matcher)
        self._add_named_matcher(matcher)

    def _add_named_matcher(self, matcher: Matcher) -> None:
        if matcher.name:
            if matcher.name in self._names:
                raise ValueError(f"A matcher named '{matcher.name}' has already been registered")
            self._names[matcher.name] = matcher


class Matches(_MCollection[Union[re.Match, None]]):
    def update(self, matchers: Matchers, value: str) -> tuple[re.Pattern | None, re.Match | None]:
        matches = [(matcher, matcher.pattern.match(value)) for matcher in matchers]

        self.clear()
        self.extend(match for matcher, match in matches)
        self._names.clear()
        self._names.update((matcher.name, match) for matcher, match in matches if matcher.name)

        return next(((matcher.pattern, match) for matcher, match in matches if match is not None), (None, None))


class PluginMeta(type):
    def __init__(cls, name, bases, namespace, **kwargs):
        super().__init__(name, bases, namespace, **kwargs)
        cls.matchers = Matchers(*getattr(cls, "matchers", []))
        cls.arguments = Arguments(*getattr(cls, "arguments", []))


class Plugin(metaclass=PluginMeta):
    """
    Plugin base class for retrieving streams and metadata from the URL specified.
    """

    #: The Streamlink session which this plugin instance belongs to,
    #: with access to its :attr:`HTTPSession <streamlink.session.Streamlink.http>`.
    session: Streamlink

    #: Plugin options, initialized with the user-set values of the plugin's arguments.
    options: Options

    #: Plugin cache object, used to store plugin-specific data other than HTTP session cookies.
    cache: Cache

    #: The list of plugin matchers (URL pattern + priority + optional name).
    #: Supports matcher lookups by the matcher index or the optional matcher name.
    #:
    #: Use the :func:`pluginmatcher` decorator to initialize plugin matchers.
    matchers: ClassVar[Matchers]

    #: The plugin's :class:`Arguments <streamlink.options.Arguments>` collection.
    #:
    #: Use the :func:`pluginargument` decorator to initialize plugin arguments.
    arguments: ClassVar[Arguments]

    #: A list of optional :class:`re.Match` results of all defined matchers.
    #: Supports match lookups by the matcher index or the optional matcher name.
    matches: Matches

    #: A reference to the compiled :class:`re.Pattern` of the first matching matcher.
    matcher: re.Pattern | None = None

    #: A reference to the :class:`re.Match` result of the first matching matcher.
    match: re.Match | None = None

    #: Metadata 'id' attribute: unique stream ID, etc.
    id: str | None = None
    #: Metadata 'title' attribute: the stream's short descriptive title.
    title: str | None = None
    #: Metadata 'author' attribute: the channel or broadcaster name, etc.
    author: str | None = None
    #: Metadata 'category' attribute: name of a game being played, a music genre, etc.
    category: str | None = None

    _url: str = ""

    def __init__(self, session: Streamlink, url: str, options: Mapping[str, Any] | Options | None = None):
        """
        :param session: The Streamlink session instance
        :param url: The input URL used for finding and resolving streams
        :param options: An optional :class:`Options` instance
        """

        modulename = self.__class__.__module__
        self.module = modulename.split(".")[-1]
        self.logger = logging.getLogger(modulename)

        self.options = Options(options)

        self.cache = Cache(
            filename="plugin-cache.json",
            key_prefix=self.module,
        )

        self.session: Streamlink = session
        self.matches = Matches()
        self.url: str = url

        self.load_cookies()

    @property
    def url(self) -> str:
        """
        The plugin's input URL.
        Setting a new value will automatically update the :attr:`matches`, :attr:`matcher` and :attr:`match` data.
        """

        return self._url

    @url.setter
    def url(self, value: str):
        self._url = value

        if self.matchers:
            self.matcher, self.match = self.matches.update(self.matchers, value)

    def set_option(self, key, value):
        self.options.set(key, value)

    def get_option(self, key):
        return self.options.get(key)

    @classmethod
    def get_argument(cls, key):
        return cls.arguments and cls.arguments.get(key)

    @classmethod
    def stream_weight(cls, stream):
        return stream_weight(stream)

    @classmethod
    def default_stream_types(cls, streams):
        stream_types = ["hls", "http"]

        for _name, stream in iterate_streams(streams):
            stream_type = type(stream).shortname()

            if stream_type not in stream_types:
                stream_types.append(stream_type)

        return stream_types

    def streams(self, stream_types=None, sorting_excludes=None):
        """
        Attempts to extract available streams.

        Returns a :class:`dict` containing the streams, where the key is
        the name of the stream (most commonly the quality name), with the value
        being a :class:`Stream <streamlink.stream.Stream>` instance.

        The result can contain the synonyms **best** and **worst** which
        point to the streams which are likely to be of highest and
        lowest quality respectively.

        If multiple streams with the same name are found, the order of
        streams specified in *stream_types* will determine which stream
        gets to keep the name while the rest will be renamed to
        "<name>_<stream type>".

        The synonyms can be fine-tuned with the *sorting_excludes*
        parameter, which can be one of these types:

            - A list of filter expressions in the format
              ``[operator]<value>``. For example the filter ">480p" will
              exclude streams ranked higher than "480p" from the list
              used in the synonyms ranking. Valid operators are ``>``, ``>=``, ``<``
              and ``<=``. If no operator is specified then equality will be tested.

            - A function that is passed to :meth:`filter` with a list of
              stream names as input.


        :param stream_types: A list of stream types to return
        :param sorting_excludes: Specify which streams to exclude from the best/worst synonyms
        :returns: A :class:`dict` of stream names and :class:`Stream <streamlink.stream.Stream>` instances
        """

        try:
            ostreams = self._get_streams()
            if isinstance(ostreams, dict):
                ostreams = ostreams.items()

            # Flatten the iterator to a list so we can reuse it.
            if ostreams:
                ostreams = list(ostreams)
        except NoStreamsError:
            return {}
        except (OSError, ValueError) as err:
            raise PluginError(err) from err

        if not ostreams:
            return {}

        if stream_types is None:
            stream_types = self.default_stream_types(ostreams)

        # Add streams depending on stream type and priorities
        sorted_streams = sorted(iterate_streams(ostreams), key=partial(stream_type_priority, stream_types))

        streams = {}
        for name, stream in sorted_streams:
            stream_type = type(stream).shortname()

            # Use * as wildcard to match other stream types
            if "*" not in stream_types and stream_type not in stream_types:
                continue

            # drop _alt from any stream names
            if name.endswith("_alt"):
                name = name[: -len("_alt")]

            existing = streams.get(name)
            if existing:
                existing_stream_type = type(existing).shortname()
                if existing_stream_type != stream_type:
                    name = "{0}_{1}".format(name, stream_type)

                if name in streams:
                    name = "{0}_alt".format(name)
                    num_alts = len(list(filter(lambda n: n.startswith(name), streams.keys())))

                    # We shouldn't need more than 2 alt streams
                    if num_alts >= 2:
                        continue
                    elif num_alts > 0:
                        name = "{0}{1}".format(name, num_alts + 1)

            # Validate stream name and discard the stream if it's bad.
            match = re.match(r"([A-z0-9_+]+)", name)
            if match:
                name = match.group(1)
            else:
                self.logger.debug(f"The stream '{name}' has been ignored since it is badly named.")
                continue

            # Force lowercase name and replace space with underscore.
            streams[name.lower()] = stream

        # Create the best/worst synonyms
        def stream_weight_only(s):
            return self.stream_weight(s)[0] or (len(streams) == 1 and 1)

        stream_names = filter(stream_weight_only, streams.keys())
        sorted_streams = sorted(stream_names, key=stream_weight_only)
        unfiltered_sorted_streams = sorted_streams

        if isinstance(sorting_excludes, list):
            for expr in sorting_excludes:
                filter_func = stream_sorting_filter(expr, self.stream_weight)
                sorted_streams = list(filter(filter_func, sorted_streams))
        elif callable(sorting_excludes):
            sorted_streams = list(filter(sorting_excludes, sorted_streams))

        final_sorted_streams = {}

        for stream_name in sorted(streams, key=stream_weight_only):
            final_sorted_streams[stream_name] = streams[stream_name]

        if len(sorted_streams) > 0:
            best = sorted_streams[-1]
            worst = sorted_streams[0]
            final_sorted_streams["worst"] = streams[worst]
            final_sorted_streams["best"] = streams[best]
        elif len(unfiltered_sorted_streams) > 0:
            best = unfiltered_sorted_streams[-1]
            worst = unfiltered_sorted_streams[0]
            final_sorted_streams["worst-unfiltered"] = streams[worst]
            final_sorted_streams["best-unfiltered"] = streams[best]

        return final_sorted_streams

    def _get_streams(self):
        """
        Implement the stream and metadata retrieval here.

        Needs to return either a dict of :class:`Stream <streamlink.stream.Stream>` instances mapped by stream name,
        or needs to act as a generator which yields tuples of stream names and :class:`Stream <streamlink.stream.Stream>`
        instances.
        """

        raise NotImplementedError

    def get_metadata(self) -> Mapping[str, str | None]:
        return dict(
            id=self.get_id(),
            author=self.get_author(),
            category=self.get_category(),
            title=self.get_title(),
        )

    def get_id(self) -> str | None:
        return None if self.id is None else str(self.id).strip()

    def get_title(self) -> str | None:
        return None if self.title is None else str(self.title).strip()

    def get_author(self) -> str | None:
        return None if self.author is None else str(self.author).strip()

    def get_category(self) -> str | None:
        return None if self.category is None else str(self.category).strip()

    def save_cookies(
        self,
        cookie_filter: Callable[[Cookie], bool] | None = None,
        default_expires: int = 60 * 60 * 24 * 7,
    ) -> list[str]:
        """
        Store the cookies from :attr:`session.http` in the plugin cache until they expire. The cookies can be filtered
        by supplying a filter method. e.g. ``lambda c: "auth" in c.name``. If no expiry date is given in the
        cookie then the ``default_expires`` value will be used.

        :param cookie_filter: a function to filter the cookies
        :param default_expires: time (in seconds) until cookies with no expiry will expire
        :return: list of the saved cookie names
        """

        cookie_filter = cookie_filter or (lambda c: True)
        saved = []

        for cookie in self.session.http.cookies:
            if not cookie_filter(cookie):
                continue

            cookie_dict = {}
            for key in _COOKIE_KEYS:
                cookie_dict[key] = getattr(cookie, key, None)
            cookie_dict["rest"] = getattr(cookie, "rest", getattr(cookie, "_rest", None))

            expires = default_expires
            if cookie_dict["expires"]:
                expires = int(cookie_dict["expires"] - time.time())
            key = "__cookie:{0}:{1}:{2}:{3}".format(
                cookie.name,
                cookie.domain,
                cookie.port_specified and cookie.port or "80",
                cookie.path_specified and cookie.path or "*",
            )
            self.cache.set(key, cookie_dict, expires)
            saved.append(cookie.name)

        if saved:  # pragma: no branch
            self.logger.debug(f"Saved cookies: {', '.join(saved)}")

        return saved

    def load_cookies(self) -> list[str]:
        """
        Load any stored cookies for the plugin that have not expired.

        :return: list of the restored cookie names
        """

        restored = []

        for key, value in self.cache.get_all().items():
            if key.startswith("__cookie"):
                cookie = requests.cookies.create_cookie(**value)
                self.session.http.cookies.set_cookie(cookie)
                restored.append(cookie.name)

        if restored:  # pragma: no branch
            self.logger.debug(f"Restored cookies: {', '.join(restored)}")

        return restored

    def clear_cookies(self, cookie_filter: Callable[[Cookie], bool] | None = None) -> list[str]:
        """
        Removes all saved cookies for this plugin. To filter the cookies that are deleted
        specify the ``cookie_filter`` argument (see :meth:`save_cookies`).

        :param cookie_filter: a function to filter the cookies
        :type cookie_filter: function
        :return: list of the removed cookie names
        """

        cookie_filter = cookie_filter or (lambda c: True)
        removed = []

        for key, value in sorted(self.cache.get_all().items(), key=operator.itemgetter(0), reverse=True):
            if key.startswith("__cookie"):
                cookie = requests.cookies.create_cookie(**value)
                if cookie_filter(cookie):
                    del self.session.http.cookies[cookie.name]
                    self.cache.set(key, None, 0)
                    removed.append(key)

        return removed

    def input_ask(self, prompt: str) -> str:
        user_input_requester: UserInputRequester | None = self.session.get_option("user-input-requester")
        if user_input_requester:
            try:
                return user_input_requester.ask(prompt)
            except OSError as err:
                raise FatalPluginError(f"User input error: {err}") from err
        raise FatalPluginError("This plugin requires user input, however it is not supported on this platform")

    def input_ask_password(self, prompt: str) -> str:
        user_input_requester: UserInputRequester | None = self.session.get_option("user-input-requester")
        if user_input_requester:
            try:
                return user_input_requester.ask_password(prompt)
            except OSError as err:
                raise FatalPluginError(f"User input error: {err}") from err
        raise FatalPluginError("This plugin requires user input, however it is not supported on this platform")


def pluginmatcher(
    pattern: re.Pattern,
    priority: int = NORMAL_PRIORITY,
    name: str | None = None,
) -> Callable[[type[Plugin]], type[Plugin]]:
    """
    Decorator for plugin URL matchers.

    A matcher consists of a compiled regular expression pattern for the plugin's input URL,
    a priority value and an optional name.
    The priority value determines which plugin gets chosen by
    :meth:`Streamlink.resolve_url() <streamlink.session.Streamlink.resolve_url>` if multiple plugins match the input URL.
    The matcher name can be used for accessing it and its matching result when multiple matchers are defined.

    Plugins must at least have one matcher. If multiple matchers are defined, then the first matching one
    according to the order of which they have been defined (top to bottom) will be responsible for setting the
    :attr:`Plugin.matcher` and :attr:`Plugin.match` attributes on the :class:`Plugin` instance.
    The :attr:`Plugin.matchers` and :attr:`Plugin.matches` attributes are affected by all defined matchers,
    and both support referencing matchers and matches by matcher index and name.

    .. code-block:: python

        import re

        from streamlink.plugin import HIGH_PRIORITY, Plugin, pluginmatcher


        @pluginmatcher(re.compile("https?://example:1234/(?:foo|bar)/(?P<name>[^/]+)"))
        @pluginmatcher(priority=HIGH_PRIORITY, pattern=re.compile(\"\"\"
            https?://(?:
                 sitenumberone
                |adifferentsite
                |somethingelse
            )
            /.+\\.m3u8
        \"\"\", re.VERBOSE))
        class MyPlugin(Plugin):
            ...
    """

    matcher = Matcher(pattern, priority, name)

    def decorator(cls: type[Plugin]) -> type[Plugin]:
        if not issubclass(cls, Plugin):
            raise TypeError(f"{cls.__name__} is not a Plugin")
        cls.matchers.add(matcher)

        return cls

    return decorator


_TChoices = TypeVar("_TChoices", bound=Iterable)


# noinspection GrazieInspection,PyShadowingBuiltins
def pluginargument(
    name: str,
    action: str | None = None,
    nargs: int | Literal["?", "*", "+"] | None = None,
    const: Any = None,
    default: Any = None,
    type: str | Callable[[Any], _TChoices | Any] | None = None,  # noqa: A002
    type_args: list | tuple | None = None,
    type_kwargs: Mapping[str, Any] | None = None,
    choices: _TChoices | None = None,
    required: bool = False,
    help: str | None = None,  # noqa: A002
    metavar: str | list[str] | tuple[str, ...] | None = None,
    dest: str | None = None,
    requires: str | list[str] | tuple[str, ...] | None = None,
    prompt: str | None = None,
    sensitive: bool = False,
    argument_name: str | None = None,
) -> Callable[[type[Plugin]], type[Plugin]]:
    """
    Decorator for plugin arguments. Takes the same arguments as :class:`Argument <streamlink.options.Argument>`.

    One exception is the ``type`` argument, which also accepts a ``str`` value:

    Plugins built into Streamlink **must** reference the used argument-type function by name, so the pluginargument data
    can be JSON-serialized. ``type_args`` and ``type_kwargs`` can be used to parametrize the type-argument function,
    but their values **must** only consist of literal objects.

    The available functions are defined in the :data:`~._PLUGINARGUMENT_TYPE_REGISTRY`.

    .. code-block:: python

        from streamlink.plugin import Plugin, pluginargument


        @pluginargument(
            "username",
            requires=["password"],
            metavar="EMAIL",
            help="The username for your account.",
        )
        @pluginargument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="The password for your account.",
        )
        class MyPlugin(Plugin):
            ...

    This will add the ``--myplugin-username`` and ``--myplugin-password`` arguments to the CLI,
    assuming the plugin's module name is ``myplugin``.
    """

    argument_type: Callable[[Any], _TChoices] | None
    if not isinstance(type, str):
        argument_type = type
    else:
        if type not in _PLUGINARGUMENT_TYPE_REGISTRY:
            raise TypeError(f"Invalid pluginargument type {type}")
        argument_type = _PLUGINARGUMENT_TYPE_REGISTRY[type]
        if type_args is not None or type_kwargs is not None:
            argument_type = argument_type(*(type_args or ()), **(type_kwargs or {}))

    arg = Argument(
        name=name,
        action=action,
        nargs=nargs,
        const=const,
        default=default,
        type=argument_type,
        choices=choices,
        required=required,
        help=help,
        metavar=metavar,
        dest=dest,
        requires=requires,
        prompt=prompt,
        sensitive=sensitive,
        argument_name=argument_name,
    )

    def decorator(cls: Type[Plugin]) -> Type[Plugin]:
        if not issubclass(cls, Plugin):
            raise TypeError(f"{repr(cls)} is not a Plugin")  # noqa: RUF010  # builtins.repr gets monkeypatched in tests
        cls.arguments.add(arg)

        return cls

    return decorator


__all__ = [
    "HIGH_PRIORITY",
    "NORMAL_PRIORITY",
    "LOW_PRIORITY",
    "NO_PRIORITY",
    "Plugin",
    "Matcher",
    "pluginmatcher",
    "pluginargument",
]
