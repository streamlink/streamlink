from dataclasses import dataclass


@dataclass(kw_only=True)
class Segment:
    num: int
    init: bool = False
    discontinuity: bool = False
    uri: str
    duration: float
