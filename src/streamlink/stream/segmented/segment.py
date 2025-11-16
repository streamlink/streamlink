from dataclasses import dataclass, field


@dataclass(kw_only=True)
class Segment:
    num: int
    init: bool = False
    discontinuity: bool = False
    uri: str = field(repr=False)
    duration: float
