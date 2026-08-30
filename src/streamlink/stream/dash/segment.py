from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from streamlink.stream.segmented.segment import Segment
from streamlink.utils.times import fromtimestamp, now


if TYPE_CHECKING:
    from datetime import datetime


EPOCH_START = fromtimestamp(0)

SEGMENT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


@dataclass
class TimelineSegment:
    t: int
    d: int


@dataclass(kw_only=True)
class DASHSegment(Segment):
    available_at: datetime = EPOCH_START
    byterange: tuple[int, int | None] | None = None

    @property
    def name(self) -> str:
        if self.init:
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
