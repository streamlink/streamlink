from dataclasses import dataclass


@dataclass
class Segment:
    uri: str
    num: int
    duration: float
