# -*- coding: utf-8 -*-
from streamlink.utils import get_filesystem_encoding
from streamlink_cli.output import PlayerOutput
from tests import posix_only, windows_only, py2_only, py3_only
from tests.mock import patch, ANY

UNICODE_TITLE = u"기타치는소율 with UL섬 "


@posix_only
@patch('subprocess.Popen')
def test_output_mpv_unicode_title_posix(popen):
    po = PlayerOutput("mpv", title=UNICODE_TITLE)
    popen().poll.side_effect = lambda: None
    po.open()
    popen.assert_called_with(['mpv', u"--title=" + UNICODE_TITLE, '-'],
                             bufsize=ANY, stderr=ANY, stdout=ANY, stdin=ANY)


@posix_only
@patch('subprocess.Popen')
def test_output_vlc_unicode_title_posix(popen):
    po = PlayerOutput("vlc", title=UNICODE_TITLE)
    popen().poll.side_effect = lambda: None
    po.open()
    popen.assert_called_with(['vlc', u'--input-title-format', UNICODE_TITLE, '-'],
                             bufsize=ANY, stderr=ANY, stdout=ANY, stdin=ANY)


@py2_only
@windows_only
@patch('subprocess.Popen')
def test_output_mpv_unicode_title_windows_py2(popen):
    po = PlayerOutput("mpv.exe", title=UNICODE_TITLE)
    popen().poll.side_effect = lambda: None
    po.open()
    popen.assert_called_with("mpv.exe \"--title=" + UNICODE_TITLE.encode(get_filesystem_encoding()) + "\" -",
                             bufsize=ANY, stderr=ANY, stdout=ANY, stdin=ANY)


@py2_only
@windows_only
@patch('subprocess.Popen')
def test_output_vlc_unicode_title_windows_py2(popen):
    po = PlayerOutput("vlc.exe", title=UNICODE_TITLE)
    popen().poll.side_effect = lambda: None
    po.open()
    popen.assert_called_with("vlc.exe --input-title-format \"" + UNICODE_TITLE.encode(get_filesystem_encoding()) + "\" -",
                             bufsize=ANY, stderr=ANY, stdout=ANY, stdin=ANY)


@py3_only
@windows_only
@patch('subprocess.Popen')
def test_output_mpv_unicode_title_windows_py3(popen):
    po = PlayerOutput("mpv.exe", title=UNICODE_TITLE)
    popen().poll.side_effect = lambda: None
    po.open()
    popen.assert_called_with("mpv.exe \"--title=" + UNICODE_TITLE + "\" -",
                             bufsize=ANY, stderr=ANY, stdout=ANY, stdin=ANY)


@py3_only
@windows_only
@patch('subprocess.Popen')
def test_output_vlc_unicode_title_windows_py3(popen):
    po = PlayerOutput("vlc.exe", title=UNICODE_TITLE)
    popen().poll.side_effect = lambda: None
    po.open()
    popen.assert_called_with("vlc.exe --input-title-format \"" + UNICODE_TITLE + "\" -",
                             bufsize=ANY, stderr=ANY, stdout=ANY, stdin=ANY)
