from __future__ import annotations

import copy
import logging
import math
import re
from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime, timedelta
from itertools import count, repeat
from typing import TYPE_CHECKING, Any, ClassVar, Literal, TypeVar, overload
from urllib.parse import urljoin, urlparse, urlunparse

from isodate import Duration, parse_datetime, parse_duration  # type: ignore[import]

# noinspection PyProtectedMember
from lxml.etree import _Attrib, _Element

from streamlink.stream.dash.segment import DASHSegment, TimelineSegment
from streamlink.utils.times import UTC, fromtimestamp, now


if TYPE_CHECKING:
    from typing_extensions import TypeAlias


log = logging.getLogger(__name__)

EPOCH_START = fromtimestamp(0)
ONE_SECOND = timedelta(seconds=1)


def _identity(x):
    return x


def datetime_to_seconds(dt):
    return (dt - EPOCH_START).total_seconds()


def count_dt(firstval: datetime | None = None, step: timedelta = ONE_SECOND) -> Iterator[datetime]:
    current = now() if firstval is None else firstval
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
    def type(mpdtype: Literal["static", "dynamic"]) -> Literal["static", "dynamic"]:
        if mpdtype not in ("static", "dynamic"):
            raise MPDParsingError("@type must be static or dynamic")
        return mpdtype

    @staticmethod
    def duration(anchor: datetime | None = None) -> Callable[[str], timedelta]:
        def duration_to_timedelta(duration: str) -> timedelta:
            parsed: timedelta | Duration = parse_duration(duration)
            if isinstance(parsed, Duration):
                return parsed.totimedelta(start=anchor or now())
            return parsed

        return duration_to_timedelta

    @staticmethod
    def datetime(dt: str) -> datetime:
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
            return timedelta(seconds=int(float(seconds) / float(timescale)))

        return _timedelta

    @staticmethod
    def range(range_spec: str) -> tuple[int, int | None]:
        r = range_spec.split("-")
        if len(r) != 2:
            raise MPDParsingError("Invalid byte-range-spec")

        start, end = int(r[0]), r[1] and int(r[1]) or None
        return start, end and ((end - start) + 1)


class MPDParsingError(Exception):
    pass


TMPDNode_co = TypeVar("TMPDNode_co", bound="MPDNode", covariant=True)
TAttrDefault = TypeVar("TAttrDefault", Any, None)
TAttrParseResult = TypeVar("TAttrParseResult")

TTimelineIdent: TypeAlias = "tuple[str | None, str | None, str]"


class MPDNode:
    __tag__: ClassVar[str]

    parent: MPDNode

    def __init__(self, node: _Element, root: MPD, parent: MPDNode, **kwargs) -> None:
        self.node = node
        self.root = root
        self.parent = parent
        self._base_url = kwargs.get("base_url")
        self.attributes: set[str] = set()
        if self.__tag__ and self.node.tag.lower() != self.__tag__.lower():
            raise MPDParsingError(f"Root tag did not match the expected tag: {self.__tag__}")

    @property
    def attrib(self) -> _Attrib:
        return self.node.attrib

    @property
    def text(self) -> str | None:
        return self.node.text

    def __str__(self):
        return f"<{self.__tag__} {' '.join(f'@{attr}={getattr(self, attr)}' for attr in self.attributes)}>"

    @overload
    def attr(  # type: ignore[misc]  # "Overloaded function signatures 1 and 2 overlap with incompatible return types"
        self,
        key: str,
        parser: None = None,
        default: None = None,
        required: bool = False,
        inherited: type[TMPDNode_co] | Sequence[type[TMPDNode_co]] | None = None,
    ) -> str | None:  # pragma: no cover
        pass

    @overload
    def attr(
        self,
        key: str,
        parser: None,
        default: TAttrDefault,
        required: bool = False,
        inherited: type[TMPDNode_co] | Sequence[type[TMPDNode_co]] | None = None,
    ) -> TAttrDefault:  # pragma: no cover
        pass

    @overload
    def attr(
        self,
        key: str,
        parser: Callable[[Any], TAttrParseResult],
        default: None = None,
        required: bool = False,
        inherited: type[TMPDNode_co] | Sequence[type[TMPDNode_co]] | None = None,
    ) -> TAttrParseResult | None:  # pragma: no cover
        pass

    @overload
    def attr(
        self,
        key: str,
        parser: Callable[[Any], TAttrParseResult],
        default: TAttrDefault,
        required: bool = False,
        inherited: type[TMPDNode_co] | Sequence[type[TMPDNode_co]] | None = None,
    ) -> TAttrParseResult | TAttrDefault:  # pragma: no cover
        pass

    def attr(self, key, parser=None, default=None, required=False, inherited=None):
        self.attributes.add(key)
        if key in self.attrib:
            value = self.attrib.get(key)
            if parser and callable(parser):
                return parser(value)
            else:
                return value
        elif inherited:
            value = self.walk_back_get_attr(key, inherited)
            if value is not None:
                return value

        if required:  # pragma: no cover
            raise MPDParsingError(f"Could not find required attribute {self.__tag__}@{key} ")

        return default

    def children(
        self,
        cls: type[TMPDNode_co],
        minimum: int = 0,
        maximum: int | None = None,
        **kwargs,
    ) -> list[TMPDNode_co]:
        children = self.node.findall(cls.__tag__)
        if len(children) < minimum or (maximum and len(children) > maximum):
            raise MPDParsingError(f"Expected to find {self.__tag__}/{cls.__tag__} required [{minimum}..{maximum or 'unbound'})")

        return [
            cls(child, root=self.root, parent=self, i=i, base_url=self.base_url, **kwargs)
            for i, child in enumerate(children)
        ]  # fmt: skip

    def only_child(
        self,
        cls: type[TMPDNode_co],
        minimum: int = 0,
        **kwargs,
    ) -> TMPDNode_co | None:
        children = self.children(cls, minimum=minimum, maximum=1, **kwargs)
        return children[0] if len(children) else None

    def walk_back(
        self,
        cls: type[TMPDNode_co] | Sequence[type[TMPDNode_co]] | None = None,
        mapper: Callable[[MPDNode], MPDNode | None] = _identity,
    ) -> Iterator[MPDNode]:
        node = self.parent
        while node:
            if cls is None or isinstance(node, cls):  # type: ignore[arg-type]
                n = mapper(node)  # type: ignore[arg-type]
                if n is not None:
                    yield n
            node = node.parent

    def walk_back_get_attr(
        self,
        attr: str,
        cls: type[TMPDNode_co] | Sequence[type[TMPDNode_co]] | None = None,
        mapper: Callable[[MPDNode], MPDNode | None] = _identity,
    ) -> Any | None:
        for ancestor in self.walk_back(cls, mapper):
            value = getattr(ancestor, attr, None)
            if value is not None:
                return value

    @property
    def base_url(self):
        base_url = self._base_url
        if hasattr(self, "baseURLs") and len(self.baseURLs):
            base_url = urljoin(base_url, self.baseURLs[0].url)
        return base_url


class MPD(MPDNode):
    """
    Represents the MPD as a whole

    Should validate the XML input and provide methods to get segment URLs for each Period, AdaptationSet and Representation.
    """

    __tag__ = "MPD"

    parent: None  # type: ignore[assignment]
    timelines: dict[TTimelineIdent, int]

    DEFAULT_MINBUFFERTIME = 3.0
    DEFAULT_LIVE_EDGE_SEGMENTS = 3

    def __init__(self, *args, url: str | None = None, **kwargs) -> None:
        # top level has no parent
        kwargs["root"] = self
        kwargs["parent"] = None
        super().__init__(*args, **kwargs)

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
        self.publishTime = self.attr(
            "publishTime",
            parser=MPDParsers.datetime,
            default=EPOCH_START,
        )
        self.availabilityStartTime = self.attr(
            "availabilityStartTime",
            parser=MPDParsers.datetime,
            default=EPOCH_START,
        )
        self.availabilityEndTime = self.attr(
            "availabilityEndTime",
            parser=MPDParsers.datetime,
        )
        self.minBufferTime: timedelta = self.attr(  # type: ignore[assignment]
            "minBufferTime",
            parser=MPDParsers.duration(self.publishTime),
            required=True,
        )
        self.minimumUpdatePeriod = self.attr(
            "minimumUpdatePeriod",
            parser=MPDParsers.duration(self.publishTime),
            default=timedelta(),
        )
        self.timeShiftBufferDepth = self.attr(
            "timeShiftBufferDepth",
            parser=MPDParsers.duration(self.publishTime),
        )
        self.mediaPresentationDuration = self.attr(
            "mediaPresentationDuration",
            parser=MPDParsers.duration(self.publishTime),
            default=timedelta(),
        )
        self.suggestedPresentationDelay = self.attr(
            "suggestedPresentationDelay",
            parser=MPDParsers.duration(self.publishTime),
            # if there is no delay, use a delay of 3 seconds, but respect the manifest's minBufferTime
            # TODO: add a customizable parameter for this
            default=timedelta(
                seconds=max(
                    self.DEFAULT_MINBUFFERTIME,
                    self.minBufferTime.total_seconds(),
                ),
            ),
        )

        # parse children
        location = self.children(Location)
        self.location = location[0] if location else None
        if self.location:
            self.url = self.location.text or ""
            urlp = list(urlparse(self.url))
            if urlp[2]:
                urlp[2], _ = urlp[2].rsplit("/", 1)
            self._base_url = urlunparse(urlp)

        self.baseURLs = self.children(BaseURL)
        self.periods = self.children(Period, minimum=1)
        self.programInformation = self.children(ProgramInformation)

    def get_representation(self, ident: TTimelineIdent) -> Representation | None:
        """
        Find the first Representation instance with a matching ident
        """
        for period in self.periods:
            for adaptationset in period.adaptationSets:
                for representation in adaptationset.representations:
                    if representation.ident == ident:
                        return representation


class ProgramInformation(MPDNode):
    __tag__ = "ProgramInformation"


class BaseURL(MPDNode):
    __tag__ = "BaseURL"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.url = (self.text or "").strip()


class Location(MPDNode):
    __tag__ = "Location"


class Period(MPDNode):
    __tag__ = "Period"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.i = kwargs.get("i", 0)
        self.id = self.attr("id")
        self.bitstreamSwitching = self.attr(
            "bitstreamSwitching",
            parser=MPDParsers.bool_str,
        )
        self.duration = self.attr(
            "duration",
            parser=MPDParsers.duration(self.root.publishTime),
            default=timedelta(),
        )
        self.start = self.attr(
            "start",
            parser=MPDParsers.duration(self.root.publishTime),
            default=timedelta(),
        )

        # anchor time for segment availability
        offset = self.start if self.root.type == "dynamic" else timedelta()
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


class AssetIdentifier(MPDNode):
    __tag__ = "AssetIdentifier"


class Subset(MPDNode):
    __tag__ = "Subset"


class EventStream(MPDNode):
    __tag__ = "EventStream"


class _RepresentationBaseType(MPDNode):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # mimeType must be set on the AdaptationSet or Representation
        self.mimeType: str = self.attr(  # type: ignore[assignment]
            "mimeType",
            required=type(self) is Representation,
            inherited=_RepresentationBaseType,
        )

        self.profiles = self.attr(
            "profiles",
            inherited=_RepresentationBaseType,
        )
        self.width = self.attr(
            "width",
            parser=int,
            inherited=_RepresentationBaseType,
        )
        self.height = self.attr(
            "height",
            parser=int,
            inherited=_RepresentationBaseType,
        )
        self.sar = self.attr(
            "sar",
            inherited=_RepresentationBaseType,
        )
        self.frameRate = self.attr(
            "frameRate",
            parser=MPDParsers.frame_rate,
            inherited=_RepresentationBaseType,
        )
        self.audioSamplingRate = self.attr(
            "audioSamplingRate",
            parser=int,
            inherited=_RepresentationBaseType,
        )
        self.codecs = self.attr(
            "codecs",
            inherited=_RepresentationBaseType,
        )
        self.scanType = self.attr(
            "scanType",
            inherited=_RepresentationBaseType,
        )

        self.contentProtections = self.children(ContentProtection)


class AdaptationSet(_RepresentationBaseType):
    __tag__ = "AdaptationSet"

    parent: Period

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.id = self.attr("id")
        self.group = self.attr("group")
        self.lang = self.attr("lang")
        self.contentType = self.attr("contentType")
        self.par = self.attr("par")
        self.minBandwidth = self.attr("minBandwidth", parser=int)
        self.maxBandwidth = self.attr("maxBandwidth", parser=int)
        self.minWidth = self.attr("minWidth", parser=int)
        self.maxWidth = self.attr("maxWidth", parser=int)
        self.minHeight = self.attr("minHeight", parser=int)
        self.maxHeight = self.attr("maxHeight", parser=int)
        self.minFrameRate = self.attr("minFrameRate", parser=MPDParsers.frame_rate)
        self.maxFrameRate = self.attr("maxFrameRate", parser=MPDParsers.frame_rate)
        self.segmentAlignment = self.attr(
            "segmentAlignment",
            parser=MPDParsers.bool_str,
            default=False,
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
        self.bitstreamSwitching = self.attr(
            "bitstreamSwitching",
            parser=MPDParsers.bool_str,
        )

        self.baseURLs = self.children(BaseURL)
        self.segmentBase = self.only_child(SegmentBase, period=self.parent)
        self.segmentList = self.only_child(SegmentList, period=self.parent)
        self.segmentTemplate = self.only_child(SegmentTemplate, period=self.parent)
        self.representations = self.children(Representation, minimum=1, period=self.parent)


class Representation(_RepresentationBaseType):
    __tag__ = "Representation"

    parent: AdaptationSet

    def __init__(self, *args, period: Period, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.period = period

        self.id: str = self.attr(  # type: ignore[assignment]
            "id",
            required=True,
        )
        self.bandwidth: float = self.attr(  # type: ignore[assignment]
            "bandwidth",
            parser=lambda b: float(b) / 1000.0,
            required=True,
        )

        self.ident = self.parent.parent.id, self.parent.id, self.id

        self.baseURLs = self.children(BaseURL)
        self.subRepresentations = self.children(SubRepresentation)
        self.segmentBase = self.only_child(SegmentBase, period=self.period)
        self.segmentList = self.only_child(SegmentList, period=self.period)
        self.segmentTemplate = self.only_child(SegmentTemplate, period=self.period)

    @property
    def lang(self):
        return self.parent.lang

    @property
    def bandwidth_rounded(self) -> float:
        return round(self.bandwidth, 1 - int(math.log10(self.bandwidth)))

    def segments(
        self,
        init: bool = True,
        timestamp: datetime | None = None,
        **kwargs,
    ) -> Iterator[DASHSegment]:
        """
        Segments are yielded when they are available

        Segments appear on a timeline, for dynamic content they are only available at a certain time
        and sometimes for a limited time. For static content they are all available at the same time.

        :param init: Yield the init segment and perform other initialization logic for dynamic manifests
        :param timestamp: Optional initial timestamp for syncing timelines of multiple substreams
        :param kwargs: extra args to pass to the segment template/list
        :return: yields Segments
        """

        # segmentBase = self.segmentBase or self.walk_back_get_attr("segmentBase")
        segmentList = self.segmentList or self.walk_back_get_attr("segmentList")
        segmentTemplate = self.segmentTemplate or self.walk_back_get_attr("segmentTemplate")

        if segmentTemplate:
            yield from segmentTemplate.segments(
                self.ident,
                self.base_url,
                init=init,
                timestamp=timestamp,
                RepresentationID=self.id,
                Bandwidth=int(self.bandwidth * 1000),
                **kwargs,
            )
        elif segmentList:
            yield from segmentList.segments(
                self.ident,
                init=init,
                **kwargs,
            )
        else:
            yield DASHSegment(
                uri=self.base_url,
                num=-1,
                duration=self.period.duration.total_seconds() or self.root.mediaPresentationDuration.total_seconds(),
                available_at=self.period.availabilityStartTime,
                init=True,
                content=True,
                byterange=None,
            )


class SubRepresentation(_RepresentationBaseType):
    __tag__ = "SubRepresentation"


class _SegmentBaseType(MPDNode):
    parent: Period | AdaptationSet | Representation

    _ancestors = (Period, AdaptationSet, Representation)

    def __init__(self, *args, period: "Period", **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.period = period

        self.timescale: int = self.attr(
            "timescale",
            parser=int,
            default=self._find_default("timescale", 1),
        )
        self.presentationTimeOffset: timedelta = self.attr(
            "presentationTimeOffset",
            parser=MPDParsers.timedelta(self.timescale),
            default=self._find_default("presentationTimeOffset", timedelta()),
        )
        self.availabilityTimeOffset: timedelta = self.attr(
            "availabilityTimeOffset",
            parser=MPDParsers.timedelta(self.timescale),
            default=self._find_default("availabilityTimeOffset", timedelta()),
        )

        self.initialization = self.only_child(Initialization) or self._find_default("initialization")

    def _find_default(self, attr: str, default: TAttrDefault = None) -> TAttrDefault | Any:
        """Find default values from nodes of the same type on ancestor nodes"""
        # the node attribute on each ancestor is named after its node tag, with the first character being lowercase
        nodeattr = f"{self.__tag__[0].lower()}{self.__tag__[1:]}"
        # start with the parent node, to avoid an unnecessary failed lookup on the current node
        value = self.parent.walk_back_get_attr(
            attr,
            self._ancestors,
            lambda node: getattr(node, nodeattr, None),
        )
        return default if value is None else value


class _MultipleSegmentBaseType(_SegmentBaseType):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.duration = self.attr(
            "duration",
            parser=int,
            default=self._find_default("duration"),
        )
        self.startNumber: int = self.attr(
            "startNumber",
            parser=int,
            default=self._find_default("startNumber", 1),
        )

        self.duration_seconds = self.duration / self.timescale if self.duration else 0.0

        self.segmentTimeline = self.only_child(SegmentTimeline) or self._find_default("segmentTimeline")


class SegmentBase(_SegmentBaseType):
    __tag__ = "SegmentBase"


class SegmentList(_MultipleSegmentBaseType):
    __tag__ = "SegmentList"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.segmentURLs = self.children(SegmentURL)

    # noinspection PyUnusedLocal
    def segments(
        self,
        ident: TTimelineIdent,
        init: bool = True,
        **kwargs,
    ) -> Iterator[DASHSegment]:
        if init and self.initialization:  # pragma: no branch
            yield DASHSegment(
                uri=self.make_url(self.initialization.source_url),
                num=-1,
                duration=0.0,
                available_at=self.period.availabilityStartTime,
                init=True,
                content=False,
                byterange=self.initialization.range,
            )
        for num, segment_url in self.segment_urls(ident, init):
            yield DASHSegment(
                uri=self.make_url(segment_url.media),
                num=num,
                duration=self.duration_seconds,
                available_at=self.period.availabilityStartTime,
                init=False,
                content=True,
                byterange=segment_url.media_range,
            )

    def segment_urls(self, ident: TTimelineIdent, init: bool) -> Iterator[tuple[int, SegmentURL]]:
        if init:
            if self.root.type == "static":
                # yield all segments in a static manifest
                start_number = self.startNumber
                segment_urls = self.segmentURLs
            else:
                # yield a specific number of segments from the live-edge of dynamic manifests
                start_number = self.calculate_optimal_start()
                segment_urls = self.segmentURLs[start_number - self.startNumber :]

        else:
            # skip segments with a lower number than the remembered segment number
            # and check if we've skipped any segments after reloading the manifest
            start_number = self.root.timelines[ident]
            offset = start_number - self.startNumber

            if offset >= 0:
                # no segments were skipped: yield a slice of the segments
                segment_urls = self.segmentURLs[offset:]
            else:
                # segments were skipped: yield all segments and set the correct segment number
                log.warning(
                    (
                        f"Skipped segments {start_number}-{self.startNumber - 1} after manifest reload. "
                        if offset < -1
                        else f"Skipped segment {start_number} after manifest reload. "
                    )
                    + "This is unsupported and will result in incoherent output data.",
                )
                start_number = self.startNumber
                segment_urls = self.segmentURLs

        # remember the next segment number
        self.root.timelines[ident] = start_number + len(segment_urls)

        yield from enumerate(segment_urls, start_number)

    def calculate_optimal_start(self) -> int:
        """Calculate the optimal segment number to start based on the suggestedPresentationDelay"""
        suggested_delay = self.root.suggestedPresentationDelay

        if self.duration_seconds == 0.0:
            log.info(f"Unknown segment duration. Falling back to an offset of {MPD.DEFAULT_LIVE_EDGE_SEGMENTS} segments.")
            offset = MPD.DEFAULT_LIVE_EDGE_SEGMENTS
        else:
            offset = max(0, math.ceil(suggested_delay.total_seconds() / self.duration_seconds))

        start = self.startNumber + len(self.segmentURLs) - offset
        log.debug(f"Calculated optimal offset is {offset} segments. First segment is {start}.")

        return start

    def make_url(self, url: str | None) -> str:
        return urljoin(self.base_url, url)


class SegmentTemplate(_MultipleSegmentBaseType):
    __tag__ = "SegmentTemplate"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.fmt_initialization = self.attr(
            "initialization",
            parser=MPDParsers.segment_template,
        )
        self.fmt_media = self.attr(
            "media",
            parser=MPDParsers.segment_template,
        )

    def segments(
        self,
        ident: TTimelineIdent,
        base_url: str,
        init: bool = True,
        timestamp: datetime | None = None,
        **kwargs,
    ) -> Iterator[DASHSegment]:
        if init:
            init_url = self.format_initialization(base_url, **kwargs)
            if init_url:  # pragma: no branch
                yield DASHSegment(
                    uri=init_url,
                    num=-1,
                    duration=0.0,
                    available_at=self.period.availabilityStartTime,
                    init=True,
                    content=False,
                    byterange=None,
                )
        for media_url, num, duration, available_at in self.format_media(ident, base_url, timestamp=timestamp, **kwargs):
            yield DASHSegment(
                uri=media_url,
                num=num,
                duration=duration,
                available_at=available_at,
                init=False,
                content=True,
                byterange=None,
            )

    @staticmethod
    def make_url(base_url: str, url: str) -> str:
        return urljoin(base_url, url)

    def segment_numbers(self, timestamp: datetime | None = None) -> Iterator[tuple[int, datetime]]:
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

        number_iter: Iterator[int] | Sequence[int]
        available_iter: Iterator[datetime]

        if self.root.type == "static":
            available_iter = repeat(self.period.availabilityStartTime)
            duration = self.period.duration.total_seconds() or self.root.mediaPresentationDuration.total_seconds()
            if duration:
                number_iter = range(self.startNumber, int(duration / self.duration_seconds) + 1)
            else:
                number_iter = count(self.startNumber)
        else:
            current_time = timestamp or now()
            since_start = current_time - self.period.availabilityStartTime - self.presentationTimeOffset

            suggested_delay = self.root.suggestedPresentationDelay
            buffer_time = self.root.minBufferTime

            # Segment number
            seconds_offset = (since_start - suggested_delay - buffer_time).total_seconds()
            number_offset = max(0, int(seconds_offset / self.duration_seconds))
            number_iter = count(self.startNumber + number_offset)

            # Segment availability time
            available_offset = timedelta(seconds=number_offset * self.duration_seconds)
            available_start = self.period.availabilityStartTime + available_offset
            available_iter = count_dt(
                available_start,
                timedelta(seconds=self.duration_seconds),
            )

            log.debug(f"Stream start: {self.period.availabilityStartTime}")
            log.debug(f"Current time: {current_time}")
            log.debug(f"Availability: {available_start}")
            log.debug(
                "; ".join([
                    f"presentationTimeOffset: {self.presentationTimeOffset}",
                    f"suggestedPresentationDelay: {self.root.suggestedPresentationDelay}",
                    f"minBufferTime: {self.root.minBufferTime}",
                ]),
            )
            log.debug(
                "; ".join([
                    f"segmentDuration: {self.duration_seconds}",
                    f"segmentStart: {self.startNumber}",
                    f"segmentOffset: {number_offset} ({seconds_offset}s)",
                ]),
            )

        yield from zip(number_iter, available_iter)

    def segment_timeline(self, ident: TTimelineIdent) -> Iterator[tuple[int, TimelineSegment, datetime]]:
        if not self.segmentTimeline:  # pragma: no cover
            raise MPDParsingError("Missing SegmentTimeline in SegmentTemplate")

        if self.root.type == "static":
            yield from zip(count(self.startNumber), self.segmentTimeline.segments, repeat(self.period.availabilityStartTime))
        else:
            time = self.root.timelines[ident]
            is_initial = time == -1

            threshold = self.root.publishTime - self.root.suggestedPresentationDelay

            # transform the timeline into a segment list
            timeline = []
            available_at = self.root.publishTime

            # the last segment in the timeline is the most recent one
            # so, work backwards and calculate when each of the segments was
            # available, based on the durations relative to the publish-time
            for number, segment in reversed(list(zip(count(self.startNumber), self.segmentTimeline.segments))):
                # stop once the suggestedPresentationDelay is reached on the first manifest parsing
                # or when a segment with a lower or equal time value was already returned from an earlier manifest
                if is_initial and available_at <= threshold or segment.t <= time:
                    break

                timeline.append((number, segment, available_at))
                available_at -= timedelta(seconds=segment.d / self.timescale)

            # return the segments in chronological order
            for number, segment, available_at in reversed(timeline):
                self.root.timelines[ident] = segment.t
                yield number, segment, available_at

    def format_initialization(self, base_url: str, **kwargs) -> str | None:
        if self.fmt_initialization is not None:  # pragma: no branch
            return self.make_url(base_url, self.fmt_initialization(**kwargs))

    def format_media(
        self,
        ident: TTimelineIdent,
        base_url: str,
        timestamp: datetime | None = None,
        **kwargs,
    ) -> Iterator[tuple[str, int, float, datetime]]:
        if self.fmt_media is None:  # pragma: no cover
            return

        if not self.segmentTimeline:
            log.debug(f"Generating segment numbers for {self.root.type} playlist: {ident!r}")
            duration = self.duration_seconds
            for number, available_at in self.segment_numbers(timestamp=timestamp):
                url = self.make_url(base_url, self.fmt_media(Number=number, **kwargs))
                yield url, number, duration, available_at
        else:
            log.debug(f"Generating segment timeline for {self.root.type} playlist: {ident!r}")
            for number, segment, available_at in self.segment_timeline(ident):
                url = self.make_url(base_url, self.fmt_media(Time=segment.t, Number=number, **kwargs))
                duration = segment.d / self.timescale
                yield url, number, duration, available_at


class SegmentTimeline(MPDNode):
    __tag__ = "SegmentTimeline"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.timescale = self.walk_back_get_attr("timescale")

        self.timeline_segments = self.children(_TimelineSegment)

    @property
    def segments(self) -> Iterator[TimelineSegment]:
        t = 0
        for tsegment in self.timeline_segments:
            if t == 0 and tsegment.t is not None:
                t = tsegment.t
            # check the start time from MPD
            for _ in range(tsegment.r + 1):
                yield TimelineSegment(t, tsegment.d)
                t += tsegment.d


class _TimelineSegment(MPDNode):
    __tag__ = "S"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.t = self.attr("t", parser=int)
        self.d: int = self.attr("d", parser=int, required=True)  # type: ignore[assignment]
        self.r = self.attr("r", parser=int, default=0)


class Initialization(MPDNode):
    __tag__ = "Initialization"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.source_url = self.attr("sourceURL")
        self.range = self.attr(
            "range",
            parser=MPDParsers.range,
        )


class SegmentURL(MPDNode):
    __tag__ = "SegmentURL"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.media = self.attr("media")
        self.media_range = self.attr(
            "mediaRange",
            parser=MPDParsers.range,
        )


class ContentProtection(MPDNode):
    __tag__ = "ContentProtection"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.schemeIdUri = self.attr("schemeIdUri")
        self.value = self.attr("value")
        self.default_KID = self.attr("default_KID")
