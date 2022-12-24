import argparse
from typing import Type
from unittest.mock import Mock, call, patch

import pytest

from streamlink_cli.main import CLIExit, handle_stream, handle_url
from tests.cli import FakePlugin


@pytest.fixture(autouse=True)
def args(request: pytest.FixtureRequest):
    _args = dict(
        stream_url=True,
        url="mock://fake",
        stream=[],
        default_stream=[],
        stream_types=None,
        stream_sorting_excludes=None,
        json=False,
        subprocess_cmdline=False,
        retry_max=0,
        retry_streams=0,
    )
    _args.update(**getattr(request, "param", {}))
    with patch("streamlink_cli.main.args", argparse.Namespace(**_args)) as mock_args:
        yield mock_args


@pytest.fixture
def console():
    with patch("streamlink_cli.main.console") as mock_console:
        yield mock_console


@pytest.fixture
def stream():
    return Mock()


@pytest.fixture
def streams(stream: Mock):
    return dict(worst=Mock(), best=stream)


@pytest.fixture
def fakeplugin(streams: dict):
    class _FakePlugin(FakePlugin):
        __module__ = FakePlugin.__module__
        _streams = streams

    return _FakePlugin


@pytest.fixture
def plugin(args: argparse.Namespace, fakeplugin: Type[FakePlugin]):
    return fakeplugin(Mock(), args.url)


@pytest.fixture(autouse=True)
def _resolve_url(fakeplugin: Type[FakePlugin]):
    with patch("streamlink_cli.main.streamlink", resolve_url=Mock(return_value=("fake", fakeplugin, ""))), \
         patch("streamlink_cli.main.setup_plugin_options"):
        yield


class TestNoStreamSelection:
    """Tests the stream-URL / JSON output when not selecting a specific stream"""

    def test_stream_url(self, args: argparse.Namespace, console: Mock, stream: Mock):
        handle_url()
        assert console.msg.call_args_list == [call(stream.to_manifest_url())]
        assert not console.msg_json.called

    @pytest.mark.parametrize("args", [{"json": True}], indirect=["args"])
    def test_json(self, args: argparse.Namespace, console: Mock, streams: dict):
        handle_url()
        assert not console.msg.called
        assert console.msg_json.call_args_list == [call(
            plugin="fake",
            metadata=dict(
                id="test-id-1234-5678",
                author="Tѥst Āuƭhǿr",
                category=None,
                title="Test Title",
            ),
            streams=streams,
        )]

    def test_error(self, args: argparse.Namespace, console: Mock, stream: Mock):
        stream.to_manifest_url.side_effect = TypeError()
        with pytest.raises(CLIExit) as cm:
            handle_url()
        assert str(cm.value) == "The stream specified cannot be translated to a URL"
        assert not console.msg.called
        assert not console.msg_json.called


class TestStreamSelection:
    """Tests the stream-URL / JSON output of a specific stream selection"""

    def test_stream_url(self, args: argparse.Namespace, console: Mock, stream: Mock, streams: dict, plugin: FakePlugin):
        handle_stream(plugin, streams, "best")
        assert console.msg.call_args_list == [call(stream.to_url())]
        assert not console.msg_json.called

    @pytest.mark.parametrize("args", [{"json": True}], indirect=["args"])
    def test_json(self, args: argparse.Namespace, console: Mock, stream: Mock, streams: dict, plugin: FakePlugin):
        handle_stream(plugin, streams, "best")
        assert not console.msg.called
        assert console.msg_json.call_args_list == [call(
            stream,
            metadata=dict(
                id="test-id-1234-5678",
                author="Tѥst Āuƭhǿr",
                category=None,
                title="Test Title",
            ),
        )]

    def test_error(self, args: argparse.Namespace, console: Mock, stream: Mock, streams: dict, plugin: FakePlugin):
        stream.to_url.side_effect = TypeError()
        with pytest.raises(CLIExit) as cm:
            handle_stream(plugin, streams, "best")
        assert str(cm.value) == "The stream specified cannot be translated to a URL"
        assert not console.msg.called
        assert not console.msg_json.called
