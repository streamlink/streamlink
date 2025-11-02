from dataclasses import dataclass


@dataclass(kw_only=True)
class Segment:
    uri: str
    num: int
    duration: float
