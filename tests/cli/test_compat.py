import importlib.util
from contextlib import suppress
from io import BufferedWriter, TextIOWrapper
from os import devnull
from types import ModuleType
from unittest.mock import Mock, call

import pytest

import streamlink_cli.compat


@pytest.fixture(autouse=True)
def mock_open(monkeypatch: pytest.MonkeyPatch):
    mock_open = Mock(side_effect=open)
    monkeypatch.setattr("builtins.open", mock_open)

    return mock_open


@pytest.fixture()
def _no_sys_stdout(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("sys.stdout", None)


@pytest.fixture()
def mock_atexit_register(monkeypatch: pytest.MonkeyPatch):
    mock_atexit_register = Mock()
    monkeypatch.setattr("atexit.register", mock_atexit_register)

    return mock_atexit_register


@pytest.fixture()
def module(monkeypatch: pytest.MonkeyPatch, mock_atexit_register: Mock):
    spec = importlib.util.find_spec("streamlink_cli.compat")
    assert spec
    assert spec.loader

    module = importlib.util.module_from_spec(spec)
    assert module is not streamlink_cli.compat

    spec.loader.exec_module(module)

    try:
        yield module
    finally:
        # close manually, since we've mocked the atexit.register() call
        with suppress(Exception):
            module.devnull_bin.close()
        with suppress(Exception):
            module.devnull_txt.close()


def test_devnull(mock_open: Mock, mock_atexit_register: Mock, module: ModuleType):
    assert "devnull_bin" not in module.__dict__
    assert "devnull_txt" not in module.__dict__
    assert mock_open.call_args_list == []

    assert hasattr(module, "devnull_bin")
    assert mock_open.call_args_list == [call(devnull, "wb")]
    mock_open.call_args_list.clear()

    assert hasattr(module, "devnull_txt")
    assert mock_open.call_args_list == [call(devnull, "w", encoding=None)]
    mock_open.call_args_list.clear()

    assert isinstance(module.devnull_bin, BufferedWriter)
    assert isinstance(module.devnull_txt, TextIOWrapper)
    assert module.devnull_bin.name == devnull
    assert module.devnull_txt.name == devnull
    assert mock_open.call_args_list == []

    assert mock_atexit_register.call_args_list == [
        call(module.devnull_bin.close),
        call(module.devnull_txt.close),
    ]


@pytest.mark.usefixtures("_no_sys_stdout")
def test_stdout_is_devnull(module: ModuleType):
    assert hasattr(module, "stdout_or_devnull_bin")
    assert isinstance(module.stdout_or_devnull_bin, BufferedWriter)
    assert module.stdout_or_devnull_bin.name == devnull


def test_missing_attr(mock_open: Mock, module: ModuleType):
    with pytest.raises(AttributeError) as exc_info:
        # noinspection PyStatementEffect
        module.missing_attr  # noqa: B018
    assert str(exc_info.value) == "Module 'streamlink_cli.compat' has no attribute 'missing_attr'"
    assert mock_open.call_args_list == []
