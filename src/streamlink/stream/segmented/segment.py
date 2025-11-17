from dataclasses import dataclass, field
from urllib.parse import urlparse

from streamlink.utils.dataclass import FormattedDataclass


@dataclass(kw_only=True)
class Segment(metaclass=FormattedDataclass, extra=["fileext"]):
    num: int
    init: bool = False
    discontinuity: bool = False
    uri: str = field(repr=False)
    duration: float

    @property
    def fileext(self) -> str | None:
        path = urlparse(self.uri).path
        ext = path.split(".")[-1]
        if 4 >= len(ext) >= 2:
            return ext
        return None
