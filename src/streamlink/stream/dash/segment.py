from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from streamlink.stream.segmented.segment import Segment
from streamlink.utils.times import fromtimestamp, now


EPOCH_START = fromtimestamp(0)

SEGMENT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


@dataclass
class TimelineSegment:
    t: int
    d: int


@dataclass
class DASHSegment(Segment):
    available_at: datetime = EPOCH_START
    init: bool = False
    content: bool = True
    byterange: tuple[int, int | None] | None = None

    @property
    def name(self) -> str:
        if self.init and not self.content:
            return "initialization"
        if self.num > -1:
            return str(self.num)
        return Path(urlparse(self.uri).path).resolve().name

    @property
    def available_in(self) -> float:
        return max(0.0, (self.available_at - now()).total_seconds())

    @property
    def availability(self) -> str:
        return f"{self.available_at.strftime(SEGMENT_TIME_FORMAT)} / {now().strftime(SEGMENT_TIME_FORMAT)}"
