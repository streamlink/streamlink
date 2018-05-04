import sys

from streamlink.stream.dash import DASHStreamWorker

if sys.version_info[0:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

try:
    from unittest.mock import MagicMock, patch, ANY, Mock, call
except ImportError:
    from mock import MagicMock, patch, ANY, Mock, call

from streamlink import PluginError
from streamlink.stream import *


class TestDASHStream(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_video_only(self, mpdClass):
        mpd = mpdClass.return_value = Mock(periods=[
            Mock(adaptionSets=[
                Mock(contentProtection=None,
                     representations=[
                         Mock(id=1, mimeType="video/mp4", height=720),
                         Mock(id=2, mimeType="video/mp4", height=1080)
                     ])
            ])
        ])

        streams = DASHStream.parse_manifest(self.session, "http://test.bar/foo.mpd")
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        self.assertSequenceEqual(
            sorted(list(streams.keys())),
            sorted(["720p", "1080p"])
        )

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_audio_only(self, mpdClass):
        mpd = mpdClass.return_value = Mock(periods=[
            Mock(adaptionSets=[
                Mock(contentProtection=None,
                     representations=[
                         Mock(id=1, mimeType="audio/mp4", bandwidth=128.0),
                         Mock(id=2, mimeType="audio/mp4", bandwidth=256.0)
                     ])
            ])
        ])

        streams = DASHStream.parse_manifest(self.session, "http://test.bar/foo.mpd")
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        self.assertSequenceEqual(
            sorted(list(streams.keys())),
            sorted(["a128k", "a256k"])
        )

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_audio_single(self, mpdClass):
        mpd = mpdClass.return_value = Mock(periods=[
            Mock(adaptionSets=[
                Mock(contentProtection=None,
                     representations=[
                         Mock(id=1, mimeType="video/mp4", height=720),
                         Mock(id=2, mimeType="video/mp4", height=1080),
                         Mock(id=3, mimeType="audio/aac", bandwidth=128.0)
                     ])
            ])
        ])

        streams = DASHStream.parse_manifest(self.session, "http://test.bar/foo.mpd")
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        self.assertSequenceEqual(
            sorted(list(streams.keys())),
            sorted(["720p", "1080p"])
        )

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_audio_multi(self, mpdClass):
        mpd = mpdClass.return_value = Mock(periods=[
            Mock(adaptionSets=[
                Mock(contentProtection=None,
                     representations=[
                         Mock(id=1, mimeType="video/mp4", height=720),
                         Mock(id=2, mimeType="video/mp4", height=1080),
                         Mock(id=3, mimeType="audio/aac", bandwidth=128.0),
                         Mock(id=4, mimeType="audio/aac", bandwidth=256.0)
                     ])
            ])
        ])

        streams = DASHStream.parse_manifest(self.session, "http://test.bar/foo.mpd")
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

        self.assertSequenceEqual(
            sorted(list(streams.keys())),
            sorted(["720p+a128k", "1080p+a128k", "720p+a256k", "1080p+a256k"])
        )

    @patch('streamlink.stream.dash.MPD')
    def test_parse_manifest_drm(self, mpdClass):
        mpd = mpdClass.return_value = Mock(periods=[Mock(adaptionSets=[Mock(contentProtection="DRM")])])

        self.assertRaises(PluginError,
                          DASHStream.parse_manifest,
                          self.session, "http://test.bar/foo.mpd")
        mpdClass.assert_called_with(ANY, base_url="http://test.bar", url="http://test.bar/foo.mpd")

    @patch('streamlink.stream.dash.DASHStreamReader')
    @patch('streamlink.stream.dash.FFMPEGMuxer')
    def test_stream_open_video_only(self, muxer, reader):
        stream = DASHStream(self.session, Mock(), Mock(id=1))
        open_reader = reader.return_value = Mock()

        stream.open()

        reader.assert_called_with(stream, 1)
        open_reader.open.assert_called_with()
        muxer.assert_not_called()

    @patch('streamlink.stream.dash.DASHStreamReader')
    @patch('streamlink.stream.dash.FFMPEGMuxer')
    def test_stream_open_video_audio(self, muxer, reader):
        stream = DASHStream(self.session, Mock(), Mock(id=1), Mock(id=2))
        open_reader = reader.return_value = Mock()

        stream.open()

        self.assertSequenceEqual(reader.mock_calls, [call(stream, 1),
                                                     call().open(),
                                                     call(stream, 2),
                                                     call().open()])
        self.assertSequenceEqual(muxer.mock_calls, [call(self.session, open_reader, open_reader),
                                                    call().open()])


class TestDASHStreamWorker(unittest.TestCase):
    @patch('streamlink.stream.dash.MPD')
    def test_dynamic_reload(self, mpdClass):
        reader = MagicMock()
        worker = DASHStreamWorker(reader)
        reader.representation_id = 1

        representation = Mock(id=1, mimeType="video/mp4", height=720)
        segments = [Mock(url="init_segment"), Mock(url="first_segment"), Mock(url="second_segment")]
        representation.segments.return_value = [segments[0]]
        mpdClass.return_value = worker.mpd = Mock(dynamic=True,
                                                  periods=[
                                                      Mock(adaptionSets=[
                                                          Mock(contentProtection=None,
                                                               representations=[
                                                                   representation
                                                               ])
                                                      ])
                                                  ])
        worker.mpd.type = "dynamic"
        worker.mpd.minimumUpdatePeriod.total_seconds.return_value = 0
        segment_iter = worker.iter_segments()

        representation.segments.return_value = segments[:1]
        self.assertEqual(next(segment_iter), segments[0])
        representation.segments.assert_called_with(init=True)

        representation.segments.return_value = segments[1:]
        self.assertSequenceEqual([next(segment_iter), next(segment_iter)], segments[1:])
        representation.segments.assert_called_with(init=False)

    def test_static(self):
        reader = MagicMock()
        worker = DASHStreamWorker(reader)
        reader.representation_id = 1

        representation = Mock(id=1, mimeType="video/mp4", height=720)
        segments = [Mock(url="init_segment"), Mock(url="first_segment"), Mock(url="second_segment")]
        representation.segments.return_value = [segments[0]]
        worker.mpd = Mock(dynamic=True,
                          periods=[
                              Mock(adaptionSets=[
                                  Mock(contentProtection=None,
                                       representations=[
                                           representation
                                       ])
                              ])
                          ])
        worker.mpd.type = "static"
        worker.mpd.minimumUpdatePeriod.total_seconds.return_value = 0

        representation.segments.return_value = segments
        self.assertSequenceEqual(list(worker.iter_segments()), segments)
        representation.segments.assert_called_with(init=True)


if __name__ == "__main__":
    unittest.main()
