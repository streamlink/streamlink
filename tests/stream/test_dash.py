import unittest
from typing import List
from unittest.mock import ANY, MagicMock, Mock, call, patch

import pytest

from streamlink import PluginError
from streamlink.stream.dash import DASHStream, DASHStreamWorker
from streamlink.stream.dash_manifest import MPD
from tests.resources import text, xml


class TestDASHStream(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()
        self.test_url = "http://test.bar/foo.mpd"
        self.session.http.get.return_value = Mock(url=self.test_url)

    @patch("streamlink.stream.dash.MPD")
    def test_parse_manifest_video_only(self, mpdClass):
        adaptationset = Mock(
            contentProtection=None,
            representations=[
                Mock(id="1", contentProtection=None, mimeType="video/mp4", height=720),
                Mock(id="2", contentProtection=None, mimeType="video/mp4", height=1080),
            ],
        )
        mpdClass.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        assert sorted(streams.keys()) == sorted(["720p", "1080p"])

    @patch("streamlink.stream.dash.MPD")
    def test_parse_manifest_audio_only(self, mpdClass):
        adaptationset = Mock(
            contentProtection=None,
            representations=[
                Mock(id="1", contentProtection=None, mimeType="audio/mp4", bandwidth=128.0, lang="en"),
                Mock(id="2", contentProtection=None, mimeType="audio/mp4", bandwidth=256.0, lang="en"),
            ],
        )
        mpdClass.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        assert sorted(streams.keys()) == sorted(["a128k", "a256k"])

    @patch("streamlink.stream.dash.MPD")
    def test_parse_manifest_audio_single(self, mpdClass):
        adaptationset = Mock(
            contentProtection=None,
            representations=[
                Mock(id="1", contentProtection=None, mimeType="video/mp4", height=720),
                Mock(id="2", contentProtection=None, mimeType="video/mp4", height=1080),
                Mock(id="3", contentProtection=None, mimeType="audio/aac", bandwidth=128.0, lang="en"),
            ],
        )
        mpdClass.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        assert sorted(streams.keys()) == sorted(["720p", "1080p"])

    @patch("streamlink.stream.dash.MPD")
    def test_parse_manifest_audio_multi(self, mpdClass):
        adaptationset = Mock(
            contentProtection=None,
            representations=[
                Mock(id="1", contentProtection=None, mimeType="video/mp4", height=720),
                Mock(id="2", contentProtection=None, mimeType="video/mp4", height=1080),
                Mock(id="3", contentProtection=None, mimeType="audio/aac", bandwidth=128.0, lang="en"),
                Mock(id="4", contentProtection=None, mimeType="audio/aac", bandwidth=256.0, lang="en"),
            ],
        )
        mpdClass.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        assert sorted(streams.keys()) == sorted(["720p+a128k", "1080p+a128k", "720p+a256k", "1080p+a256k"])

    @patch("streamlink.stream.dash.MPD")
    def test_parse_manifest_audio_multi_lang(self, mpdClass):
        adaptationset = Mock(
            contentProtection=None,
            representations=[
                Mock(id="1", contentProtection=None, mimeType="video/mp4", height=720),
                Mock(id="2", contentProtection=None, mimeType="video/mp4", height=1080),
                Mock(id="3", contentProtection=None, mimeType="audio/aac", bandwidth=128.0, lang="en"),
                Mock(id="4", contentProtection=None, mimeType="audio/aac", bandwidth=128.0, lang="es"),
            ],
        )
        mpdClass.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        assert sorted(streams.keys()) == sorted(["720p", "1080p"])

        assert streams["720p"].audio_representation.lang == "en"
        assert streams["1080p"].audio_representation.lang == "en"

    @patch("streamlink.stream.dash.MPD")
    def test_parse_manifest_audio_multi_lang_alpha3(self, mpdClass):
        adaptationset = Mock(
            contentProtection=None,
            representations=[
                Mock(id="1", contentProtection=None, mimeType="video/mp4", height=720),
                Mock(id="2", contentProtection=None, mimeType="video/mp4", height=1080),
                Mock(id="3", contentProtection=None, mimeType="audio/aac", bandwidth=128.0, lang="eng"),
                Mock(id="4", contentProtection=None, mimeType="audio/aac", bandwidth=128.0, lang="spa"),
            ],
        )
        mpdClass.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        assert sorted(streams.keys()) == sorted(["720p", "1080p"])

        assert streams["720p"].audio_representation.lang == "eng"
        assert streams["1080p"].audio_representation.lang == "eng"

    @patch("streamlink.stream.dash.MPD")
    def test_parse_manifest_audio_invalid_lang(self, mpdClass):
        adaptationset = Mock(
            contentProtection=None,
            representations=[
                Mock(id="1", contentProtection=None, mimeType="video/mp4", height=720),
                Mock(id="2", contentProtection=None, mimeType="video/mp4", height=1080),
                Mock(id="3", contentProtection=None, mimeType="audio/aac", bandwidth=128.0, lang="en_no_voice"),
            ],
        )
        mpdClass.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        assert sorted(streams.keys()) == sorted(["720p", "1080p"])

        assert streams["720p"].audio_representation.lang == "en_no_voice"
        assert streams["1080p"].audio_representation.lang == "en_no_voice"

    @patch("streamlink.stream.dash.MPD")
    def test_parse_manifest_audio_multi_lang_locale(self, mpdClass):
        self.session.localization.language.alpha2 = "es"
        self.session.localization.explicit = True

        adaptationset = Mock(
            contentProtection=None,
            representations=[
                Mock(id="1", contentProtection=None, mimeType="video/mp4", height=720),
                Mock(id="2", contentProtection=None, mimeType="video/mp4", height=1080),
                Mock(id="3", contentProtection=None, mimeType="audio/aac", bandwidth=128.0, lang="en"),
                Mock(id="4", contentProtection=None, mimeType="audio/aac", bandwidth=128.0, lang="es"),
            ],
        )
        mpdClass.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        assert sorted(streams.keys()) == sorted(["720p", "1080p"])

        assert streams["720p"].audio_representation.lang == "es"
        assert streams["1080p"].audio_representation.lang == "es"

    @patch("streamlink.stream.dash.MPD")
    def test_parse_manifest_drm_adaptationset(self, mpdClass):
        adaptationset = Mock(
            contentProtection="DRM",
            representations=[],
        )
        mpdClass.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        with pytest.raises(PluginError):
            DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

    @patch("streamlink.stream.dash.MPD")
    def test_parse_manifest_drm_representation(self, mpdClass):
        adaptationset = Mock(
            contentProtection=None,
            representations=[
                Mock(id="1", contentProtection="DRM"),
            ],
        )
        mpdClass.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        with pytest.raises(PluginError):
            DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

    def test_parse_manifest_string(self):
        with text("dash/test_9.mpd") as mpd_txt:
            test_manifest = mpd_txt.read()

        streams = DASHStream.parse_manifest(self.session, test_manifest)
        assert list(streams.keys()) == ["2500k"]

    @patch("streamlink.stream.dash.DASHStreamReader")
    @patch("streamlink.stream.dash.FFMPEGMuxer")
    def test_stream_open_video_only(self, muxer: Mock, reader: Mock):
        rep_video = Mock(ident=(None, None, "1"), mimeType="video/mp4")
        stream = DASHStream(self.session, Mock(), rep_video)
        stream.open()

        assert reader.call_args_list == [call(stream, rep_video)]
        reader_video = reader(stream, rep_video)
        assert reader_video.open.called_once
        assert muxer.call_args_list == []

    @patch("streamlink.stream.dash.DASHStreamReader")
    @patch("streamlink.stream.dash.FFMPEGMuxer")
    def test_stream_open_video_audio(self, muxer: Mock, reader: Mock):
        rep_video = Mock(ident=(None, None, "1"), mimeType="video/mp4")
        rep_audio = Mock(ident=(None, None, "2"), mimeType="audio/mp3", lang="en")
        stream = DASHStream(self.session, Mock(), rep_video, rep_audio)
        stream.open()

        assert reader.call_args_list == [call(stream, rep_video), call(stream, rep_audio)]
        reader_video = reader(stream, rep_video)
        reader_audio = reader(stream, rep_audio)
        assert reader_video.open.called_once
        assert reader_audio.open.called_once
        assert muxer.call_args_list == [call(self.session, reader_video, reader_audio, copyts=True)]

    @patch("streamlink.stream.dash.MPD")
    def test_segments_number_time(self, mpdClass):
        with xml("dash/test_9.mpd") as mpd_xml:
            mpdClass.return_value = MPD(mpd_xml, base_url="http://test.bar", url="http://test.bar/foo.mpd")

            streams = DASHStream.parse_manifest(self.session, self.test_url)
            mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

            assert list(streams.keys()) == ["2500k"]

    @patch("streamlink.stream.dash.MPD")
    def test_parse_manifest_with_duplicated_resolutions(self, mpdClass):
        """
            Verify the fix for https://github.com/streamlink/streamlink/issues/3365
        """
        adaptationset = Mock(
            contentProtection=None,
            representations=[
                Mock(id="1", contentProtection=None, mimeType="video/mp4", height=1080, bandwidth=128.0),
                Mock(id="2", contentProtection=None, mimeType="video/mp4", height=1080, bandwidth=64.0),
                Mock(id="3", contentProtection=None, mimeType="video/mp4", height=1080, bandwidth=32.0),
                Mock(id="4", contentProtection=None, mimeType="video/mp4", height=720),
            ],
        )
        mpdClass.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        assert sorted(streams.keys()) == sorted(["720p", "1080p", "1080p_alt", "1080p_alt2"])

    @patch("streamlink.stream.dash.MPD")
    def test_parse_manifest_with_duplicated_resolutions_sorted_bandwidth(self, mpdClass):
        """
            Verify the fix for https://github.com/streamlink/streamlink/issues/4217
        """
        adaptationset = Mock(
            contentProtection=None,
            representations=[
                Mock(id="1", contentProtection=None, mimeType="video/mp4", height=1080, bandwidth=64.0),
                Mock(id="2", contentProtection=None, mimeType="video/mp4", height=1080, bandwidth=128.0),
                Mock(id="3", contentProtection=None, mimeType="video/mp4", height=1080, bandwidth=32.0),
            ],
        )
        mpdClass.return_value = Mock(periods=[Mock(adaptationSets=[adaptationset])])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        assert streams["1080p"].video_representation.bandwidth == pytest.approx(128.0)
        assert streams["1080p_alt"].video_representation.bandwidth == pytest.approx(64.0)
        assert streams["1080p_alt2"].video_representation.bandwidth == pytest.approx(32.0)


class TestDASHStreamWorker:
    @pytest.fixture()
    def mock_time(self, monkeypatch: pytest.MonkeyPatch) -> Mock:
        mock = Mock(return_value=1)
        monkeypatch.setattr("streamlink.stream.dash.time", mock)
        return mock

    @pytest.fixture(autouse=True)
    def mock_wait(self, monkeypatch: pytest.MonkeyPatch) -> Mock:
        mock = Mock(return_value=True)
        monkeypatch.setattr("streamlink.stream.dash.DASHStreamWorker.wait", mock)
        return mock

    @pytest.fixture()
    def representation(self) -> Mock:
        return Mock(ident=(None, None, "1"), mimeType="video/mp4", height=720)

    @pytest.fixture()
    def segments(self) -> List[Mock]:
        return [
            Mock(url="init_segment"),
            Mock(url="first_segment"),
            Mock(url="second_segment"),
        ]

    @pytest.fixture()
    def mpd(self, representation) -> Mock:
        return Mock(
            publishTime=1,
            minimumUpdatePeriod=Mock(total_seconds=Mock(return_value=0)),
            periods=[
                Mock(
                    duration=Mock(total_seconds=Mock(return_value=0)),
                    adaptationSets=[
                        Mock(
                            contentProtection=None,
                            representations=[representation],
                        ),
                    ],
                ),
            ],
        )

    @pytest.fixture()
    def worker(self, mpd):
        stream = Mock(mpd=mpd, period=0, args={})
        reader = Mock(stream=stream, ident=(None, None, "1"))
        worker = DASHStreamWorker(reader)
        return worker

    def test_dynamic_reload(
        self,
        monkeypatch: pytest.MonkeyPatch,
        worker: DASHStreamWorker,
        representation: Mock,
        segments: List[Mock],
        mpd: Mock,
    ):
        mpd.dynamic = True
        mpd.type = "dynamic"
        monkeypatch.setattr("streamlink.stream.dash.MPD", lambda *args, **kwargs: mpd)

        segment_iter = worker.iter_segments()

        representation.segments.return_value = segments[:1]
        assert next(segment_iter) is segments[0]
        assert representation.segments.call_args_list == [call(init=True)]
        assert not worker._wait.is_set()

        representation.segments.reset_mock()
        representation.segments.return_value = segments[1:]
        assert [next(segment_iter), next(segment_iter)] == segments[1:]
        assert representation.segments.call_args_list == [call(), call(init=False)]
        assert not worker._wait.is_set()

    def test_static(
        self,
        worker: DASHStreamWorker,
        representation: Mock,
        segments: List[Mock],
        mpd: Mock,
    ):
        mpd.dynamic = False
        mpd.type = "static"

        representation.segments.return_value = segments
        assert list(worker.iter_segments()) == segments
        assert representation.segments.call_args_list == [call(init=True)]
        assert worker._wait.is_set()

    @pytest.mark.parametrize("duration", [
        0,
        204.32,
    ])
    def test_static_refresh_wait(
        self,
        duration: float,
        mock_wait: Mock,
        mock_time: Mock,
        worker: DASHStreamWorker,
        representation: Mock,
        segments: List[Mock],
        mpd: Mock,
    ):
        """
            Verify the fix for https://github.com/streamlink/streamlink/issues/2873
        """
        mpd.dynamic = False
        mpd.type = "static"
        mpd.periods[0].duration.total_seconds.return_value = duration

        representation.segments.return_value = segments
        assert list(worker.iter_segments()) == segments
        assert representation.segments.call_args_list == [call(init=True)]
        assert mock_wait.call_args_list == [call(5)]
        assert worker._wait.is_set()

    def test_duplicate_rep_id(self):
        representation_vid = Mock(ident=(None, None, "1"), mimeType="video/mp4", height=720)
        representation_aud = Mock(ident=(None, None, "2"), mimeType="audio/aac", lang="en")

        worker = DASHStreamWorker(Mock(stream=Mock(period=0)))
        mpd = Mock(
            dynamic=False,
            publishTime=1,
            periods=[
                Mock(
                    adaptationSets=[
                        Mock(
                            contentProtection=None,
                            representations=[representation_vid],
                        ),
                        Mock(
                            contentProtection=None,
                            representations=[representation_aud],
                        ),
                    ],
                ),
            ],
        )
        assert worker.get_representation(mpd, (None, None, "1")) is representation_vid
        assert worker.get_representation(mpd, (None, None, "2")) is representation_aud
