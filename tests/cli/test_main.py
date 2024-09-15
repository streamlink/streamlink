import re
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

from streamlink_cli.compat import stdout
from streamlink_cli.exceptions import StreamlinkCLIError
from streamlink_cli.main import (
    Formatter,
    create_output,
)
from streamlink_cli.output import FileOutput, PlayerOutput


# TODO: rewrite the entire mess


# TODO: don't use Mock() for mocking args, use a custom argparse.Namespace instead
class TestCLIMainCreateOutput(unittest.TestCase):
    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.console", Mock())
    @patch("streamlink_cli.main.DEFAULT_STREAM_METADATA", {"title": "bar"})
    def test_create_output_no_file_output_options(self, args: Mock):
        formatter = Formatter({
            "author": lambda: "foo",
        })
        args.output = None
        args.stdout = None
        args.record = None
        args.record_and_pipe = None
        args.player_fifo = False
        args.player_http = False
        args.title = None
        args.url = "URL"
        args.player = Path("mpv")
        args.player_args = ""
        args.player_env = None

        output = create_output(formatter)
        assert type(output) is PlayerOutput
        assert output.playerargs.title == "URL"
        assert output.env == {}

        args.title = "{author} - {title}"
        output = create_output(formatter)
        assert type(output) is PlayerOutput
        assert output.playerargs.title == "foo - bar"

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.check_file_output")
    def test_create_output_file_output(self, mock_check_file_output: Mock, args: Mock):
        formatter = Formatter({})
        mock_check_file_output.side_effect = lambda path, force: FileOutput(path)
        args.output = "foo"
        args.stdout = None
        args.record = None
        args.record_and_pipe = None
        args.force = False
        args.fs_safe_rules = None

        output = create_output(formatter)
        assert mock_check_file_output.call_args_list == [call(Path("foo"), False)]
        assert type(output) is FileOutput
        assert output.filename == Path("foo")
        assert output.fd is None
        assert output.record is None

    @patch("streamlink_cli.main.args")
    def test_create_output_stdout(self, args: Mock):
        formatter = Formatter({})
        args.output = None
        args.stdout = True
        args.record = None
        args.record_and_pipe = None

        output = create_output(formatter)
        assert type(output) is FileOutput
        assert output.filename is None
        assert output.fd is stdout
        assert output.record is None

        args.output = "-"
        args.stdout = False
        output = create_output(formatter)
        assert type(output) is FileOutput
        assert output.filename is None
        assert output.fd is stdout
        assert output.record is None

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.check_file_output")
    def test_create_output_record_and_pipe(self, mock_check_file_output: Mock, args: Mock):
        formatter = Formatter({})
        mock_check_file_output.side_effect = lambda path, force: FileOutput(path)
        args.output = None
        args.stdout = None
        args.record_and_pipe = "foo"
        args.force = False
        args.fs_safe_rules = None

        output = create_output(formatter)
        assert mock_check_file_output.call_args_list == [call(Path("foo"), False)]
        assert type(output) is FileOutput
        assert output.filename is None
        assert output.fd is stdout
        assert type(output.record) is FileOutput
        assert output.record.filename == Path("foo")
        assert output.record.fd is None
        assert output.record.record is None

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.check_file_output")
    @patch("streamlink_cli.main.DEFAULT_STREAM_METADATA", {"title": "bar"})
    def test_create_output_record(self, mock_check_file_output: Mock, args: Mock):
        formatter = Formatter({
            "author": lambda: "foo",
        })
        mock_check_file_output.side_effect = lambda path, force: FileOutput(path)
        args.output = None
        args.stdout = None
        args.record = "foo"
        args.record_and_pipe = None
        args.force = False
        args.fs_safe_rules = None
        args.title = None
        args.url = "URL"
        args.player = Path("mpv")
        args.player_args = ""
        args.player_env = [("VAR1", "abc"), ("VAR2", "def")]
        args.player_fifo = None
        args.player_http = None

        output = create_output(formatter)
        assert type(output) is PlayerOutput
        assert output.playerargs.title == "URL"
        assert output.env == {"VAR1": "abc", "VAR2": "def"}
        assert type(output.record) is FileOutput
        assert output.record.filename == Path("foo")
        assert output.record.fd is None
        assert output.record.record is None

        args.title = "{author} - {title}"
        output = create_output(formatter)
        assert type(output) is PlayerOutput
        assert output.playerargs.title == "foo - bar"
        assert type(output.record) is FileOutput
        assert output.record.filename == Path("foo")
        assert output.record.fd is None
        assert output.record.record is None

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.DEFAULT_STREAM_METADATA", {"title": "bar"})
    def test_create_output_record_stdout(self, args: Mock):
        formatter = Formatter({
            "author": lambda: "foo",
        })
        args.output = None
        args.stdout = None
        args.record = "-"
        args.record_and_pipe = None
        args.force = False
        args.fs_safe_rules = None
        args.title = "{author} - {title}"
        args.url = "URL"
        args.player = Path("mpv")
        args.player_args = ""
        args.player_env = [("VAR1", "abc"), ("VAR2", "def")]
        args.player_fifo = None
        args.player_http = None

        output = create_output(formatter)
        assert type(output) is PlayerOutput
        assert output.playerargs.title == "foo - bar"
        assert output.env == {"VAR1": "abc", "VAR2": "def"}
        assert type(output.record) is FileOutput
        assert output.record.filename is None
        assert output.record.fd is stdout
        assert output.record.record is None

    @patch("streamlink_cli.main.args")
    def test_create_output_record_and_other_file_output(self, args: Mock):
        formatter = Formatter({})
        args.output = None
        args.stdout = True
        args.record_and_pipe = True
        with pytest.raises(StreamlinkCLIError) as excinfo:
            create_output(formatter)
        assert str(excinfo.value) == "Cannot use record options with other file output options."
        assert excinfo.value.code == 1

    @patch("streamlink_cli.main.args")
    def test_create_output_no_default_player(self, args: Mock):
        formatter = Formatter({})
        args.output = None
        args.stdout = False
        args.record_and_pipe = False
        args.player = None
        with pytest.raises(StreamlinkCLIError) as excinfo:
            create_output(formatter)
        assert re.search(r"^The default player \(\w+\) does not seem to be installed\.", str(excinfo.value))
        assert excinfo.value.code == 1
