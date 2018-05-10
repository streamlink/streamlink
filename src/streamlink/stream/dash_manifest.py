import datetime
import re
import time
from collections import defaultdict
from collections import namedtuple
from itertools import count, repeat

from streamlink.compat import urlparse, urljoin, urlunparse, izip, urlsplit, urlunsplit

if hasattr(datetime, "timezone"):
    utc = datetime.timezone.utc

else:
    class UTC(datetime.tzinfo):
        def utcoffset(self, dt):
            return datetime.timedelta(0)

        def tzname(self, dt):
            return "UTC"

        def dst(self, dt):
            return datetime.timedelta(0)


    utc = UTC()

from isodate import parse_datetime, parse_duration, Duration
from contextlib import contextmanager

Segment = namedtuple("Segment", "url duration init content available_at")


def datetime_to_seconds(dt):
    return (dt - datetime.datetime(1970, 1, 1, tzinfo=utc)).total_seconds()


@contextmanager
def sleeper(duration):
    s = time.time()
    yield
    time_to_sleep = duration - (time.time() - s)
    if time_to_sleep > 0:
        time.sleep(time_to_sleep)


def sleep_until(walltime):
    c = time.time()
    time_to_wait = walltime - c
    if time_to_wait > 0:
        time.sleep(time_to_wait)


class MPDParsers(object):
    @staticmethod
    def bool_str(v):
        return v.lower() == "true"

    @staticmethod
    def type(type_):
        if type_ not in (u"static", u"dynamic"):
            raise MPDParsingError("@type must be static or dynamic")
        return type_

    @staticmethod
    def duration(duration):
        return parse_duration(duration)

    @staticmethod
    def datetime(dt):
        return parse_datetime(dt).replace(tzinfo=utc)

    @staticmethod
    def segment_template(url_template):
        end = 0
        res = ""
        for m in re.compile(r"(.*?)\$(\w+)(?:%(\w+))?\$").finditer(url_template):
            _, end = m.span()
            res += "{0}{{{1}{2}}}".format(m.group(1),
                                          m.group(2),
                                          (":" + m.group(3)) if m.group(3) else "")
        return (res + url_template[end:]).format

    @staticmethod
    def frame_rate(frame_rate):
        if "/" in frame_rate:
            a, b = frame_rate.split("/")
            return float(a) / float(b)
        else:
            return float(frame_rate)

    @staticmethod
    def timedelta(timescale=1):
        def _timedelta(seconds):
            return datetime.timedelta(seconds=int(float(seconds) / float(timescale)))

        return _timedelta


class MPDParsingError(Exception):
    pass


class MPDNode(object):
    __tag__ = None

    def __init__(self, node, root=None, parent=None, *args, **kwargs):
        self.node = node
        self.root = root
        self.parent = parent
        self._base_url = kwargs.get(u"base_url")
        self.attributes = set([])
        if self.__tag__ and self.node.tag.lower() != self.__tag__.lower():
            raise MPDParsingError("root tag did not match the expected tag: {}".format(self.__tag__))

    @property
    def attrib(self):
        return self.node.attrib

    @property
    def text(self):
        return self.node.text

    def __str__(self):
        return "<{tag} {attrs}>".format(
            tag=self.__tag__,
            attrs=" ".join("@{}={}".format(attr, getattr(self, attr)) for attr in self.attributes)
        )

    def attr(self, key, default=None, parser=None, required=False, inherited=False):
        self.attributes.add(key)
        if key in self.attrib:
            value = self.attrib.get(key)
            if parser and callable(parser):
                return parser(value)
            else:
                return value
        elif inherited:
            if self.parent and hasattr(self.parent, key) and getattr(self.parent, key):
                return getattr(self.parent, key)

        if required:
            raise MPDParsingError("could not find required attribute {tag}@{attr} ".format(attr=key, tag=self.__tag__))
        else:
            return default

    def children(self, cls, minimum=0, maximum=None):

        children = self.node.findall(cls.__tag__)
        if len(children) < minimum or (maximum and len(children) > maximum):
            raise MPDParsingError("expected to find {}/{} required [{}..{})".format(
                self.__tag__, cls.__tag__, minimum, maximum or "unbound"))

        return list(map(lambda x: cls(x[1], root=self.root, parent=self, i=x[0], base_url=self.base_url),
                        enumerate(children)))

    def only_child(self, cls, minimum=0):
        children = self.children(cls, minimum=minimum, maximum=1)
        return children[0] if len(children) else None

    def walk_back(self, cls=None, f=lambda x: x):
        node = self.parent
        while node:
            if cls is None or cls.__tag__ == node.__tag__:
                yield f(node)
            node = node.parent

    def walk_back_get_attr(self, attr):
        parent_attrs = [getattr(n, attr) for n in self.walk_back() if hasattr(n, attr)]
        return parent_attrs[0] if len(parent_attrs) else None

    @property
    def base_url(self):
        base_url = self._base_url
        if hasattr(self, "baseURLs") and len(self.baseURLs):
            base_url = BaseURL.join(base_url, self.baseURLs[0].url)
        return base_url


class MPD(MPDNode):
    """
    Represents the MPD as a whole

    Should validate the XML input and provide methods to get segment URLs for each Period, AdaptationSet and
    Representation.

    """
    __tag__ = u"MPD"

    def __init__(self, node, root=None, parent=None, url=None, *args, **kwargs):
        # top level has no parent
        super(MPD, self).__init__(node, root=self, *args, **kwargs)
        # parser attributes
        self.url = url
        self.timelines = defaultdict(int)
        self.timelines.update(kwargs.pop("timelines", {}))
        self.id = self.attr(u"id")
        self.profiles = self.attr(u"profiles", required=True)
        self.type = self.attr(u"type", default=u"static", parser=MPDParsers.type)
        self.minimumUpdatePeriod = self.attr(u"minimumUpdatePeriod", parser=MPDParsers.duration, default=Duration())
        self.minBufferTime = self.attr(u"minBufferTime", parser=MPDParsers.duration, required=True)
        self.timeShiftBufferDepth = self.attr(u"timeShiftBufferDepth", parser=MPDParsers.duration)
        self.availabilityStartTime = self.attr(u"availabilityStartTime", parser=MPDParsers.datetime,
                                               default=datetime.datetime.fromtimestamp(0, utc),  # earliest date
                                               required=self.type == "dynamic")
        self.publishTime = self.attr(u"publishTime", parser=MPDParsers.datetime, required=self.type == "dynamic")
        self.mediaPresentationDuration = self.attr(u"mediaPresentationDuration", parser=MPDParsers.duration)
        self.suggestedPresentationDelay = self.attr(u"suggestedPresentationDelay", parser=MPDParsers.duration)

        # parse children
        location = self.children(Location)
        self.location = location[0] if location else None
        if self.location:
            self.url = self.location.text
            urlp = list(urlparse(self.url))
            urlp[2], _ = urlp[2].rsplit("/", 1)
            self._base_url = urlunparse(urlp)

        self.baseURLs = self.children(BaseURL)
        self.periods = self.children(Period, minimum=1)
        self.programInformation = self.children(ProgramInformation)


class ProgramInformation(MPDNode):
    __tag__ = "ProgramInformation"


class BaseURL(MPDNode):
    __tag__ = "BaseURL"

    def __init__(self, node, root=None, parent=None, *args, **kwargs):
        super(BaseURL, self).__init__(node, root, parent, *args, **kwargs)
        self.url = self.node.text.strip()

    @property
    def is_absolute(self):
        return urlparse(self.url).scheme

    @staticmethod
    def join(url, other):
        # if the other URL is an absolute url, then return that
        if urlparse(other).scheme:
            return other
        elif url:
            parts = list(urlsplit(url))
            if not parts[2].endswith("/"):
                parts[2] += "/"
            url = urlunsplit(parts)
            return urljoin(url, other)
        else:
            return other


class Location(MPDNode):
    __tag__ = "Location"


class Period(MPDNode):
    __tag__ = u"Period"

    def __init__(self, node, root=None, parent=None, *args, **kwargs):
        super(Period, self).__init__(node, root, parent, *args, **kwargs)
        self.i = kwargs.get(u"i", 0)
        self.id = self.attr(u"id")
        self.bitstreamSwitching = self.attr(u"bitstreamSwitching", parser=MPDParsers.bool_str)
        self.duration = self.attr(u"duration", default=Duration(), parser=MPDParsers.duration)
        self.start = self.attr(u"start", default=Duration(), parser=MPDParsers.duration)

        if self.start is None and self.i == 0 and self.root.type == "static":
            self.start = 0

        # TODO: Early Access Periods

        self.baseURLs = self.children(BaseURL)
        self.segmentBase = self.only_child(SegmentBase)
        self.adaptionSets = self.children(AdaptationSet, minimum=1)
        self.segmentList = self.only_child(SegmentList)
        self.segmentTemplate = self.only_child(SegmentTemplate)
        self.sssetIdentifier = self.only_child(AssetIdentifier)
        self.eventStream = self.children(EventStream)
        self.subset = self.children(Subset)


class SegmentBase(MPDNode):
    __tag__ = "SegmentBase"


class AssetIdentifier(MPDNode):
    __tag__ = "AssetIdentifier"


class Subset(MPDNode):
    __tag__ = "Subset"


class EventStream(MPDNode):
    __tag__ = "EventStream"


class SegmentList(MPDNode):
    __tag__ = "SegmentList"


class AdaptationSet(MPDNode):
    __tag__ = u"AdaptationSet"

    def __init__(self, node, root=None, parent=None, *args, **kwargs):
        super(AdaptationSet, self).__init__(node, root, parent, *args, **kwargs)

        self.id = self.attr(u"id")
        self.group = self.attr(u"group")
        self.mimeType = self.attr(u"mimeType")
        self.lang = self.attr(u"lang")
        self.contentType = self.attr(u"contentType")
        self.par = self.attr(u"par")
        self.minBandwidth = self.attr(u"minBandwidth")
        self.maxBandwidth = self.attr(u"maxBandwidth")
        self.minWidth = self.attr(u"minWidth", parser=int)
        self.maxWidth = self.attr(u"maxWidth", parser=int)
        self.minHeight = self.attr(u"minHeight", parser=int)
        self.maxHeight = self.attr(u"maxHeight", parser=int)
        self.minFrameRate = self.attr(u"minFrameRate", parser=MPDParsers.frame_rate)
        self.maxFrameRate = self.attr(u"maxFrameRate", parser=MPDParsers.frame_rate)
        self.segmentAlignment = self.attr(u"segmentAlignment", default=False, parser=MPDParsers.bool_str)
        self.bitstreamSwitching = self.attr(u"bitstreamSwitching", parser=MPDParsers.bool_str)
        self.subsegmentAlignment = self.attr(u"subsegmentAlignment", default=False, parser=MPDParsers.bool_str)
        self.subsegmentStartsWithSAP = self.attr(u"subsegmentStartsWithSAP", default=0, parser=int)

        self.baseURLs = self.children(BaseURL)
        self.segmentTemplate = self.only_child(SegmentTemplate)
        self.representations = self.children(Representation, minimum=1)
        self.contentProtection = self.children(ContentProtection)


class SegmentTemplate(MPDNode):
    __tag__ = "SegmentTemplate"

    def __init__(self, node, root=None, parent=None, *args, **kwargs):
        super(SegmentTemplate, self).__init__(node, root, parent, *args, **kwargs)
        self.defaultSegmentTemplate = self.walk_back_get_attr('segmentTemplate')

        self.initialization = self.attr(u"initialization", parser=MPDParsers.segment_template)
        self.media = self.attr(u"media", parser=MPDParsers.segment_template)
        self.duration = self.attr(u"duration", parser=int, default=self.defaultSegmentTemplate.duration if self.defaultSegmentTemplate else None)
        self.timescale = self.attr(u"timescale", parser=int, default=self.defaultSegmentTemplate.timescale if self.defaultSegmentTemplate else 1)
        self.startNumber = self.attr(u"startNumber", parser=int, default=self.defaultSegmentTemplate.startNumber if self.defaultSegmentTemplate else 1)
        self.presentationTimeOffset = self.attr(u"presentationTimeOffset", parser=MPDParsers.timedelta(self.timescale))

        if self.duration:
            self.duration_seconds = self.duration / float(self.timescale)
        else:
            self.duration_seconds = None

        self.period = list(self.walk_back(Period))[0]

        # children
        self.segmentTimeline = self.only_child(SegmentTimeline)

    def segments(self, **kwargs):
        if kwargs.pop("init", True):
            init_url = self.format_initialization(**kwargs)
            if init_url:
                yield Segment(init_url, 0, True, False, 0)
        for media_url, available_at in self.format_media(**kwargs):
            yield Segment(media_url, self.duration_seconds, False, True, available_at)

    def make_url(self, url):
        """
        Join the URL with the base URL, unless it's an absolute URL
        :param url: maybe relative URL
        :return: joined URL
        """
        return BaseURL.join(self.base_url, url)

    def format_initialization(self, **kwargs):
        if self.initialization:
            return self.make_url(self.initialization(**kwargs))

    def segment_numbers(self):
        """
        yield the segment number and when it will be available
        There are two cases for segment number generation, static and dynamic.

        In the case of static stream, the segment number starts at the startNumber and counts
        up to the number of segments that are represented by the periods duration.

        In the case of dynamic streams, the segments should appear at the specified time
        in the simplest case the segment number is based on the time since the availabilityStartTime
        :return:
        """
        if self.root.type == u"static":
            available_iter = repeat(0)
            duration = self.period.duration.seconds or self.root.mediaPresentationDuration.seconds
            if duration:
                number_iter = range(self.startNumber, int(duration / self.duration_seconds) + 1)
            else:
                number_iter = count(self.startNumber)
        else:
            now = datetime.datetime.now(utc)
            if self.presentationTimeOffset:
                seconds_since_start = (
                (now - self.presentationTimeOffset) - self.root.availabilityStartTime).total_seconds()
                available_start_date = self.root.availabilityStartTime + self.presentationTimeOffset + datetime.timedelta(
                    seconds=seconds_since_start)
                available_start = int(datetime_to_seconds(available_start_date))
            else:
                seconds_since_start = (now - self.root.availabilityStartTime).total_seconds()
                available_start = int(datetime_to_seconds(now))

            # if there is no delay, use a delay of 3 seconds
            suggested_delay = self.root.suggestedPresentationDelay.total_seconds() if self.root.suggestedPresentationDelay else 3

            number_iter = count(self.startNumber + int((seconds_since_start - suggested_delay) / self.duration_seconds))
            available_iter = count(available_start - suggested_delay, step=self.duration_seconds)

        for number, available_at in izip(number_iter, available_iter):
            yield number, available_at

    def format_media(self, **kwargs):
        if self.segmentTimeline:
            t = 0
            for segment in self.segmentTimeline.segments:
                t = t or segment.t
                # check the start time from MPD
                if t > self.root.timelines[self.parent.id]:
                    yield self.make_url(self.media(Time=t, **kwargs)), 0
                    self.root.timelines[self.parent.id] = t
                t += segment.d
        else:
            for number, available_at in self.segment_numbers():
                yield self.make_url(self.media(Number=number, **kwargs)), available_at


class Representation(MPDNode):
    __tag__ = u"Representation"

    def __init__(self, node, root=None, parent=None, *args, **kwargs):
        super(Representation, self).__init__(node, root, parent, *args, **kwargs)
        self.id = self.attr(u"id", required=True)
        self.bandwidth = self.attr(u"bandwidth", parser=lambda b: float(b) / 1000.0, required=True)
        self.mimeType = self.attr(u"mimeType", required=True, inherited=True)

        self.codecs = self.attr(u"codecs")
        self.startWithSAP = self.attr(u"startWithSAP")

        # video
        self.width = self.attr(u"width", parser=int)
        self.height = self.attr(u"height", parser=int)
        self.frameRate = self.attr(u"frameRate", parser=MPDParsers.frame_rate)

        # audio
        self.audioSamplingRate = self.attr(u"audioSamplingRate", parser=int)
        self.numChannels = self.attr(u"numChannels", parser=int)

        # subtitle
        self.lang = self.attr(u"lang", inherited=True)

        self.baseURLs = self.children(BaseURL)
        self.subRepresentation = self.children(SubRepresentation)
        self.segmentBase = self.only_child(SegmentBase)
        self.segmentList = self.only_child(SegmentList)
        self.segmentTemplate = self.only_child(SegmentTemplate)

    def segments(self, **kwargs):
        """
        Segments are yielded when they are available

        Segments appear on a time line, for dynamic content they are only available at a certain time
        and sometimes for a limited time. For static content they are all available at the same time.

        :param kwargs: extra args to pass to the segment template
        :return: yields Segments
        """

        segmentBase = self.segmentBase or self.walk_back_get_attr("segmentBase")
        segmentList = self.segmentList or self.walk_back_get_attr("segmentList")
        segmentTemplate = self.segmentTemplate or self.walk_back_get_attr("segmentTemplate")

        if segmentTemplate:
            for segment in segmentTemplate.segments(RepresentationID=self.id,
                                                    Bandwidth=int(self.bandwidth * 1000),
                                                    **kwargs):
                if segment.init:
                    yield segment
                else:
                    sleep_until(segment.available_at)
                    yield segment
        else:
            yield Segment(self.base_url, 0, True, True, 0)


class SubRepresentation(MPDNode):
    __tag__ = "SubRepresentation"


class SegmentTimeline(MPDNode):
    __tag__ = "SegmentTimeline"

    def __init__(self, node, *args, **kwargs):
        super(SegmentTimeline, self).__init__(node, *args, **kwargs)

        self.segments = self.children(TimelineSegment)


class TimelineSegment(MPDNode):
    __tag__ = "S"

    def __init__(self, node, *args, **kwargs):
        super(TimelineSegment, self).__init__(node, *args, **kwargs)

        self.t = self.attr("t", parser=int)
        self.d = self.attr("d", parser=int)


class ContentProtection(MPDNode):
    __tag__ = "ContentProtection"

    def __init__(self, node, root=None, parent=None, *args, **kwargs):
        super(ContentProtection, self).__init__(node, root, parent, *args, **kwargs)

        self.schemeIdUri = self.attr(u"schemeIdUri")
        self.value = self.attr(u"value")
        self.default_KID = self.attr(u"default_KID")
