from dataclasses import dataclass, field

from streamlink.utils.dataclass import FormattedDataclass


@dataclass(kw_only=True)
class Segment(metaclass=FormattedDataclass):
    num: int
    init: bool = False
    discontinuity: bool = False
    uri: str = field(repr=False)
    duration: float
