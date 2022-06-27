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

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_video_only(self, mpdClass):
        mpdClass.return_value = Mock(periods=[
            Mock(adaptationSets=[
                Mock(contentProtection=None,
                     representations=[
                         Mock(id=1, mimeType="video/mp4", height=720),
                         Mock(id=2, mimeType="video/mp4", height=1080)
                     ])
            ])
        ])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        self.assertSequenceEqual(
            sorted(list(streams.keys())),
            sorted(["720p", "1080p"])
        )

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_audio_only(self, mpdClass):
        mpdClass.return_value = Mock(periods=[
            Mock(adaptationSets=[
                Mock(contentProtection=None,
                     representations=[
                         Mock(id=1, mimeType="audio/mp4", bandwidth=128.0, lang='en'),
                         Mock(id=2, mimeType="audio/mp4", bandwidth=256.0, lang='en')
                     ])
            ])
        ])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        self.assertSequenceEqual(
            sorted(list(streams.keys())),
            sorted(["a128k", "a256k"])
        )

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_audio_single(self, mpdClass):
        mpdClass.return_value = Mock(periods=[
            Mock(adaptationSets=[
                Mock(contentProtection=None,
                     representations=[
                         Mock(id=1, mimeType="video/mp4", height=720),
                         Mock(id=2, mimeType="video/mp4", height=1080),
                         Mock(id=3, mimeType="audio/aac", bandwidth=128.0, lang='en')
                     ])
            ])
        ])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        self.assertSequenceEqual(
            sorted(list(streams.keys())),
            sorted(["720p", "1080p"])
        )

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_audio_multi(self, mpdClass):
        mpdClass.return_value = Mock(periods=[
            Mock(adaptationSets=[
                Mock(contentProtection=None,
                     representations=[
                         Mock(id=1, mimeType="video/mp4", height=720),
                         Mock(id=2, mimeType="video/mp4", height=1080),
                         Mock(id=3, mimeType="audio/aac", bandwidth=128.0, lang='en'),
                         Mock(id=4, mimeType="audio/aac", bandwidth=256.0, lang='en')
                     ])
            ])
        ])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        self.assertSequenceEqual(
            sorted(list(streams.keys())),
            sorted(["720p+a128k", "1080p+a128k", "720p+a256k", "1080p+a256k"])
        )

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_audio_multi_lang(self, mpdClass):
        mpdClass.return_value = Mock(periods=[
            Mock(adaptationSets=[
                Mock(contentProtection=None,
                     representations=[
                         Mock(id=1, mimeType="video/mp4", height=720),
                         Mock(id=2, mimeType="video/mp4", height=1080),
                         Mock(id=3, mimeType="audio/aac", bandwidth=128.0, lang='en'),
                         Mock(id=4, mimeType="audio/aac", bandwidth=128.0, lang='es')
                     ])
            ])
        ])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        self.assertSequenceEqual(
            sorted(list(streams.keys())),
            sorted(["720p", "1080p"])
        )

        self.assertEqual(streams["720p"].audio_representation.lang, "en")
        self.assertEqual(streams["1080p"].audio_representation.lang, "en")

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_audio_multi_lang_alpha3(self, mpdClass):
        mpdClass.return_value = Mock(periods=[
            Mock(adaptationSets=[
                Mock(contentProtection=None,
                     representations=[
                         Mock(id=1, mimeType="video/mp4", height=720),
                         Mock(id=2, mimeType="video/mp4", height=1080),
                         Mock(id=3, mimeType="audio/aac", bandwidth=128.0, lang='eng'),
                         Mock(id=4, mimeType="audio/aac", bandwidth=128.0, lang='spa')
                     ])
            ])
        ])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        self.assertSequenceEqual(
            sorted(list(streams.keys())),
            sorted(["720p", "1080p"])
        )

        self.assertEqual(streams["720p"].audio_representation.lang, "eng")
        self.assertEqual(streams["1080p"].audio_representation.lang, "eng")

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_audio_invalid_lang(self, mpdClass):
        mpdClass.return_value = Mock(periods=[
            Mock(adaptationSets=[
                Mock(contentProtection=None,
                     representations=[
                         Mock(id=1, mimeType="video/mp4", height=720),
                         Mock(id=2, mimeType="video/mp4", height=1080),
                         Mock(id=3, mimeType="audio/aac", bandwidth=128.0, lang='en_no_voice'),
                     ])
            ])
        ])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        self.assertSequenceEqual(
            sorted(list(streams.keys())),
            sorted(["720p", "1080p"])
        )

        self.assertEqual(streams["720p"].audio_representation.lang, "en_no_voice")
        self.assertEqual(streams["1080p"].audio_representation.lang, "en_no_voice")

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_audio_multi_lang_locale(self, mpdClass):
        self.session.localization.language.alpha2 = "es"
        self.session.localization.explicit = True

        mpdClass.return_value = Mock(periods=[
            Mock(adaptationSets=[
                Mock(contentProtection=None,
                     representations=[
                         Mock(id=1, mimeType="video/mp4", height=720),
                         Mock(id=2, mimeType="video/mp4", height=1080),
                         Mock(id=3, mimeType="audio/aac", bandwidth=128.0, lang='en'),
                         Mock(id=4, mimeType="audio/aac", bandwidth=128.0, lang='es')
                     ])
            ])
        ])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        self.assertSequenceEqual(
            sorted(list(streams.keys())),
            sorted(["720p", "1080p"])
        )

        self.assertEqual(streams["720p"].audio_representation.lang, "es")
        self.assertEqual(streams["1080p"].audio_representation.lang, "es")

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_drm(self, mpdClass):
        mpdClass.return_value = Mock(periods=[Mock(adaptationSets=[Mock(contentProtection="DRM")])])

        self.assertRaises(PluginError,
                          DASHStream.parse_manifest,
                          self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

    def test_parse_manifest_string(self):
        with text("dash/test_9.mpd") as mpd_txt:
            test_manifest = mpd_txt.read()

        streams = DASHStream.parse_manifest(self.session, test_manifest)
        self.assertSequenceEqual(list(streams.keys()), ['2500k'])

    @patch('streamlink.stream.dash.DASHStreamReader')
    @patch('streamlink.stream.dash.FFMPEGMuxer')
    def test_stream_open_video_only(self, muxer, reader):
        stream = DASHStream(self.session, Mock(), Mock(id=1, mimeType="video/mp4"))
        open_reader = reader.return_value = Mock()

        stream.open()

        reader.assert_called_with(stream, 1, "video/mp4")
        open_reader.open.assert_called_with()
        muxer.assert_not_called()

    @patch('streamlink.stream.dash.DASHStreamReader')
    @patch('streamlink.stream.dash.FFMPEGMuxer')
    def test_stream_open_video_audio(self, muxer, reader):
        stream = DASHStream(self.session, Mock(), Mock(id=1, mimeType="video/mp4"), Mock(id=2, mimeType="audio/mp3", lang='en'))
        open_reader = reader.return_value = Mock()

        stream.open()

        self.assertSequenceEqual(reader.mock_calls, [call(stream, 1, "video/mp4"),
                                                     call().open(),
                                                     call(stream, 2, "audio/mp3"),
                                                     call().open()])
        self.assertSequenceEqual(muxer.mock_calls, [call(self.session, open_reader, open_reader, copyts=True),
                                                    call().open()])

    @patch('streamlink.stream.dash.MPD')
    def test_segments_number_time(self, mpdClass):
        with xml("dash/test_9.mpd") as mpd_xml:
            mpdClass.return_value = MPD(mpd_xml, base_url="http://test.bar", url="http://test.bar/foo.mpd")

            streams = DASHStream.parse_manifest(self.session, self.test_url)
            mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

            self.assertSequenceEqual(list(streams.keys()), ['2500k'])

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_with_duplicated_resolutions(self, mpdClass):
        """
            Verify the fix for https://github.com/streamlink/streamlink/issues/3365
        """
        mpdClass.return_value = Mock(periods=[
            Mock(adaptationSets=[
                Mock(contentProtection=None,
                     representations=[
                         Mock(id=1, mimeType="video/mp4", height=1080, bandwidth=128.0),
                         Mock(id=2, mimeType="video/mp4", height=1080, bandwidth=64.0),
                         Mock(id=3, mimeType="video/mp4", height=1080, bandwidth=32.0),
                         Mock(id=4, mimeType="video/mp4", height=720),
                     ])
            ])
        ])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        self.assertSequenceEqual(
            sorted(list(streams.keys())),
            sorted(["720p", "1080p", "1080p_alt", "1080p_alt2"])
        )

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_with_duplicated_resolutions_sorted_bandwidth(self, mpdClass):
        """
            Verify the fix for https://github.com/streamlink/streamlink/issues/4217
        """
        mpdClass.return_value = Mock(periods=[
            Mock(adaptationSets=[
                Mock(contentProtection=None,
                     representations=[
                         Mock(id=1, mimeType="video/mp4", height=1080, bandwidth=64.0),
                         Mock(id=2, mimeType="video/mp4", height=1080, bandwidth=128.0),
                         Mock(id=3, mimeType="video/mp4", height=1080, bandwidth=32.0),
                     ])
            ])
        ])

        streams = DASHStream.parse_manifest(self.session, self.test_url)
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        self.assertEqual(streams["1080p"].video_representation.bandwidth, 128.0)
        self.assertEqual(streams["1080p_alt"].video_representation.bandwidth, 64.0)
        self.assertEqual(streams["1080p_alt2"].video_representation.bandwidth, 32.0)


class TestDASHStreamWorker:
    @pytest.fixture
    def mock_time(self, monkeypatch: pytest.MonkeyPatch) -> Mock:
        mock = Mock(return_value=1)
        monkeypatch.setattr("streamlink.stream.dash.time", mock)
        return mock

    @pytest.fixture(autouse=True)
    def mock_wait(self, monkeypatch: pytest.MonkeyPatch) -> Mock:
        mock = Mock(return_value=True)
        monkeypatch.setattr("streamlink.stream.dash.DASHStreamWorker.wait", mock)
        return mock

    @pytest.fixture
    def representation(self) -> Mock:
        return Mock(id=1, mimeType="video/mp4", height=720)

    @pytest.fixture
    def segments(self) -> List[Mock]:
        return [
            Mock(url="init_segment"),
            Mock(url="first_segment"),
            Mock(url="second_segment"),
        ]

    @pytest.fixture
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

    @pytest.fixture
    def worker(self, mpd):
        reader = MagicMock(representation_id=1, mime_type="video/mp4")
        worker = DASHStreamWorker(reader)
        worker.mpd = mpd
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
        representation_vid = Mock(id=1, mimeType="video/mp4", height=720)
        representation_aud = Mock(id=1, mimeType="audio/aac", lang="en")

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

        assert DASHStreamWorker.get_representation(mpd, 1, "video/mp4") is representation_vid
        assert DASHStreamWorker.get_representation(mpd, 1, "audio/aac") is representation_aud
