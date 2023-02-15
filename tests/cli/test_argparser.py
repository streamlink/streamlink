from argparse import ArgumentParser, Namespace
from typing import Any, List
from unittest.mock import Mock

import pytest

from streamlink.session import Streamlink
from streamlink_cli.argparser import build_parser, setup_session_options
from streamlink_cli.main import main as streamlink_cli_main


@pytest.fixture(scope="module")
def parser():
    return build_parser()


@pytest.fixture()
def session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("streamlink.session.Streamlink.load_builtin_plugins", lambda _: None)
    return Streamlink()


@pytest.mark.filterwarnings("ignore")
@pytest.mark.parametrize(("argv", "option", "expected"), [
    pytest.param(
        ["--locale", "xx_XX"],
        "locale",
        "xx_XX",
        id="Arg+value without mapper",
    ),
    pytest.param(
        ["--http-query-param", "foo=bar", "--http-query-param", "baz=qux"],
        "http-query-params",
        {"foo": "bar", "baz": "qux"},
        id="Arg+value with dict mapper",
    ),
    pytest.param(
        ["--http-no-ssl-verify"],
        "http-ssl-verify",
        False,
        id="Arg with bool mapper",
    ),
    pytest.param(
        ["--http-ssl-cert-crt-key", "foo.crt", "bar.key"],
        "http-ssl-cert",
        ("foo.crt", "bar.key"),
        id="Arg+value with tuple mapper",
    ),
    pytest.param(
        ["--hls-timeout", "123"],
        "stream-timeout",
        123.0,
        id="Deprecated argument",
    ),
    pytest.param(
        ["--hls-timeout", "123", "--stream-timeout", "456"],
        "stream-timeout",
        456.0,
        id="Deprecated argument with override",
    ),
])
def test_setup_session_options(parser: ArgumentParser, session: Streamlink, argv: List, option: str, expected: Any):
    args = parser.parse_args(argv)
    setup_session_options(session, args)
    assert session.get_option(option) == expected


def test_cli_main_setup_session_options(monkeypatch: pytest.MonkeyPatch, parser: ArgumentParser, session: Streamlink):
    class StopTest(Exception):
        pass

    mock_setup_session_options = Mock()

    monkeypatch.setattr("sys.argv", [])
    monkeypatch.setattr("streamlink_cli.main.CONFIG_FILES", [])
    monkeypatch.setattr("streamlink_cli.main.logger", Mock())
    monkeypatch.setattr("streamlink_cli.main.streamlink", session)
    monkeypatch.setattr("streamlink_cli.main.build_parser", Mock(return_value=parser))
    monkeypatch.setattr("streamlink_cli.main.setup_streamlink", Mock())
    monkeypatch.setattr("streamlink_cli.main.setup_plugins", Mock())
    monkeypatch.setattr("streamlink_cli.main.log_root_warning", Mock())
    monkeypatch.setattr("streamlink_cli.main.log_current_versions", Mock())
    monkeypatch.setattr("streamlink_cli.main.log_current_arguments", Mock())
    monkeypatch.setattr("streamlink_cli.main.setup_session_options", mock_setup_session_options)
    monkeypatch.setattr("streamlink_cli.main.setup_signals", Mock(side_effect=StopTest))

    with pytest.raises(StopTest):
        streamlink_cli_main()

    assert mock_setup_session_options.call_count == 1, \
        "Has called setup_session_options() before setting up signals and running actual CLI code"
    assert mock_setup_session_options.call_args_list[0][0][0] is session
    assert isinstance(mock_setup_session_options.call_args_list[0][0][1], Namespace)
