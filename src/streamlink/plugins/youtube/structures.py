"""Shared data structures for the YouTube plugin.

Defines n-challenge I/O types, extractor result types, protocols,
and the module-level runtime context shared across extractors and JS solvers.
"""
import logging
from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import Protocol

from streamlink.options import Options
from streamlink.session.session import Streamlink

log = logging.getLogger(__name__)


class StreamPick(StrEnum):
    """Named ordering options for stream selection."""
    FIRST = auto()
    LAST = auto()
    POPULAR = auto()

    @classmethod
    def metavar(cls) -> str:
        return "|".join(v.value for v in cls) + "|N"


@dataclass(frozen=True)
class StreamSelection:
    """Represents a stream selection option from the /streams page.

    Can be ``first``, ``last``, ``popular``, or a 1-based position number.

    Args:
        value: A :class:`StreamPick` value, or a positive :class:`int` position.
    """
    value: StreamPick | int

    def __post_init__(self):
        try:
            if isinstance(self.value, str) and self.value.isdigit():
                object.__setattr__(self, "value", int(self.value))
            elif isinstance(self.value, str):
                object.__setattr__(self, "value", StreamPick(self.value))
            if isinstance(self.value, int) and self.value < 1:
                raise ValueError()
        except ValueError:
            log.warning("Invalid stream selection option %r, defaulting to %r", self.value, StreamPick.POPULAR.value)
            object.__setattr__(self, "value", StreamPick.POPULAR)


@dataclass(frozen=True)
class NChallengeInput:
    """Input data for a YouTube n-parameter challenge.

    Args:
        player_url: URL of the YouTube player JS bundle containing the solver.
        token: The raw ``n`` query parameter value to be transformed.
    """
    player_url: str
    token: str


@dataclass(frozen=True)
class NChallengeOutput:
    """Result of a solved n-parameter challenge.

    Args:
        results: Mapping of original ``n`` token -> solved token.
    """
    results: dict[str, str] = field(default_factory=dict)


class ExtractorType(StrEnum):
    """Discriminator for the YouTube Extractors."""
    VIDEO = auto()  # youtube.com/watch?v=<id>
    LIVE = auto()  # youtube.com/@handle/live, /channel/<id>/live, etc.
    STREAMS = auto()  # youtube.com/@handle/streams, /channel/<id>/streams, etc.


@dataclass(frozen=True)
class NextExtractor:
    """Redirect instruction returned when one extractor defers to another.

    Args:
        extractor: Target extractor type to invoke next.
        url: Resolved URL to pass to that extractor.
    """
    extractor: ExtractorType
    url: str


@dataclass(frozen=True)
class ExtractorResult:
    """Return value from any extractor.

    Exactly one field should be set per result:

    Args:
        next: Populated when the extractor delegates to another extractor.
        hls:  Populated when the extractor has resolved final HLS manifest URLs.
    """
    next: NextExtractor | None = None
    hls: list[str] | None = None


class Extractor(Protocol):
    """Structural interface that every YouTube extractor must implement."""

    valid_url_re: str
    """Regex pattern used to decide whether this extractor owns a given URL."""

    extractor_type: ExtractorType
    """Enum value that identifies this extractor."""

    def extract(self, url: str) -> ExtractorResult:
        """Run extraction for *url* and return a result or a redirect.

        Args:
            url: The URL to extract streams from.

        Returns:
            An :class:`ExtractorResult` with either ``next`` or ``hls`` set.
        """
        ...


class JsSolver(Protocol):
    """Structural interface for a JS runtime that evaluates YouTube JS challenges."""

    def solve(self, challenge: NChallengeInput) -> NChallengeOutput | None:
        """Solve a single n-parameter challenge.

        Args:
            challenge: Input containing the player URL and raw ``n`` token.

        Returns:
            :class:`NChallengeOutput` on success, ``None`` if unsolvable.
        """
        ...


@dataclass
class Context:
    """Shared runtime state injected into extractors and solvers.

    Args:
        session: Active :class:`~streamlink.session.Streamlink` session.
        deno:    JS solver instance (e.g. Deno-backed) for n-challenges.
    """
    session: Streamlink = None
    options: Options = None
    deno: JsSolver = None


# Module-level singleton — populated by the plugin entry point before
# any extractor or solver is invoked.
ctx = Context()
