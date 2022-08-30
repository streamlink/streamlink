from unittest.mock import ANY, Mock, patch

from streamlink_cli.output import PlayerOutput
from tests import posix_only, windows_only

UNICODE_TITLE = "기타치는소율 with UL섬 "


@posix_only
@patch("streamlink_cli.output.sleep", Mock())
@patch("subprocess.Popen")
def test_output_mpv_unicode_title_posix(popen):
    po = PlayerOutput("mpv", title=UNICODE_TITLE)
    popen().poll.side_effect = lambda: None
    po.open()
    popen.assert_called_with(["mpv", f"--force-media-title={UNICODE_TITLE}", "-"],
                             bufsize=ANY, stderr=ANY, stdout=ANY, stdin=ANY)


@posix_only
@patch("streamlink_cli.output.sleep", Mock())
@patch("subprocess.Popen")
def test_output_vlc_unicode_title_posix(popen):
    po = PlayerOutput("vlc", title=UNICODE_TITLE)
    popen().poll.side_effect = lambda: None
    po.open()
    popen.assert_called_with(["vlc", "--input-title-format", UNICODE_TITLE, "-"],
                             bufsize=ANY, stderr=ANY, stdout=ANY, stdin=ANY)


@windows_only
@patch("streamlink_cli.output.sleep", Mock())
@patch("subprocess.Popen")
def test_output_mpv_unicode_title_windows_py3(popen):
    po = PlayerOutput("mpv.exe", title=UNICODE_TITLE)
    popen().poll.side_effect = lambda: None
    po.open()
    popen.assert_called_with(f"mpv.exe \"--force-media-title={UNICODE_TITLE}\" -",
                             bufsize=ANY, stderr=ANY, stdout=ANY, stdin=ANY)


@windows_only
@patch("streamlink_cli.output.sleep", Mock())
@patch("subprocess.Popen")
def test_output_vlc_unicode_title_windows_py3(popen):
    po = PlayerOutput("vlc.exe", title=UNICODE_TITLE)
    popen().poll.side_effect = lambda: None
    po.open()
    popen.assert_called_with(f"vlc.exe --input-title-format \"{UNICODE_TITLE}\" -",
                             bufsize=ANY, stderr=ANY, stdout=ANY, stdin=ANY)


@posix_only
def test_output_args_posix():
    po_none = PlayerOutput("foo")
    assert po_none._create_arguments() == ["foo", "-"]

    po_implicit = PlayerOutput("foo", args="--bar")
    assert po_implicit._create_arguments() == ["foo", "--bar", "-"]

    po_explicit = PlayerOutput("foo", args="--bar {playerinput}")
    assert po_explicit._create_arguments() == ["foo", "--bar", "-"]

    po_fallback = PlayerOutput("foo", args="--bar {filename}")
    assert po_fallback._create_arguments() == ["foo", "--bar", "-"]

    po_fallback = PlayerOutput("foo", args="--bar {playerinput} {filename}")
    assert po_fallback._create_arguments() == ["foo", "--bar", "-", "-"]

    po_fallback = PlayerOutput("foo", args="--bar {qux}")
    assert po_fallback._create_arguments() == ["foo", "--bar", "{qux}", "-"]


@windows_only
def test_output_args_windows():
    po_none = PlayerOutput("foo")
    assert po_none._create_arguments() == "foo -"

    po_implicit = PlayerOutput("foo", args="--bar")
    assert po_implicit._create_arguments() == "foo --bar -"

    po_explicit = PlayerOutput("foo", args="--bar {playerinput}")
    assert po_explicit._create_arguments() == "foo --bar -"

    po_fallback = PlayerOutput("foo", args="--bar {filename}")
    assert po_fallback._create_arguments() == "foo --bar -"

    po_fallback = PlayerOutput("foo", args="--bar {playerinput} {filename}")
    assert po_fallback._create_arguments() == "foo --bar - -"

    po_fallback = PlayerOutput("foo", args="--bar {qux}")
    assert po_fallback._create_arguments() == "foo --bar {qux} -"
