import pytest

from tests.mixins.stream_hls import TestMixinStreamHLS


@pytest.fixture(autouse=True)
def caplog_on_testcase(request: pytest.FixtureRequest, caplog: pytest.LogCaptureFixture):
    if not isinstance(request.instance, TestMixinStreamHLS):
        return

    caplog.set_level("info", "streamlink")
    request.instance.caplog = caplog  # type: ignore[attr-defined]
