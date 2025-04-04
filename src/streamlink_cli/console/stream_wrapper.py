from __future__ import annotations

from io import TextIOWrapper


class StreamWrapper:
    def __init__(self, stream):
        super().__init__()
        self._stream = stream
        self._target = None

    @classmethod
    def wrap(cls, obj, attr):
        stream = getattr(obj, attr)
        if not isinstance(stream, TextIOWrapper):
            raise AttributeError(f"{stream!r} is not a TextIOWrapper object ({obj!r}, {attr!r})")

        console_output_stream = cls(stream)
        console_output_stream._wrap(obj, attr)

        return console_output_stream

    def _wrap(self, obj, attr):
        self._target = obj, attr
        setattr(obj, attr, self)

    def restore(self):
        if self._target:  # pragma: no branch
            setattr(*self._target, self._stream)

    def __getattr__(self, name):
        return getattr(self._stream, name)

    def __del__(self):  # pragma: no cover
        # Don't automatically close the underlying buffer on object destruction, as this breaks our tests.
        # We manually close the wrapped streams ourselves.
        return
