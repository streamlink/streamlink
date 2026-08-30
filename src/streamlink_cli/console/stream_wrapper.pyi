from io import TextIOWrapper

from typing_extensions import Self

# Fake TextIOWrapper inheritance
class StreamWrapper(TextIOWrapper):
    _stream: TextIOWrapper
    _target: tuple[object, str] | None

    def __init__(self, stream: TextIOWrapper) -> None: ...
    @classmethod
    def wrap(cls, obj: object, attr: str) -> Self: ...
    def _wrap(self, obj: object, attr: str) -> None: ...
    def restore(self) -> None: ...
