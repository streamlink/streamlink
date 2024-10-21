import pytest
from requests_mock import Mocker

from streamlink import Streamlink
from streamlink.plugins.rtpplay import RTPPlay
from tests.plugins import PluginCanHandleUrl
from tests.resources import text


class TestPluginCanHandleUrlRTPPlay(PluginCanHandleUrl):
    __plugin__ = RTPPlay

    should_match = [
        "http://www.rtp.pt/play/",
        "https://www.rtp.pt/play/",
        "https://www.rtp.pt/play/direto/rtp1",
        "https://www.rtp.pt/play/direto/rtpmadeira",
    ]

    should_not_match = [
        "https://www.rtp.pt/programa/",
        "http://www.rtp.pt/programa/",
        "https://media.rtp.pt/",
        "http://media.rtp.pt/",
    ]


class TestRTPPlay:
    # all invalid HLS URLs at the beginning need to be ignored ("https://invalid")
    _content_pre = """
        /*  var player1 = new RTPPlayer({
                file: {hls : atob( decodeURIComponent(["aHR0c", "HM6Ly", "9pbnZ", "hbGlk"].join("") ) ), dash : foo() } }); */
        var f = {hls : atob( decodeURIComponent(["aHR0c", "HM6Ly", "9pbnZ", "hbGlk"].join("") ) ), dash: foo() };
    """
    # invalid resources sometimes have an empty string as HLS URL
    _content_invalid = """
        var f = {hls : ""};
    """
    # the actual HLS URL always comes last ("https://valid")
    _content_valid = """
        var f = {hls : decodeURIComponent(["https%3","A%2F%2F", "valid"].join("") ), dash: foo() };
    """
    _content_valid_b64 = """
        var f = {hls : atob( decodeURIComponent(["aHR0c", "HM6Ly", "92YWx", "pZA=="].join("") ) ), dash: foo() };
    """

    @pytest.fixture(scope="class")
    def playlist(self):
        with text("hls/test_master.m3u8") as fd:
            return fd.read()

    @pytest.fixture()
    def streams(self, request: pytest.FixtureRequest, requests_mock: Mocker, session: Streamlink, playlist: str):
        response = getattr(request, "param", "")

        requests_mock.get("https://www.rtp.pt/play/id/title", text=response)
        requests_mock.get("https://valid", text=playlist)
        requests_mock.get("https://invalid", exc=AssertionError)

        plugin = RTPPlay(session, "https://www.rtp.pt/play/id/title")

        return plugin._get_streams()

    @pytest.mark.parametrize(
        ("streams", "expected"),
        [
            pytest.param(
                "",
                False,
                id="empty",
            ),
            pytest.param(
                _content_pre + _content_invalid,
                False,
                id="invalid",
            ),
            pytest.param(
                _content_pre + _content_valid,
                True,
                id="valid",
            ),
            pytest.param(
                _content_pre + _content_valid_b64,
                True,
                id="valid-b64",
            ),
        ],
        indirect=["streams"],
    )
    def test_streams(self, streams, expected):
        assert (streams is not None) is expected
