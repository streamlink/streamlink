from tests.plugin.testplugin import TestPlugin as _TestPlugin


class FakePlugin(_TestPlugin):
    __module__ = "fake"
    _streams = {}  # type: ignore

    def streams(self, *args, **kwargs):
        return self._streams

    def _get_streams(self):  # pragma: no cover
        pass
