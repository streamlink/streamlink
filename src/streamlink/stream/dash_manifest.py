import copy
import dataclasses
import datetime
import logging
import math
import re
from collections import defaultdict
from contextlib import contextmanager
from itertools import count, repeat
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from urllib.parse import urljoin, urlparse, urlsplit, urlunparse, urlunsplit

from isodate import Duration, parse_datetime, parse_duration  # type: ignore[import]

# noinspection PyProtectedMember
from lxml.etree import _Attrib, _Element


if TYPE_CHECKING:  # pragma: no cover
    from typing_extensions import Literal


log = logging.getLogger(__name__)

UTC = datetime.timezone.utc
EPOCH_START = datetime.datetime(1970, 1, 1, tzinfo=UTC)
ONE_SECOND = datetime.timedelta(seconds=1)


@dataclasses.dataclass
class Segment:
    url: str
    duration: float
    init: bool = False
    content: bool = True
    available_at: datetime.datetime = EPOCH_START
    byterange: Optional[Tuple[int, Optional[int]]] = None


@dataclasses.dataclass
class TimelineSegment:
    t: int
    d: int


def _identity(x):
    return x


def datetime_to_seconds(dt):
    return (dt - EPOCH_START).total_seconds()


def count_dt(
    firstval: Optional[datetime.datetime] = None,
    step: datetime.timedelta = ONE_SECOND,
) -> Iterator[datetime.datetime]:
    current = datetime.datetime.now(tz=UTC) if firstval is None else firstval
    while True:
        yield current
        current += step


@contextmanager
def freeze_timeline(mpd):
    timelines = copy.copy(mpd.timelines)
    yield
    mpd.timelines = timelines


_re_segment_template = re.compile(r"(.*?)\$(\w+)(?:%([\w.]+))?\$")


class MPDParsers:
    @staticmethod
    def bool_str(v: str) -> bool:
        return v.lower() == "true"

    @staticmethod
    def type(mpdtype: "Literal['static', 'dynamic']") -> "Literal['static', 'dynamic']":
        if mpdtype not in ("static", "dynamic"):
            raise MPDParsingError("@type must be static or dynamic")
        return mpdtype

    @staticmethod
    def duration(duration: str) -> Union[datetime.timedelta, Duration]:
        return parse_duration(duration)

    @staticmethod
    def datetime(dt: str) -> datetime.datetime:
        return parse_datetime(dt).replace(tzinfo=UTC)

    @staticmethod
    def segment_template(url_template: str) -> Callable[..., str]:
        end = 0
        res = ""
        for m in _re_segment_template.finditer(url_template):
            _, end = m.span()
            res += f"{m[1]}{{{m[2]}{f':{m[3]}' if m[3] else ''}}}"

        return f"{res}{url_template[end:]}".format

    @staticmethod
    def frame_rate(frame_rate: str) -> float:
        if "/" not in frame_rate:
            return float(frame_rate)

        a, b = frame_rate.split("/")
        return float(a) / float(b)

    @staticmethod
    def timedelta(timescale: float = 1):
        def _timedelta(seconds):
            return datetime.timedelta(seconds=int(float(seconds) / float(timescale)))

        return _timedelta

    @staticmethod
    def range(range_spec: str) -> Tuple[int, Optional[int]]:
        r = range_spec.split("-")
        if len(r) != 2:
            raise MPDParsingError("Invalid byte-range-spec")

        start, end = int(r[0]), r[1] and int(r[1]) or None
        return start, end and ((end - start) + 1)


class MPDParsingError(Exception):
    pass


TMPDNode = TypeVar("TMPDNode", bound="MPDNode", covariant=True)
TAttrDefault = TypeVar("TAttrDefault", Any, None)
TAttrParseResult = TypeVar("TAttrParseResult")

TTimelineIdent = Tuple[Optional[str], Optional[str], str]


class MPDNode:
    __tag__: ClassVar[str]

    parent: "MPDNode"

    def __init__(
        self,
        node: _Element,
        root: "MPD",
        parent: "MPDNode",
        *args,
        **kwargs,
    ):
        self.node = node
        self.root = root
        self.parent = parent
        self._base_url = kwargs.get("base_url")
        self.attributes: Set[str] = set()
        if self.__tag__ and self.node.tag.lower() != self.__tag__.lower():
            raise MPDParsingError(f"Root tag did not match the expected tag: {self.__tag__}")

    @property
    def attrib(self) -> _Attrib:
        return self.node.attrib

    @property
    def text(self) -> Optional[str]:
        return self.node.text

    def __str__(self):
        return f"<{self.__tag__} {' '.join(f'@{attr}={getattr(self, attr)}' for attr in self.attributes)}>"

    def attr(
        self,
        key: str,
        default: TAttrDefault = None,
        parser: Optional[Callable[[Any], TAttrParseResult]] = None,
        required: bool = False,
        inherited: bool = False,
    ) -> Union[TAttrParseResult, TAttrDefault, Any]:
        self.attributes.add(key)
        if key in self.attrib:
            value: Any = self.attrib.get(key)
            if parser and callable(parser):
                return parser(value)
            else:
                return value
        elif inherited:
            if self.parent and hasattr(self.parent, key) and getattr(self.parent, key):
                return getattr(self.parent, key)

        if required:
            raise MPDParsingError(f"Could not find required attribute {self.__tag__}@{key} ")

        return default

    def children(
        self,
        cls: Type[TMPDNode],
        minimum: int = 0,
        maximum: Optional[int] = None,
        **kwargs,
    ) -> List[TMPDNode]:
        children = self.node.findall(cls.__tag__)
        if len(children) < minimum or (maximum and len(children) > maximum):
            raise MPDParsingError(f"Expected to find {self.__tag__}/{cls.__tag__} required [{minimum}..{maximum or 'unbound'})")

        return [
            cls(child, root=self.root, parent=self, i=i, base_url=self.base_url, **kwargs)
            for i, child in enumerate(children)
        ]

    def only_child(
        self,
        cls: Type[TMPDNode],
        minimum: int = 0,
        **kwargs,
    ) -> Optional[TMPDNode]:
        children = self.children(cls, minimum=minimum, maximum=1, **kwargs)
        return children[0] if len(children) else None

    def walk_back(
        self,
        cls: Optional[Type[TMPDNode]] = None,
        f: Callable[["MPDNode"], "MPDNode"] = _identity,
    ) -> Iterator[Union[TMPDNode, "MPDNode"]]:
        node = self.parent
        while node:
            if cls is None or cls.__tag__ == node.__tag__:
                yield f(node)
            node = node.parent

    def walk_back_get_attr(self, attr: str) -> Optional[Any]:
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

    Should validate the XML input and provide methods to get segment URLs for each Period, AdaptationSet and Representation.
    """

    __tag__ = "MPD"

    parent: None  # type: ignore[assignment]
    timelines: Dict[TTimelineIdent, int]

    def __init__(self, node, url=None, *args, **kwargs):
        # top level has no parent
        kwargs.pop("root", None)
        kwargs.pop("parent", None)
        # noinspection PyTypeChecker
        super().__init__(node, root=self, parent=None, *args, **kwargs)

        # parser attributes
        self.url = url
        self.timelines = defaultdict(lambda: -1)
        self.timelines.update(kwargs.pop("timelines", {}))

        self.id = self.attr("id")
        self.profiles = self.attr(
            "profiles",
            required=True,
        )
        self.type = self.attr(
            "type",
            parser=MPDParsers.type,
            default="static",
        )
        self.minimumUpdatePeriod = self.attr(
            "minimumUpdatePeriod",
            parser=MPDParsers.duration,
            default=datetime.timedelta(),
        )
        self.minBufferTime = self.attr(
            "minBufferTime",
            parser=MPDParsers.duration,
            required=True,
        )
        self.timeShiftBufferDepth = self.attr(
            "timeShiftBufferDepth",
            parser=MPDParsers.duration,
        )
        self.availabilityStartTime = self.attr(
            "availabilityStartTime",
            parser=MPDParsers.datetime,
            default=EPOCH_START,
            required=self.type == "dynamic",
        )
        self.publishTime = self.attr(
            "publishTime",
            parser=MPDParsers.datetime,
            required=self.type == "dynamic",
        )
        self.availabilityEndTime = self.attr(
            "availabilityEndTime",
            parser=MPDParsers.datetime,
        )
        self.mediaPresentationDuration = self.attr(
            "mediaPresentationDuration",
            parser=MPDParsers.duration,
        )
        self.suggestedPresentationDelay = self.attr(
            "suggestedPresentationDelay",
            parser=MPDParsers.duration,
            # if there is no delay, use a delay of 3 seconds
            # TODO: add a customizable parameter for this
            default=datetime.timedelta(seconds=3),
        )

        # parse children
        location = self.children(Location)
        self.location = location[0] if location else None
        if self.location:
            self.url = self.location.text
            urlp = list(urlparse(self.url))
            if urlp[2]:
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
        super().__init__(node, root, parent, *args, **kwargs)

        self.url = self.text.strip()

    @property
    def is_absolute(self) -> bool:
        return bool(urlparse(self.url).scheme)

    @staticmethod
    def join(url: str, other: str) -> str:
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
    __tag__ = "Period"

    def __init__(self, node, root=None, parent=None, *args, **kwargs):
        super().__init__(node, root, parent, *args, **kwargs)

        self.i = kwargs.get("i", 0)
        self.id = self.attr("id")
        self.bitstreamSwitching = self.attr(
            "bitstreamSwitching",
            parser=MPDParsers.bool_str,
        )
        self.duration = self.attr(
            "duration",
            parser=MPDParsers.duration,
            default=datetime.timedelta(),
        )
        self.start = self.attr(
            "start",
            parser=MPDParsers.duration,
            default=datetime.timedelta(),
        )

        # anchor time for segment availability
        offset = self.start if self.root.type == "dynamic" else datetime.timedelta()
        self.availabilityStartTime = self.root.availabilityStartTime + offset

        # TODO: Early Access Periods

        self.baseURLs = self.children(BaseURL)
        self.segmentBase = self.only_child(SegmentBase, period=self)
        self.segmentList = self.only_child(SegmentList, period=self)
        self.segmentTemplate = self.only_child(SegmentTemplate, period=self)
        self.adaptationSets = self.children(AdaptationSet, minimum=1)
        self.assetIdentifier = self.only_child(AssetIdentifier)
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


class Initialization(MPDNode):
    __tag__ = "Initialization"

    def __init__(self, node, root=None, parent=None, *args, **kwargs):
        super().__init__(node, root, parent, *args, **kwargs)

        self.source_url = self.attr("sourceURL")
        self.range = self.attr(
            "range",
            parser=MPDParsers.range,
        )


class SegmentURL(MPDNode):
    __tag__ = "SegmentURL"

    def __init__(self, node, root=None, parent=None, *args, **kwargs):
        super().__init__(node, root, parent, *args, **kwargs)

        self.media = self.attr("media")
        self.media_range = self.attr(
            "mediaRange",
            parser=MPDParsers.range,
        )


class SegmentList(MPDNode):
    __tag__ = "SegmentList"

    period: "Period"

    def __init__(self, node, root=None, parent=None, period=None, *args, **kwargs):
        super().__init__(node, root, parent, *args, **kwargs)

        self.period = period

        self.presentation_time_offset = self.attr("presentationTimeOffset")
        self.timescale = self.attr(
            "timescale",
            parser=int,
        )
        self.duration = self.attr(
            "duration",
            parser=int,
        )
        self.start_number = self.attr(
            "startNumber",
            parser=int,
            default=1,
        )

        if self.duration:
            self.duration_seconds = self.duration / float(self.timescale)
        else:
            self.duration_seconds = None

        self.initialization = self.only_child(Initialization)
        self.segment_urls = self.children(SegmentURL, minimum=1)

    @property
    def segments(self) -> Iterator[Segment]:
        if self.initialization:  # pragma: no branch
            yield Segment(
                url=self.make_url(self.initialization.source_url),
                duration=0,
                init=True,
                content=False,
                available_at=self.period.availabilityStartTime,
                byterange=self.initialization.range,
            )
        for n, segment_url in enumerate(self.segment_urls, self.start_number):
            yield Segment(
                url=self.make_url(segment_url.media),
                duration=self.duration_seconds,
                available_at=self.period.availabilityStartTime,
                byterange=segment_url.media_range,
            )

    def make_url(self, url: str) -> str:
        return BaseURL.join(self.base_url, url)


class AdaptationSet(MPDNode):
    __tag__ = "AdaptationSet"

    parent: "Period"

    def __init__(self, node, root=None, parent=None, *args, **kwargs):
        super().__init__(node, root, parent, *args, **kwargs)

        self.id = self.attr("id")
        self.group = self.attr("group")
        self.mimeType = self.attr("mimeType")
        self.lang = self.attr("lang")
        self.contentType = self.attr("contentType")
        self.par = self.attr("par")
        self.minBandwidth = self.attr("minBandwidth")
        self.maxBandwidth = self.attr("maxBandwidth")
        self.minWidth = self.attr(
            "minWidth",
            parser=int,
        )
        self.maxWidth = self.attr(
            "maxWidth",
            parser=int,
        )
        self.minHeight = self.attr(
            "minHeight",
            parser=int,
        )
        self.maxHeight = self.attr(
            "maxHeight",
            parser=int,
        )
        self.minFrameRate = self.attr(
            "minFrameRate",
            parser=MPDParsers.frame_rate,
        )
        self.maxFrameRate = self.attr(
            "maxFrameRate",
            parser=MPDParsers.frame_rate,
        )
        self.segmentAlignment = self.attr(
            "segmentAlignment",
            parser=MPDParsers.bool_str,
            default=False,
        )
        self.bitstreamSwitching = self.attr(
            "bitstreamSwitching",
            parser=MPDParsers.bool_str,
        )
        self.subsegmentAlignment = self.attr(
            "subsegmentAlignment",
            parser=MPDParsers.bool_str,
            default=False,
        )
        self.subsegmentStartsWithSAP = self.attr(
            "subsegmentStartsWithSAP",
            parser=int,
            default=0,
        )

        self.baseURLs = self.children(BaseURL)
        self.segmentTemplate = self.only_child(SegmentTemplate, period=self.parent)
        self.representations = self.children(Representation, minimum=1, period=self.parent)
        self.contentProtection = self.children(ContentProtection)


class SegmentTemplate(MPDNode):
    __tag__ = "SegmentTemplate"

    parent: Union["Period", "AdaptationSet", "Representation"]
    period: "Period"

    def __init__(self, node, root=None, parent=None, period=None, *args, **kwargs):
        super().__init__(node, root, parent, *args, **kwargs)

        self.period = period

        self.defaultSegmentTemplate = self.walk_back_get_attr("segmentTemplate")

        self.initialization = self.attr(
            "initialization",
            parser=MPDParsers.segment_template,
        )
        self.media = self.attr(
            "media",
            parser=MPDParsers.segment_template,
        )
        self.duration = self.attr(
            "duration",
            parser=int,
            default=self.defaultSegmentTemplate.duration if self.defaultSegmentTemplate else None,
        )
        self.timescale = self.attr(
            "timescale",
            parser=int,
            default=self.defaultSegmentTemplate.timescale if self.defaultSegmentTemplate else 1,
        )
        self.startNumber = self.attr(
            "startNumber",
            parser=int,
            default=self.defaultSegmentTemplate.startNumber if self.defaultSegmentTemplate else 1,
        )
        self.presentationTimeOffset = self.attr(
            "presentationTimeOffset",
            parser=MPDParsers.timedelta(self.timescale),
            default=datetime.timedelta(),
        )

        self.duration_seconds = self.duration / self.timescale if self.duration and self.timescale else None

        # children
        self.segmentTimeline = self.only_child(SegmentTimeline)

    def segments(self, ident: TTimelineIdent, base_url: str, **kwargs) -> Iterator[Segment]:
        if kwargs.pop("init", True):  # pragma: no branch
            init_url = self.format_initialization(base_url, **kwargs)
            if init_url:  # pragma: no branch
                yield Segment(
                    url=init_url,
                    duration=0,
                    init=True,
                    content=False,
                    available_at=self.period.availabilityStartTime,
                )
        for media_url, available_at in self.format_media(ident, base_url, **kwargs):
            yield Segment(
                url=media_url,
                duration=self.duration_seconds,
                init=False,
                content=True,
                available_at=available_at,
            )

    @staticmethod
    def make_url(base_url: str, url: str) -> str:
        return BaseURL.join(base_url, url)

    def format_initialization(self, base_url: str, **kwargs) -> Optional[str]:
        if self.initialization:
            return self.make_url(base_url, self.initialization(**kwargs))

    def segment_numbers(self) -> Iterator[Tuple[int, datetime.datetime]]:
        """
        yield the segment number and when it will be available.

        There are two cases for segment number generation, "static" and "dynamic":

        In the case of static streams, the segment number starts at the startNumber and counts
        up to the number of segments that are represented by the periods-duration.

        In the case of dynamic streams, the segments should appear at the specified time.
        In the simplest case, the segment number is based on the time since the availabilityStartTime.
        """

        if not self.duration_seconds:  # pragma: no cover
            raise MPDParsingError("Unknown segment durations: missing duration/timescale attributes on SegmentTemplate")

        number_iter: Union[Iterator[int], Sequence[int]]
        available_iter: Iterator[datetime.datetime]

        if self.root.type == "static":
            available_iter = repeat(self.period.availabilityStartTime)
            duration = self.period.duration.seconds or self.root.mediaPresentationDuration.seconds
            if duration:
                number_iter = range(self.startNumber, int(duration / self.duration_seconds) + 1)
            else:
                number_iter = count(self.startNumber)
        else:
            now = datetime.datetime.now(UTC)
            since_start = now - self.period.availabilityStartTime - self.presentationTimeOffset

            suggested_delay = self.root.suggestedPresentationDelay
            buffer_time = self.root.minBufferTime

            # Segment number
            # To reduce unnecessary delay, start with the next/upcoming segment: +1
            seconds_offset = (since_start - suggested_delay - buffer_time).total_seconds()
            number_offset = max(0, int(seconds_offset / self.duration_seconds) + 1)
            number_iter = count(self.startNumber + number_offset)

            # Segment availability time
            # The availability time marks the segment's beginning: -1
            available_offset = datetime.timedelta(seconds=max(0, number_offset - 1) * self.duration_seconds)
            available_start = self.period.availabilityStartTime + available_offset
            available_iter = count_dt(
                available_start,
                datetime.timedelta(seconds=self.duration_seconds),
            )

            log.debug(f"Stream start: {self.period.availabilityStartTime}")
            log.debug(f"Current time: {now}")
            log.debug(f"Availability: {available_start}")
            log.debug("; ".join([
                f"presentationTimeOffset: {self.presentationTimeOffset}",
                f"suggestedPresentationDelay: {self.root.suggestedPresentationDelay}",
                f"minBufferTime: {self.root.minBufferTime}",
            ]))
            log.debug("; ".join([
                f"segmentDuration: {self.duration_seconds}",
                f"segmentStart: {self.startNumber}",
                f"segmentOffset: {number_offset} ({seconds_offset}s)",
            ]))

        yield from zip(number_iter, available_iter)

    def format_media(self, ident: TTimelineIdent, base_url: str, **kwargs) -> Iterator[Tuple[str, datetime.datetime]]:
        if not self.segmentTimeline:
            log.debug(f"Generating segment numbers for {self.root.type} playlist: {ident!r}")
            for number, available_at in self.segment_numbers():
                url = self.make_url(base_url, self.media(Number=number, **kwargs))
                yield url, available_at
            return

        log.debug(f"Generating segment timeline for {self.root.type} playlist: {ident!r}")

        if self.root.type == "static":
            available_at = self.period.availabilityStartTime
            for segment, n in zip(self.segmentTimeline.segments, count(self.startNumber)):
                url = self.make_url(base_url, self.media(Time=segment.t, Number=n, **kwargs))
                yield url, available_at
            return

        # Convert potential `isodate.Duration` instance to `datetime.timedelta` (relative to now)
        now = datetime.datetime.now(UTC)
        suggested_delay: datetime.timedelta = now + self.root.suggestedPresentationDelay - now

        publish_time = self.root.publishTime or EPOCH_START

        # transform the timeline into a segment list
        timeline = []
        available_at = publish_time
        for segment, n in reversed(list(zip(self.segmentTimeline.segments, count(self.startNumber)))):
            # the last segment in the timeline is the most recent one
            # so, work backwards and calculate when each of the segments was
            # available, based on the durations relative to the publish-time
            url = self.make_url(base_url, self.media(Time=segment.t, Number=n, **kwargs))
            duration = datetime.timedelta(seconds=segment.d / self.timescale)

            # once the suggested_delay is reached, stop
            if self.root.timelines[ident] == -1 and publish_time - available_at >= suggested_delay:
                break

            timeline.append((url, available_at, segment.t))

            available_at -= duration  # walk backwards in time

        # return the segments in chronological order
        for url, available_at, t in reversed(timeline):
            if t > self.root.timelines[ident]:
                self.root.timelines[ident] = t
                yield url, available_at


class Representation(MPDNode):
    __tag__ = "Representation"

    parent: "AdaptationSet"
    period: "Period"

    def __init__(self, node, root=None, parent=None, period=None, *args, **kwargs):
        super().__init__(node, root, parent, *args, **kwargs)

        self.period = period

        self.id = self.attr(
            "id",
            required=True,
        )
        self.bandwidth = self.attr(
            "bandwidth",
            parser=lambda b: float(b) / 1000.0,
            required=True,
        )
        self.mimeType = self.attr(
            "mimeType",
            required=True,
            inherited=True,
        )

        self.codecs = self.attr("codecs")
        self.startWithSAP = self.attr("startWithSAP")

        # video
        self.width = self.attr(
            "width",
            parser=int,
        )
        self.height = self.attr(
            "height",
            parser=int,
        )
        self.frameRate = self.attr(
            "frameRate",
            parser=MPDParsers.frame_rate,
        )

        # audio
        self.audioSamplingRate = self.attr(
            "audioSamplingRate",
            parser=int,
        )
        self.numChannels = self.attr(
            "numChannels",
            parser=int,
        )

        # subtitle
        self.lang = self.attr(
            "lang",
            inherited=True,
        )

        self.ident = self.parent.parent.id, self.parent.id, self.id

        self.baseURLs = self.children(BaseURL)
        self.subRepresentation = self.children(SubRepresentation)
        self.segmentBase = self.only_child(SegmentBase, period=self.period)
        self.segmentList = self.children(SegmentList, period=self.period)
        self.segmentTemplate = self.only_child(SegmentTemplate, period=self.period)
        self.contentProtection = self.children(ContentProtection)

    @property
    def bandwidth_rounded(self) -> float:
        return round(self.bandwidth, 1 - int(math.log10(self.bandwidth)))

    def segments(self, **kwargs) -> Iterator[Segment]:
        """
        Segments are yielded when they are available

        Segments appear on a timeline, for dynamic content they are only available at a certain time
        and sometimes for a limited time. For static content they are all available at the same time.

        :param kwargs: extra args to pass to the segment template
        :return: yields Segments
        """

        # segmentBase = self.segmentBase or self.walk_back_get_attr("segmentBase")
        segmentLists = self.segmentList or self.walk_back_get_attr("segmentList")
        segmentTemplate = self.segmentTemplate or self.walk_back_get_attr("segmentTemplate")

        if segmentTemplate:
            yield from segmentTemplate.segments(
                self.ident,
                self.base_url,
                RepresentationID=self.id,
                Bandwidth=int(self.bandwidth * 1000),
                **kwargs,
            )
        elif segmentLists:
            for segmentList in segmentLists:
                yield from segmentList.segments
        else:
            yield Segment(
                url=self.base_url,
                duration=0,
                init=True,
                content=True,
                available_at=self.period.availabilityStartTime,
            )


class SubRepresentation(MPDNode):
    __tag__ = "SubRepresentation"


class SegmentTimeline(MPDNode):
    __tag__ = "SegmentTimeline"

    def __init__(self, node, root=None, parent=None, *args, **kwargs):
        super().__init__(node, root, parent, *args, **kwargs)

        self.timescale = self.walk_back_get_attr("timescale")

        self.timeline_segments = self.children(_TimelineSegment)

    @property
    def segments(self) -> Iterator[TimelineSegment]:
        t = 0
        for tsegment in self.timeline_segments:
            if t == 0 and tsegment.t is not None:
                t = tsegment.t
            # check the start time from MPD
            for repeated_i in range(tsegment.r + 1):
                yield TimelineSegment(t, tsegment.d)
                t += tsegment.d


class _TimelineSegment(MPDNode):
    __tag__ = "S"

    def __init__(self, node, root=None, parent=None, *args, **kwargs):
        super().__init__(node, root, parent, *args, **kwargs)

        self.t = self.attr("t", parser=int)
        self.d = self.attr("d", parser=int)
        self.r = self.attr("r", parser=int, default=0)


class ContentProtection(MPDNode):
    __tag__ = "ContentProtection"

    def __init__(self, node, root=None, parent=None, *args, **kwargs):
        super().__init__(node, root, parent, *args, **kwargs)

        self.schemeIdUri = self.attr("schemeIdUri")
        self.value = self.attr("value")
        self.default_KID = self.attr("default_KID")
