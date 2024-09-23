import importlib.util
from io import BufferedWriter
from os import devnull
from unittest.mock import Mock, call

import pytest

import streamlink_cli.compat


def test_no_stdout(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("sys.stdout", None)

    mock_atexit_register = Mock()
    monkeypatch.setattr("atexit.register", mock_atexit_register)

    spec = importlib.util.find_spec("streamlink_cli.compat")
    assert spec
    assert spec.loader

    module = importlib.util.module_from_spec(spec)
    assert module is not streamlink_cli.compat

    spec.loader.exec_module(module)
    assert module.sys.stdout is None
    assert isinstance(module.stdout, BufferedWriter)
    assert module.stdout.name == devnull

    assert mock_atexit_register.call_args_list == [call(module.stdout.close)]
    module.stdout.close()  # close manually, since we've mocked the atexit.register() call
