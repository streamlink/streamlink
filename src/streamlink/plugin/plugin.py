import ast
import logging
import operator
import re
import time
from functools import partial
from typing import Any, Callable, ClassVar, Dict, List, Match, NamedTuple, Optional, Pattern, Sequence, Type, Union

import requests.cookies

from streamlink.cache import Cache
from streamlink.exceptions import FatalPluginError, NoStreamsError, PluginError
from streamlink.options import Argument, Arguments, Options
from streamlink.user_input import UserInputRequester


log = logging.getLogger(__name__)

# FIXME: This is a crude attempt at making a bitrate's
# weight end up similar to the weight of a resolution.
# Someone who knows math, please fix.
BIT_RATE_WEIGHT_RATIO = 2.8

ALT_WEIGHT_MOD = 0.01

QUALITY_WEIGTHS_EXTRA = {
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


def stream_weight(stream):
    for group, weights in QUALITY_WEIGTHS_EXTRA.items():
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
                yield (name, sub_stream)
        else:
            yield (name, stream)


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


def parse_params(params: Optional[str] = None) -> Dict[str, Any]:
    rval: Dict[str, Any] = {}
    if not params:
        return rval

    matches = re.findall(PARAMS_REGEX, params)

    for key, value in matches:
        try:
            value = ast.literal_eval(value)
        except Exception:
            pass

        rval[key] = value

    return rval


class Matcher(NamedTuple):
    pattern: Pattern
    priority: int


class Plugin:
    """
    Plugin base class for retrieving streams and metadata from the URL specified.
    """

    matchers: ClassVar[Optional[List[Matcher]]] = None
    """
    The list of plugin matchers (URL pattern + priority).
    Use the :meth:`streamlink.plugin.pluginmatcher` decorator for initializing this list.
    """

    matches: Sequence[Optional[Match]]
    """A tuple of :class:`re.Match` results of all defined matchers"""

    matcher: Optional[Pattern]
    """A reference to the compiled :class:`re.Pattern` of the first matching matcher"""

    match: Optional[Match]
    """A reference to the :class:`re.Match` result of the first matching matcher"""

    # plugin metadata attributes
    id: Optional[str] = None
    """Metadata 'id' attribute: unique stream ID, etc."""
    title: Optional[str] = None
    """Metadata 'title' attribute: the stream's short descriptive title"""
    author: Optional[str] = None
    """Metadata 'author' attribute: the channel or broadcaster name, etc."""
    category: Optional[str] = None
    """Metadata 'category' attribute: name of a game being played, a music genre, etc."""

    cache = None
    logger = None
    module = "unknown"
    options = Options()
    arguments: Optional[Arguments] = None
    session = None
    _url: Optional[str] = None

    # deprecated
    can_handle_url: Callable[[str], bool]
    # deprecated
    priority: Callable[[str], int]

    @classmethod
    def bind(cls, session, module):
        cls.cache = Cache(filename="plugin-cache.json",
                          key_prefix=module)
        cls.logger = logging.getLogger("streamlink.plugins." + module)
        cls.module = module
        cls.session = session

    @property
    def url(self) -> Optional[str]:
        """
        The plugin's input URL.
        Setting a new value will automatically update the :attr:`matches`, :attr:`matcher` and :attr:`match` data.
        """

        return self._url

    @url.setter
    def url(self, value: str):
        self._url = value

        matches = [(pattern, pattern.match(value)) for pattern, priority in self.matchers or []]
        self.matches = tuple(m for p, m in matches)
        self.matcher, self.match = next(((p, m) for p, m in matches if m is not None), (None, None))

    def __init__(self, url: str):
        """
        :param str url: URL that the plugin will operate on
        """

        self.url = url

        try:
            self.load_cookies()
        except RuntimeError:
            pass  # unbound cannot load

    @classmethod
    def set_option(cls, key, value):
        cls.options.set(key, value)

    @classmethod
    def get_option(cls, key):
        return cls.options.get(key)

    @classmethod
    def get_argument(cls, key):
        return cls.arguments.get(key)

    @classmethod
    def stream_weight(cls, stream):
        return stream_weight(stream)

    @classmethod
    def default_stream_types(cls, streams):
        stream_types = ["hls", "http"]

        for name, stream in iterate_streams(streams):
            stream_type = type(stream).shortname()

            if stream_type not in stream_types:
                stream_types.append(stream_type)

        return stream_types

    @classmethod
    def broken(cls, issue=None):
        def func(*args, **kwargs):
            msg = (
                "This plugin has been marked as broken. This is likely due to "
                "changes to the service preventing a working implementation. "
            )

            if issue:
                msg += "More info: https://github.com/streamlink/streamlink/issues/{0}".format(issue)

            raise PluginError(msg)

        def decorator(*args, **kwargs):
            return func

        return decorator

    def streams(self, stream_types=None, sorting_excludes=None):
        """
        Attempts to extract available streams.

        Returns a :class:`dict` containing the streams, where the key is
        the name of the stream (most commonly the quality name), with the value
        being a :class:`Stream` instance.

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
        :returns: A :class:`dict` of stream names and :class:`streamlink.stream.Stream` instances
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
            raise PluginError(err)

        if not ostreams:
            return {}

        if stream_types is None:
            stream_types = self.default_stream_types(ostreams)

        # Add streams depending on stream type and priorities
        sorted_streams = sorted(iterate_streams(ostreams),
                                key=partial(stream_type_priority,
                                            stream_types))

        streams = {}
        for name, stream in sorted_streams:
            stream_type = type(stream).shortname()

            # Use * as wildcard to match other stream types
            if "*" not in stream_types and stream_type not in stream_types:
                continue

            # drop _alt from any stream names
            if name.endswith("_alt"):
                name = name[:-len("_alt")]

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
            match = re.match("([A-z0-9_+]+)", name)
            if match:
                name = match.group(1)
            else:
                self.logger.debug(f"The stream '{name}' has been ignored since it is badly named.")
                continue

            # Force lowercase name and replace space with underscore.
            streams[name.lower()] = stream

        # Create the best/worst synonyms
        def stream_weight_only(s):
            return (self.stream_weight(s)[0] or (len(streams) == 1 and 1))

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

        Needs to return either a dict of :class:`streamlink.stream.Stream` instances mapped by stream name, or needs to act
        as a generator which yields tuples of stream names and :class:`streamlink.stream.Stream` instances.
        """

        raise NotImplementedError

    def get_metadata(self) -> Dict[str, Optional[str]]:
        return dict(
            id=self.get_id(),
            author=self.get_author(),
            category=self.get_category(),
            title=self.get_title()
        )

    def get_id(self) -> Optional[str]:
        return None if self.id is None else str(self.id).strip()

    def get_title(self) -> Optional[str]:
        return None if self.title is None else str(self.title).strip()

    def get_author(self) -> Optional[str]:
        return None if self.author is None else str(self.author).strip()

    def get_category(self) -> Optional[str]:
        return None if self.category is None else str(self.category).strip()

    def save_cookies(
        self,
        cookie_filter: Optional[Callable] = None,
        default_expires: int = 60 * 60 * 24 * 7
    ) -> List[str]:
        """
        Store the cookies from :attr:`session.http` in the plugin cache until they expire. The cookies can be filtered
        by supplying a filter method. e.g. ``lambda c: "auth" in c.name``. If no expiry date is given in the
        cookie then the ``default_expires`` value will be used.

        :param cookie_filter: a function to filter the cookies
        :param default_expires: time (in seconds) until cookies with no expiry will expire
        :return: list of the saved cookie names
        """

        if not self.session or not self.cache:
            raise RuntimeError("Cannot cache cookies in unbound plugin")

        cookie_filter = cookie_filter or (lambda c: True)
        saved = []

        for cookie in filter(cookie_filter, self.session.http.cookies):
            cookie_dict = {}
            for attr in ("version", "name", "value", "port", "domain", "path", "secure", "expires", "discard",
                         "comment", "comment_url", "rfc2109"):
                cookie_dict[attr] = getattr(cookie, attr, None)
            cookie_dict["rest"] = getattr(cookie, "rest", getattr(cookie, "_rest", None))

            expires = default_expires
            if cookie_dict['expires']:
                expires = int(cookie_dict['expires'] - time.time())
            key = "__cookie:{0}:{1}:{2}:{3}".format(cookie.name,
                                                    cookie.domain,
                                                    cookie.port_specified and cookie.port or "80",
                                                    cookie.path_specified and cookie.path or "*")
            self.cache.set(key, cookie_dict, expires)
            saved.append(cookie.name)

        if saved:
            self.logger.debug("Saved cookies: {0}".format(", ".join(saved)))
        return saved

    def load_cookies(self) -> List[str]:
        """
        Load any stored cookies for the plugin that have not expired.

        :return: list of the restored cookie names
        """

        if not self.session or not self.cache:
            raise RuntimeError("Cannot load cached cookies in unbound plugin")

        restored = []

        for key, value in self.cache.get_all().items():
            if key.startswith("__cookie"):
                cookie = requests.cookies.create_cookie(**value)
                self.session.http.cookies.set_cookie(cookie)
                restored.append(cookie.name)

        if restored:
            self.logger.debug("Restored cookies: {0}".format(", ".join(restored)))
        return restored

    def clear_cookies(self, cookie_filter: Optional[Callable] = None) -> List[str]:
        """
        Removes all saved cookies for this plugin. To filter the cookies that are deleted
        specify the ``cookie_filter`` argument (see :func:`save_cookies`).

        :param cookie_filter: a function to filter the cookies
        :type cookie_filter: function
        :return: list of the removed cookie names
        """

        if not self.session or not self.cache:
            raise RuntimeError("Cannot clear cached cookies in unbound plugin")

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
        user_input_requester: Optional[UserInputRequester] = self.session.get_option("user-input-requester")  # type: ignore
        if user_input_requester:
            try:
                return user_input_requester.ask(prompt)
            except OSError as err:
                raise FatalPluginError(f"User input error: {err}")
        raise FatalPluginError("This plugin requires user input, however it is not supported on this platform")

    def input_ask_password(self, prompt: str) -> str:
        user_input_requester: Optional[UserInputRequester] = self.session.get_option("user-input-requester")  # type: ignore
        if user_input_requester:
            try:
                return user_input_requester.ask_password(prompt)
            except OSError as err:
                raise FatalPluginError(f"User input error: {err}")
        raise FatalPluginError("This plugin requires user input, however it is not supported on this platform")


def pluginmatcher(pattern: Pattern, priority: int = NORMAL_PRIORITY) -> Callable[[Type[Plugin]], Type[Plugin]]:
    matcher = Matcher(pattern, priority)

    def decorator(cls: Type[Plugin]) -> Type[Plugin]:
        if not issubclass(cls, Plugin):
            raise TypeError(f"{repr(cls)} is not a Plugin")
        if cls.matchers is None:
            cls.matchers = []
        cls.matchers.insert(0, matcher)

        return cls

    return decorator


def pluginargument(
    name: str,
    required: bool = False,
    requires: Optional[Union[str, Sequence[str]]] = None,
    prompt: Optional[str] = None,
    sensitive: bool = False,
    argument_name: Optional[str] = None,
    dest: Optional[str] = None,
    is_global: bool = False,
    **options,
):
    arg = Argument(
        name,
        required=required,
        requires=requires,
        prompt=prompt,
        sensitive=sensitive,
        argument_name=argument_name,
        dest=dest,
        is_global=is_global,
        **options,
    )

    def decorator(cls: Type[Plugin]) -> Type[Plugin]:
        if not issubclass(cls, Plugin):
            raise TypeError(f"{repr(cls)} is not a Plugin")
        if cls.arguments is None:
            cls.arguments = Arguments()
        cls.arguments.add(arg)

        return cls

    return decorator


__all__ = [
    "HIGH_PRIORITY", "NORMAL_PRIORITY", "LOW_PRIORITY", "NO_PRIORITY",
    "Plugin",
    "Matcher", "pluginmatcher",
    "pluginargument",
]
