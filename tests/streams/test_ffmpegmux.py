from unittest.mock import ANY, patch

import pytest

from streamlink.stream.ffmpegmux import FFMPEGMuxer


@pytest.fixture
def session():
    from streamlink import Streamlink
    return Streamlink()


def test_ffmpeg_command(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        assert FFMPEGMuxer.command(session) == "ffmpeg"


def test_ffmpeg_open(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        f = FFMPEGMuxer(session, format="mpegts")
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-f', 'mpegts', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_default(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        f = FFMPEGMuxer(session)
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-f', FFMPEGMuxer.DEFAULT_OUTPUT_FORMAT, 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_format(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        session.options.set("ffmpeg-fout", "avi")
        f = FFMPEGMuxer(session, format="mpegts")
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-f', 'avi', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_copyts(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        f = FFMPEGMuxer(session, copyts=True)
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-copyts', '-f', 'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_copyts_user_override(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        session.options.set("ffmpeg-copyts", True)
        f = FFMPEGMuxer(session, copyts=False)
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-copyts', '-f', 'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_copyts_disable_session_start_at_zero(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        session.options.set("ffmpeg-start-at-zero", False)
        f = FFMPEGMuxer(session, copyts=True)
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-copyts', '-f', 'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_copyts_disable_session_start_at_zero_user_override(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        session.options.set("ffmpeg-copyts", True)
        session.options.set("ffmpeg-start-at-zero", False)
        f = FFMPEGMuxer(session, copyts=False)
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-copyts', '-f', 'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_copyts_enable_session_start_at_zero(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        session.options.set("ffmpeg-start-at-zero", True)
        f = FFMPEGMuxer(session, copyts=True)
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-copyts', '-start_at_zero', '-f', 'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_copyts_enable_session_start_at_zero_user_override(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        session.options.set("ffmpeg-copyts", True)
        session.options.set("ffmpeg-start-at-zero", True)
        f = FFMPEGMuxer(session, copyts=False)
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-copyts', '-start_at_zero', '-f', 'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_copyts_disable_start_at_zero(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        f = FFMPEGMuxer(session, copyts=True, start_at_zero=False)
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-copyts', '-f', 'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_copyts_disable_start_at_zero_user_override(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        session.options.set("ffmpeg-copyts", True)
        f = FFMPEGMuxer(session, copyts=False, start_at_zero=False)
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-copyts', '-f', 'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_copyts_enable_start_at_zero(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        f = FFMPEGMuxer(session, copyts=True, start_at_zero=True)
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-copyts', '-start_at_zero', '-f', 'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_copyts_enable_start_at_zero_user_override(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        session.options.set("ffmpeg-copyts", True)
        f = FFMPEGMuxer(session, copyts=False, start_at_zero=True)
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-copyts', '-start_at_zero', '-f', 'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_vcodec(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        f = FFMPEGMuxer(session, vcodec="avc")
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', 'avc', '-c:a', FFMPEGMuxer.DEFAULT_AUDIO_CODEC,
                                      '-f', 'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_vcodec_user_override(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        session.options.set("ffmpeg-video-transcode", "divx")
        f = FFMPEGMuxer(session, vcodec="avc")
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', 'divx', '-c:a', FFMPEGMuxer.DEFAULT_AUDIO_CODEC,
                                      '-f', 'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_acodec(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        f = FFMPEGMuxer(session, acodec="mp3")
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a', 'mp3', '-f',
                                      'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_acodec_user_override(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        session.options.set("ffmpeg-audio-transcode", "ogg")
        f = FFMPEGMuxer(session, acodec="mp3")
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a', 'ogg', '-f',
                                      'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_vcodec_acodec(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        f = FFMPEGMuxer(session, acodec="mp3", vcodec="avc")
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', 'avc', '-c:a', 'mp3', '-f', 'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_vcodec_acodec_user_override(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        session.options.set("ffmpeg-video-transcode", "divx")
        session.options.set("ffmpeg-audio-transcode", "ogg")
        f = FFMPEGMuxer(session, acodec="mp3", vcodec="avc")
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', 'divx', '-c:a', 'ogg', '-f', 'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_maps(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        f = FFMPEGMuxer(session, maps=["test", "test2"])
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-map', 'test', '-map', 'test2', '-f', 'matroska',
                                      'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_metadata_stream_audio(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        f = FFMPEGMuxer(session, metadata={"s:a:0": ["language=eng"]})
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-metadata:s:a:0', 'language=eng', '-f', 'matroska',
                                      'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)


def test_ffmpeg_open_metadata_title(session):
    with patch('streamlink.stream.ffmpegmux.which', return_value="ffmpeg"):
        f = FFMPEGMuxer(session, metadata={None: ["title=test"]})
        with patch('subprocess.Popen') as popen:
            f.open()
            popen.assert_called_with(['ffmpeg', '-nostats', '-y', '-c:v', FFMPEGMuxer.DEFAULT_VIDEO_CODEC, '-c:a',
                                      FFMPEGMuxer.DEFAULT_AUDIO_CODEC, '-metadata', 'title=test', '-f', 'matroska', 'pipe:1'],
                                     stderr=ANY,
                                     stdout=ANY,
                                     stdin=ANY)
