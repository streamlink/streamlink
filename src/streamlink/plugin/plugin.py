import operator
import re

from functools import partial

from ..cache import Cache
from ..exceptions import PluginError, NoStreamsError
from ..options import Options


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
        "hq":  576,
        "sq":  360,
    },
}


FILTER_OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


def stream_weight(stream):
    for group, weights in QUALITY_WEIGTHS_EXTRA.items():
        if stream in weights:
            return weights[stream], group

    match = re.match("^(\d+)([k]|[p])?(\d*)([\+])?$", stream)

    if match:
        if match.group(2) == "k":
            bitrate = int(match.group(1))

            # FIXME: This is a crude attempt at making a bitrate's
            # weight end up similar to the weight of a resolution.
            # Someone who knows math, please fix.
            weight = bitrate / 2.8

            return weight, "bitrate"

        elif match.group(2) == "p":
            weight = int(match.group(1))

            if match.group(3):
                weight += int(match.group(3))

            if match.group(4) == "+":
                weight += 1

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
        prio = 99

    return prio


def stream_sorting_filter(expr, stream_weight):
    match = re.match(r"(?P<op><=|>=|<|>)?(?P<value>[\w\+]+)", expr)

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


class Plugin(object):
    """A plugin can retrieve stream information from the URL specified.

    :param url: URL that the plugin will operate on
    """

    cache = None
    logger = None
    module = "unknown"
    options = Options()
    session = None

    @classmethod
    def bind(cls, session, module):
        cls.cache = Cache(filename="plugin-cache.json",
                          key_prefix=module)
        cls.logger = session.logger.new_module("plugin." + module)
        cls.module = module
        cls.session = session

    def __init__(self, url):
        self.url = url

    @classmethod
    def can_handle_url(cls, url):
        raise NotImplementedError

    @classmethod
    def set_option(cls, key, value):
        cls.options.set(key, value)

    @classmethod
    def get_option(cls, key):
        return cls.options.get(key)

    @classmethod
    def stream_weight(cls, stream):
        return stream_weight(stream)

    @classmethod
    def default_stream_types(cls, streams):
        stream_types = ["rtmp", "hls", "hds", "http"]

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
        """Attempts to extract available streams.

        Returns a :class:`dict` containing the streams, where the key is
        the name of the stream, most commonly the quality and the value
        is a :class:`Stream` object.

        The result can contain the synonyms **best** and **worst** which
        points to the streams which are likely to be of highest and
        lowest quality respectively.

        If multiple streams with the same name are found, the order of
        streams specified in *stream_types* will determine which stream
        gets to keep the name while the rest will be renamed to
        "<name>_<stream type>".

        The synonyms can be fine tuned with the *sorting_excludes*
        parameter. This can be either of these types:

            - A list of filter expressions in the format
              *[operator]<value>*. For example the filter ">480p" will
              exclude streams ranked higher than "480p" from the list
              used in the synonyms ranking. Valid operators are >, >=, <
              and <=. If no operator is specified then equality will be
              tested.

            - A function that is passed to filter() with a list of
              stream names as input.


        :param stream_types: A list of stream types to return.
        :param sorting_excludes: Specify which streams to exclude from
                                 the best/worst synonyms.


        .. versionchanged:: 1.4.2
           Added *priority* parameter.

        .. versionchanged:: 1.5.0
           Renamed *priority* to *stream_types* and changed behaviour
           slightly.

        .. versionchanged:: 1.5.0
           Added *sorting_excludes* parameter.

        .. versionchanged:: 1.6.0
           *sorting_excludes* can now be a list of filter expressions
           or a function that is passed to filter().


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
        except (IOError, OSError, ValueError) as err:
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

            if stream_type not in stream_types:
                continue

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
                self.logger.debug("The stream '{0}' has been ignored "
                                  "since it is badly named.", name)
                continue

            # Force lowercase name and replace space with underscore.
            streams[name.lower()] = stream

        # Create the best/worst synonmys
        stream_weight_only = lambda s: (self.stream_weight(s)[0] or
                                        (len(streams) == 1 and 1))
        stream_names = filter(stream_weight_only, streams.keys())
        sorted_streams = sorted(stream_names, key=stream_weight_only)

        if isinstance(sorting_excludes, list):
            for expr in sorting_excludes:
                filter_func = stream_sorting_filter(expr, self.stream_weight)
                sorted_streams = list(filter(filter_func, sorted_streams))
        elif callable(sorting_excludes):
            sorted_streams = list(filter(sorting_excludes, sorted_streams))

        if len(sorted_streams) > 0:
            best = sorted_streams[-1]
            worst = sorted_streams[0]
            streams["best"] = streams[best]
            streams["worst"] = streams[worst]

        return streams

    def get_streams(self, *args, **kwargs):
        """Deprecated since version 1.9.0.

        Has been renamed to :func:`Plugin.streams`, this is an alias
        for backwards compatibility.
        """

        return self.streams(*args, **kwargs)

    def _get_streams(self):
        raise NotImplementedError


__all__ = ["Plugin"]
