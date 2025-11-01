from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import ANY, Mock, call

import freezegun
import pytest
from lxml.etree import ParseError

from streamlink.exceptions import PluginError
from streamlink.stream.dash import MPD, DASHSegment, DASHStream, DASHStreamWorker, MPDParsingError
from streamlink.stream.dash.dash import log
from streamlink.utils.parse import parse_xml as original_parse_xml
from tests.resources import text, xml


if TYPE_CHECKING:
    import requests_mock as rm

    from streamlink.session import Streamlink
    from streamlink.stream.dash import DASHStreamReader


does_not_raise = nullcontext()


@pytest.fixture()
def timestamp():
    with freezegun.freeze_time("2000-01-01T00:00:00Z"):
        yield datetime.now(timezone.utc)


def test_logger_name():
    assert log.name == "streamlink.stream.dash"


class TestDASHStreamParseManifest:
    @pytest.fixture(autouse=True)
    def _response(self, request: pytest.FixtureRequest, requests_mock: rm.Mocker):
        response = requests_mock.register_uri("GET", "http://test/manifest.mpd", **getattr(request, "param", {}))
        called_once = "nomockedhttprequest" not in request.keywords
        yield
        assert (response.call_count == 1) is called_once

    @pytest.fixture()
    def parse_xml(self, monkeypatch: pytest.MonkeyPatch):
        parse_xml = Mock(return_value=Mock())
        monkeypatch.setattr("streamlink.stream.dash.dash.parse_xml", parse_xml)
        return parse_xml

    @pytest.fixture()
    def mpd(self, monkeypatch: pytest.MonkeyPatch, parse_xml: Mock):
        mpd = Mock()
        monkeypatch.setattr("streamlink.stream.dash.dash.MPD", mpd)
        return mpd

    @pytest.mark.parametrize(
        ("se_parse_xml", "se_mpd"),
        [
            (ParseError, None),
            (None, MPDParsingError),
        ],
    )
    def test_parse_fail(self, session: Streamlink, mpd: Mock, parse_xml: Mock, se_parse_xml, se_mpd):
        parse_xml.side_effect = se_parse_xml
        mpd.side_effect = se_mpd

        with pytest.raises(PluginError) as cm:
            DASHStream.parse_manifest(session, "http://test/manifest.mpd")
        assert str(cm.value).startswith("Failed to parse MPD manifest: ")

    def test_video_only(self, session: Streamlink, mpd: Mock):
        adaptationset = Mock(
            contentProtections=None,
            representations=[
                Mock(id="1", contentProtections=None, mimeType="video/mp4", height=720),
                Mock(id="2", contentProtections=None, mimeType="video/mp4", height=1080),
            ],
        )
        mpd.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(session, "http://test/manifest.mpd")
        assert mpd.call_args_list == [call(ANY, url="http://test/manifest.mpd", base_url="http://test/manifest.mpd")]
        assert sorted(streams.keys()) == sorted(["720p", "1080p"])

    def test_audio_only(self, session: Streamlink, mpd: Mock):
        adaptationset = Mock(
            contentProtections=None,
            representations=[
                Mock(id="1", contentProtections=None, mimeType="audio/mp4", bandwidth=128.0, lang="en"),
                Mock(id="2", contentProtections=None, mimeType="audio/mp4", bandwidth=256.0, lang="en"),
            ],
        )
        mpd.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(session, "http://test/manifest.mpd")
        assert mpd.call_args_list == [call(ANY, url="http://test/manifest.mpd", base_url="http://test/manifest.mpd")]
        assert sorted(streams.keys()) == sorted(["a128k", "a256k"])

    @pytest.mark.parametrize(
        ("with_video_only", "with_audio_only", "expected"),
        [
            pytest.param(
                False,
                False,
                ["720p+a128k", "720p+a256k", "1080p+a128k", "1080p+a256k"],
                id="Only muxed streams",
            ),
            pytest.param(
                True,
                False,
                ["720p", "720p+a128k", "720p+a256k", "1080p", "1080p+a128k", "1080p+a256k"],
                id="With video-only streams",
            ),
            pytest.param(
                False,
                True,
                ["a128k", "a256k", "720p+a128k", "720p+a256k", "1080p+a128k", "1080p+a256k"],
                id="With audio-only streams",
            ),
            pytest.param(
                True,
                True,
                ["a128k", "a256k", "720p", "720p+a128k", "720p+a256k", "1080p", "1080p+a128k", "1080p+a256k"],
                id="With video-only and audio-only streams",
            ),
        ],
    )
    def test_with_videoaudio_only(
        self,
        session: Streamlink,
        mpd: Mock,
        with_video_only: bool,
        with_audio_only: bool,
        expected: list[str],
    ):
        adaptationset = Mock(
            contentProtections=None,
            representations=[
                Mock(id="1", contentProtections=None, mimeType="video/mp4", height=720),
                Mock(id="2", contentProtections=None, mimeType="video/mp4", height=1080),
                Mock(id="3", contentProtections=None, mimeType="audio/mp4", bandwidth=128.0, lang="en"),
                Mock(id="4", contentProtections=None, mimeType="audio/mp4", bandwidth=256.0, lang="en"),
            ],
        )
        mpd.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(
            session,
            "http://test/manifest.mpd",
            with_video_only=with_video_only,
            with_audio_only=with_audio_only,
        )
        assert mpd.call_args_list == [call(ANY, url="http://test/manifest.mpd", base_url="http://test/manifest.mpd")]
        assert list(streams.keys()) == expected

    def test_audio_single(self, session: Streamlink, mpd: Mock):
        adaptationset = Mock(
            contentProtections=None,
            representations=[
                Mock(id="1", contentProtections=None, mimeType="video/mp4", height=720),
                Mock(id="2", contentProtections=None, mimeType="video/mp4", height=1080),
                Mock(id="3", contentProtections=None, mimeType="audio/aac", bandwidth=128.0, lang="en"),
            ],
        )
        mpd.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(session, "http://test/manifest.mpd")
        assert mpd.call_args_list == [call(ANY, url="http://test/manifest.mpd", base_url="http://test/manifest.mpd")]
        assert sorted(streams.keys()) == sorted(["720p", "1080p"])

    def test_audio_multi(self, session: Streamlink, mpd: Mock):
        adaptationset = Mock(
            contentProtections=None,
            representations=[
                Mock(id="1", contentProtections=None, mimeType="video/mp4", height=720),
                Mock(id="2", contentProtections=None, mimeType="video/mp4", height=1080),
                Mock(id="3", contentProtections=None, mimeType="audio/aac", bandwidth=128.0, lang="en"),
                Mock(id="4", contentProtections=None, mimeType="audio/aac", bandwidth=256.0, lang="en"),
            ],
        )
        mpd.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(session, "http://test/manifest.mpd")
        assert mpd.call_args_list == [call(ANY, url="http://test/manifest.mpd", base_url="http://test/manifest.mpd")]
        assert sorted(streams.keys()) == sorted(["720p+a128k", "1080p+a128k", "720p+a256k", "1080p+a256k"])

    def test_audio_multi_lang(self, session: Streamlink, mpd: Mock):
        adaptationset = Mock(
            contentProtections=None,
            representations=[
                Mock(id="1", contentProtections=None, mimeType="video/mp4", height=720),
                Mock(id="2", contentProtections=None, mimeType="video/mp4", height=1080),
                Mock(id="3", contentProtections=None, mimeType="audio/aac", bandwidth=128.0, lang="en"),
                Mock(id="4", contentProtections=None, mimeType="audio/aac", bandwidth=128.0, lang="es"),
            ],
        )
        mpd.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(session, "http://test/manifest.mpd")
        assert mpd.call_args_list == [call(ANY, url="http://test/manifest.mpd", base_url="http://test/manifest.mpd")]
        assert sorted(streams.keys()) == sorted(["720p", "1080p"])
        assert getattr(streams["720p"].audio_representation, "lang", None) == "en"
        assert getattr(streams["1080p"].audio_representation, "lang", None) == "en"

    def test_audio_multi_lang_alpha3(self, session: Streamlink, mpd: Mock):
        adaptationset = Mock(
            contentProtections=None,
            representations=[
                Mock(id="1", contentProtections=None, mimeType="video/mp4", height=720),
                Mock(id="2", contentProtections=None, mimeType="video/mp4", height=1080),
                Mock(id="3", contentProtections=None, mimeType="audio/aac", bandwidth=128.0, lang="eng"),
                Mock(id="4", contentProtections=None, mimeType="audio/aac", bandwidth=128.0, lang="spa"),
            ],
        )
        mpd.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(session, "http://test/manifest.mpd")
        assert mpd.call_args_list == [call(ANY, url="http://test/manifest.mpd", base_url="http://test/manifest.mpd")]
        assert sorted(streams.keys()) == sorted(["720p", "1080p"])
        assert getattr(streams["720p"].audio_representation, "lang", None) == "eng"
        assert getattr(streams["1080p"].audio_representation, "lang", None) == "eng"

    def test_audio_invalid_lang(self, session: Streamlink, mpd: Mock):
        adaptationset = Mock(
            contentProtections=None,
            representations=[
                Mock(id="1", contentProtections=None, mimeType="video/mp4", height=720),
                Mock(id="2", contentProtections=None, mimeType="video/mp4", height=1080),
                Mock(id="3", contentProtections=None, mimeType="audio/aac", bandwidth=128.0, lang="en_no_voice"),
            ],
        )
        mpd.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(session, "http://test/manifest.mpd")
        assert mpd.call_args_list == [call(ANY, url="http://test/manifest.mpd", base_url="http://test/manifest.mpd")]
        assert sorted(streams.keys()) == sorted(["720p", "1080p"])
        assert getattr(streams["720p"].audio_representation, "lang", None) == "en_no_voice"
        assert getattr(streams["1080p"].audio_representation, "lang", None) == "en_no_voice"

    def test_audio_multi_lang_locale(self, monkeypatch: pytest.MonkeyPatch, session: Streamlink, mpd: Mock):
        session.set_option("locale", "es_ES")

        adaptationset = Mock(
            contentProtections=None,
            representations=[
                Mock(id="1", contentProtections=None, mimeType="video/mp4", height=720),
                Mock(id="2", contentProtections=None, mimeType="video/mp4", height=1080),
                Mock(id="3", contentProtections=None, mimeType="audio/aac", bandwidth=128.0, lang="en"),
                Mock(id="4", contentProtections=None, mimeType="audio/aac", bandwidth=128.0, lang="es"),
            ],
        )
        mpd.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(session, "http://test/manifest.mpd")
        assert mpd.call_args_list == [call(ANY, url="http://test/manifest.mpd", base_url="http://test/manifest.mpd")]
        assert sorted(streams.keys()) == sorted(["720p", "1080p"])
        assert getattr(streams["720p"].audio_representation, "lang", None) == "es"
        assert getattr(streams["1080p"].audio_representation, "lang", None) == "es"

    # Verify the fix for https://github.com/streamlink/streamlink/issues/3365
    def test_duplicated_resolutions(self, session: Streamlink, mpd: Mock):
        adaptationset = Mock(
            contentProtections=None,
            representations=[
                Mock(id="1", contentProtections=None, mimeType="video/mp4", height=1080, bandwidth=128.0),
                Mock(id="2", contentProtections=None, mimeType="video/mp4", height=1080, bandwidth=64.0),
                Mock(id="3", contentProtections=None, mimeType="video/mp4", height=1080, bandwidth=32.0),
                Mock(id="4", contentProtections=None, mimeType="video/mp4", height=720),
            ],
        )
        mpd.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(session, "http://test/manifest.mpd")
        assert mpd.call_args_list == [call(ANY, url="http://test/manifest.mpd", base_url="http://test/manifest.mpd")]
        assert sorted(streams.keys()) == sorted(["720p", "1080p", "1080p_alt", "1080p_alt2"])

    # Verify the fix for https://github.com/streamlink/streamlink/issues/4217
    def test_duplicated_resolutions_sorted_bandwidth(self, session: Streamlink, mpd: Mock):
        adaptationset = Mock(
            contentProtections=None,
            representations=[
                Mock(id="1", contentProtections=None, mimeType="video/mp4", height=1080, bandwidth=64.0),
                Mock(id="2", contentProtections=None, mimeType="video/mp4", height=1080, bandwidth=128.0),
                Mock(id="3", contentProtections=None, mimeType="video/mp4", height=1080, bandwidth=32.0),
            ],
        )
        mpd.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(session, "http://test/manifest.mpd")
        assert mpd.call_args_list == [call(ANY, url="http://test/manifest.mpd", base_url="http://test/manifest.mpd")]
        assert getattr(streams["1080p"].video_representation, "bandwidth", None) == pytest.approx(128.0)
        assert getattr(streams["1080p_alt"].video_representation, "bandwidth", None) == pytest.approx(64.0)
        assert getattr(streams["1080p_alt2"].video_representation, "bandwidth", None) == pytest.approx(32.0)

    @pytest.mark.parametrize(
        "adaptationset",
        [
            pytest.param(
                Mock(contentProtections="DRM", representations=[]),
                id="ContentProtection on AdaptationSet",
            ),
            pytest.param(
                Mock(contentProtections=None, representations=[Mock(id="1", contentProtections="DRM")]),
                id="ContentProtection on Representation",
            ),
        ],
    )
    def test_contentprotection(self, session: Streamlink, mpd: Mock, adaptationset: Mock):
        mpd.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        with pytest.raises(PluginError):
            DASHStream.parse_manifest(session, "http://test/manifest.mpd")

    @pytest.mark.nomockedhttprequest()
    def test_string(self, session: Streamlink, mpd: Mock, parse_xml: Mock):
        with text("dash/test_9.mpd") as mpd_txt:
            test_manifest = mpd_txt.read()
        parse_xml.side_effect = original_parse_xml
        mpd.side_effect = MPD

        streams = DASHStream.parse_manifest(session, test_manifest)
        assert mpd.call_args_list == [call(ANY)]
        assert list(streams.keys()) == ["480p"]

    # TODO: Move this test to test_dash_parser and properly test segment URLs.
    #       This test currently achieves nothing... (manifest fixture added in 7aada92)
    def test_segments_number_time(self, session: Streamlink, mpd: Mock):
        with xml("dash/test_9.mpd") as mpd_xml:
            mpd.return_value = MPD(mpd_xml, base_url="http://test/manifest.mpd", url="http://test/manifest.mpd")

        streams = DASHStream.parse_manifest(session, "http://test/manifest.mpd")
        assert mpd.call_args_list == [call(ANY, url="http://test/manifest.mpd", base_url="http://test/manifest.mpd")]
        assert list(streams.keys()) == ["480p"]

    @pytest.mark.parametrize(
        ("period", "raises"),
        [
            pytest.param(0, does_not_raise, id="index-0"),
            pytest.param(1, does_not_raise, id="index-1"),
            pytest.param(2, does_not_raise, id="index-2"),
            pytest.param("p1", does_not_raise, id="id-p1"),
            pytest.param("p2", does_not_raise, id="id-p2"),
            pytest.param(3, pytest.raises(PluginError, match=r"^DASH period 3 not found\."), id="error-index"),
            pytest.param("p3", pytest.raises(PluginError, match=r"^DASH period 'p3' not found\."), id="error-id"),
        ],
    )
    def test_period_selection(
        self,
        caplog: pytest.LogCaptureFixture,
        session: Streamlink,
        mpd: Mock,
        period: int | str,
        raises: nullcontext,
    ):
        caplog.set_level(1, "streamlink")

        with xml("dash/test_period_selection.mpd") as mpd_xml:
            mpd.return_value = MPD(mpd_xml, base_url="http://test/manifest.mpd", url="http://test/manifest.mpd")

        with raises:
            streams = DASHStream.parse_manifest(session, "http://test/manifest.mpd", period=period)
            assert streams

        records = [(record.name, record.levelname, record.message) for record in caplog.records]
        assert ("streamlink.stream.dash", "debug", "Available DASH periods: 0, 1 (id='p1'), 2 (id='p2')") in records


class TestDASHStreamOpen:
    @pytest.fixture()
    def reader(self, monkeypatch: pytest.MonkeyPatch):
        reader = Mock()
        monkeypatch.setattr("streamlink.stream.dash.dash.DASHStreamReader", reader)
        return reader

    @pytest.fixture()
    def muxer(self, monkeypatch: pytest.MonkeyPatch):
        muxer = Mock()
        muxer.is_usable.return_value = True
        monkeypatch.setattr("streamlink.stream.dash.dash.FFMPEGMuxer", muxer)
        return muxer

    def test_stream_open_video_only(self, session: Streamlink, timestamp: datetime, muxer: Mock, reader: Mock):
        rep_video = Mock(ident=(None, None, "1"), mimeType="video/mp4")
        stream = DASHStream(session, Mock(), rep_video)
        stream.open()

        assert reader.call_args_list == [call(stream, rep_video, timestamp, name="video")]
        assert reader().open.call_count == 1
        assert muxer.call_args_list == []

    def test_stream_open_video_audio(self, session: Streamlink, timestamp: datetime, muxer: Mock, reader: Mock):
        rep_video = Mock(ident=(None, None, "1"), mimeType="video/mp4")
        rep_audio = Mock(ident=(None, None, "2"), mimeType="audio/mp3", lang="en")

        mock_reader_video = Mock()
        mock_reader_audio = Mock()
        readers = {rep_video: mock_reader_video, rep_audio: mock_reader_audio}
        reader.side_effect = lambda _stream, _representation, _timestamp, *_, **__: readers[_representation]

        stream = DASHStream(session, Mock(), rep_video, rep_audio)
        stream.open()

        assert reader.call_args_list == [
            call(stream, rep_video, timestamp, name="video"),
            call(stream, rep_audio, timestamp, name="audio"),
        ]
        assert mock_reader_video.open.call_count == 1
        assert mock_reader_audio.open.call_count == 1
        assert muxer.call_args_list == [call(session, mock_reader_video, mock_reader_audio, copyts=True)]


class TestDASHStreamWorker:
    @pytest.fixture()
    def mock_time(self, monkeypatch: pytest.MonkeyPatch) -> Mock:
        mock = Mock(return_value=1)
        monkeypatch.setattr("streamlink.stream.dash.dash.time", mock)
        return mock

    @pytest.fixture(autouse=True)
    def mock_wait(self, monkeypatch: pytest.MonkeyPatch) -> Mock:
        mock = Mock(return_value=True)
        monkeypatch.setattr("streamlink.stream.dash.dash.DASHStreamWorker.wait", mock)
        return mock

    @pytest.fixture()
    def segments(self) -> list[DASHSegment]:
        return [
            DASHSegment(uri="init_segment", num=-1, duration=0.0),
            DASHSegment(uri="first_segment", num=0, duration=2.0),
            DASHSegment(uri="second_segment", num=1, duration=3.0),
            DASHSegment(uri="third_segment", num=2, duration=5.0),
            DASHSegment(uri="fourth_segment", num=3, duration=8.0),
            DASHSegment(uri="fifth_segment", num=4, duration=13.0),
        ]

    @pytest.fixture()
    def mpd(self) -> Mock:
        representation = Mock(
            ident=(None, None, "1"),
            mimeType="video/mp4",
            height=720,
        )
        adaptationset = Mock(
            contentProtections=None,
            representations=[representation],
        )
        period = Mock(
            duration=Mock(total_seconds=Mock(return_value=0)),
            adaptationSets=[adaptationset],
        )
        representation.period = period

        return Mock(
            publishTime=1,
            minimumUpdatePeriod=Mock(total_seconds=Mock(return_value=0)),
            periods=[period],
            get_representation=Mock(return_value=representation),
        )

    @pytest.fixture()
    def representation(self, mpd) -> Mock:
        return mpd.periods[0].adaptationSets[0].representations[0]

    @pytest.fixture()
    def stream(self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, session: Streamlink, mpd: Mock):
        options = getattr(request, "param", {})

        monkeypatch.setattr(session.http, "request", Mock())
        monkeypatch.setattr(session.http, "xml", Mock())

        return DASHStream(session, mpd, **options)

    @pytest.fixture()
    def reader(self, session: Streamlink, stream: DASHStream, timestamp: datetime):
        return Mock(
            session=session,
            stream=stream,
            ident=(None, None, "1"),
            timestamp=timestamp,
        )

    @pytest.fixture()
    def worker(self, reader: DASHStreamReader):
        return DASHStreamWorker(reader)

    def test_dynamic_reload(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        timestamp: datetime,
        worker: DASHStreamWorker,
        representation: Mock,
        segments: list[DASHSegment],
        mpd: Mock,
    ):
        caplog.set_level("INFO", "streamlink")

        mpd.dynamic = True
        mpd.type = "dynamic"
        monkeypatch.setattr("streamlink.stream.dash.dash.MPD", lambda *args, **kwargs: mpd)

        segment_iter = worker.iter_segments()

        def next_segments(num):
            items = []
            for _ in range(num):
                segment = next(segment_iter)
                # fake worker.run() implementation
                worker.check_sequence_gap(segment)
                worker.sequence = segment.num + 1
                items.append(segment)

            return items

        representation.segments.return_value = segments[:2]
        assert next_segments(2) == segments[:2]
        assert representation.segments.call_args_list == [call(sequence=-1, init=True, timestamp=timestamp)]
        assert not worker._wait.is_set()
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == []

        representation.segments.reset_mock()
        representation.segments.return_value = segments[3:]
        assert next_segments(3) == segments[3:]
        assert representation.segments.call_args_list == [call(), call(sequence=1, init=False, timestamp=None)]
        assert not worker._wait.is_set()
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.stream.segmented",
                "warning",
                "Sequence gap of 1 segment at position 1. This is unsupported and will result in incoherent output data.",
            ),
        ]

    def test_static(
        self,
        worker: DASHStreamWorker,
        timestamp: datetime,
        representation: Mock,
        segments: list[DASHSegment],
        mpd: Mock,
    ):
        mpd.dynamic = False
        mpd.type = "static"

        representation.segments.return_value = segments
        assert list(worker.iter_segments()) == segments
        assert representation.segments.call_args_list == [call(sequence=-1, init=True, timestamp=timestamp)]
        assert worker._wait.is_set()

    # Verify the fix for https://github.com/streamlink/streamlink/issues/2873
    @pytest.mark.parametrize(
        "period_duration",
        [
            0,
            204.32,
        ],
    )
    def test_static_refresh_wait(
        self,
        timestamp: datetime,
        mock_wait: Mock,
        mock_time: Mock,
        worker: DASHStreamWorker,
        representation: Mock,
        segments: list[DASHSegment],
        mpd: Mock,
        period_duration: float,
    ):
        mpd.dynamic = False
        mpd.type = "static"
        mpd.periods[0].duration.total_seconds.return_value = period_duration

        representation.segments.return_value = segments
        assert list(worker.iter_segments()) == segments
        assert representation.segments.call_args_list == [call(sequence=-1, init=True, timestamp=timestamp)]
        assert mock_wait.call_args_list == [call(5)]
        assert worker._wait.is_set()

    @pytest.mark.parametrize(
        ("stream", "session"),
        [
            pytest.param(
                {"duration": 5.0},
                {},
                id="duration keyword",
            ),
            pytest.param(
                {},
                {"stream-segmented-duration": 5.0},
                id="stream-segmented-duration session option",
            ),
            pytest.param(
                {"duration": 5.0},
                {"stream-segmented-duration": 2.0},
                id="duration keyword priority",
            ),
        ],
        indirect=["stream", "session"],
    )
    def test_duration(
        self,
        caplog: pytest.LogCaptureFixture,
        reader: Mock,
        worker: DASHStreamWorker,
        timestamp: datetime,
        representation: Mock,
        segments: list[DASHSegment],
        mpd: Mock,
        stream: DASHStream,
        session: Streamlink,
    ):
        caplog.set_level("INFO", "streamlink")

        mpd.dynamic = False
        mpd.type = "static"

        representation.segments.return_value = segments
        worker.run()

        assert [call_arg.args[0] for call_arg in reader.writer.put.call_args_list] == [*segments[0:3], None]
        assert representation.segments.call_args_list == [call(sequence=-1, init=True, timestamp=timestamp)]
        assert worker._wait.is_set()
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            ("streamlink.stream.segmented", "info", "Stopping stream early after 5.00s"),
        ]
