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


@pytest.mark.filterwarnings("ignore")
@pytest.mark.parametrize(("argv", "option", "expected"), [
    pytest.param(
        ["--locale", "xx_XX"],
        "locale",
        "xx_XX",
        id="Arg+value without mapper",
    ),
    pytest.param(
        ["--http-disable-dh"],
        "http-disable-dh",
        True,
        id="Arg with action=store_true",
    ),
    pytest.param(
        ["--http-no-ssl-verify"],
        "http-ssl-verify",
        False,
        id="Arg with action=store_false",
    ),
    pytest.param(
        ["--http-query-param", "foo=bar", "--http-query-param", "baz=qux"],
        "http-query-params",
        {"foo": "bar", "baz": "qux"},
        id="Arg+value with dict mapper",
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


def test_setup_session_options_default_values(monkeypatch: pytest.MonkeyPatch, parser: ArgumentParser, session: Streamlink):
    mock_set_option = Mock()
    monkeypatch.setattr(session, "set_option", mock_set_option)
    args = parser.parse_args([])
    setup_session_options(session, args)
    assert session.options.options == session.options.defaults
    assert not mock_set_option.called, "Value of unset session-option arg must be None and must not call set_option()"


@pytest.mark.parametrize(("default", "new", "expected"), [
    pytest.param(False, None, False, id="Default False, unset"),
    pytest.param(True, None, True, id="Default True, unset"),
    pytest.param(False, False, False, id="Default False, set to False"),
    pytest.param(False, True, True, id="Default False, set to True"),
    pytest.param(True, False, False, id="Default True, set to False"),
    pytest.param(True, True, True, id="Default True, set to True"),
])
def test_setup_session_options_override(monkeypatch: pytest.MonkeyPatch, session: Streamlink, default, new, expected):
    arg = "NON_EXISTING_ARGPARSER_ARGUMENT"
    key = "NON-EXISTING-SESSION-OPTION-KEY"
    monkeypatch.setattr("streamlink_cli.argparser._ARGUMENT_TO_SESSIONOPTION", [(arg, key, None)])
    session.set_option(key, default)
    setup_session_options(session, Namespace(**{arg: new}))
    assert session.get_option(key) == expected


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
