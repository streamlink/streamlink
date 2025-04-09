from __future__ import annotations

import sys

# noinspection PyProtectedMember
from ctypes import Structure, _SimpleCData  # noqa: PLC2701
from ctypes.wintypes import DWORD, WCHAR, WORD
from io import TextIOWrapper
from types import ModuleType
from typing import ClassVar, Generic, TypeVar
from unittest.mock import ANY, Mock, call

import pytest

from streamlink_cli.console.windows import COORD, WindowsConsole


_TCTypesType = TypeVar("_TCTypesType")


class _CTypesComparable(Generic[_TCTypesType]):
    """Allow comparing ctypes data types with built-in types for equality"""

    _type: ClassVar[type]

    def __init__(self, data: _TCTypesType):
        self.data: tuple = self._get_data(data)

    def _get_data(self, data: _TCTypesType) -> tuple:  # pragma: no cover
        raise NotImplementedError

    def __eq__(self, other):
        if isinstance(other, self._type):
            return self.__eq__(type(self)(other))
        if not isinstance(other, type(self)):  # pragma: no cover
            return False

        return self.data == other.data

    def __hash__(self):  # pragma: no cover
        return super().__hash__()


class EqSimpleCData(_CTypesComparable[_SimpleCData]):
    _type: ClassVar = _SimpleCData

    def _get_data(self, data: _SimpleCData) -> tuple:
        # noinspection PyProtectedMember
        return data._type_, data.value  # type: ignore[attr-defined]


class EqStructure(_CTypesComparable[Structure]):
    _type: ClassVar = Structure

    def _get_data(self, data: Structure) -> tuple:
        # noinspection PyProtectedMember
        return tuple(getattr(data, item) for (item, *_) in data._fields_)


@pytest.fixture(autouse=True)
def _mock_byref(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("streamlink_cli.console.windows.byref", Mock(side_effect=lambda obj, *_, **__: obj))


@pytest.fixture(autouse=True)
def mock_windll(monkeypatch: pytest.MonkeyPatch):
    mock_windll = Mock()
    monkeypatch.setattr("ctypes.windll", mock_windll, raising=False)

    return mock_windll


def test_no_windll(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(sys.modules, "ctypes", ModuleType("ctypes"))
    assert WindowsConsole() is None


@pytest.mark.parametrize(
    ("method", "function"),
    [
        ("get_std_handle", "GetStdHandle"),
        ("get_console_mode", "GetConsoleMode"),
        ("get_console_screen_buffer_info", "GetConsoleScreenBufferInfo"),
        ("set_console_cursor_position", "SetConsoleCursorPosition"),
        ("fill_console_output_attribute", "FillConsoleOutputAttribute"),
        ("fill_console_output_character_w", "FillConsoleOutputCharacterW"),
    ],
)
def test_functions(mock_windll: Mock, method: str, function: str):
    windows_console = WindowsConsole()
    assert isinstance(windows_console, WindowsConsole)
    assert getattr(windows_console, method).method is getattr(mock_windll.kernel32, function)


def test_call_success_error(monkeypatch: pytest.MonkeyPatch, mock_windll: Mock):
    windows_console = WindowsConsole()
    monkeypatch.setattr(windows_console.set_console_cursor_position, "method", Mock(return_value=False))
    mock_windll.kernel32.GetLastError.return_value = 87

    with pytest.raises(OSError) as exc_info:  # noqa: PT011
        windows_console.set_console_cursor_position(123, 456)
    assert str(exc_info.value) == "Error while calling kernel32.SetConsoleCursorPosition (last_error=0x57)"


@pytest.mark.parametrize(
    ("stream", "expected"),
    [
        pytest.param(None, -11, id="None"),
        pytest.param(sys.stdout, -11, id="stdout"),
        pytest.param(sys.stderr, -12, id="stderr"),
    ],
)
def test_std_handle(mock_windll: Mock, stream: TextIOWrapper | None, expected: int):
    windows_console = WindowsConsole(stream)
    assert mock_windll.kernel32.GetStdHandle.call_args_list == [call(expected)]
    assert windows_console.handle is mock_windll.kernel32.GetStdHandle.return_value


@pytest.mark.parametrize(
    ("value", "success", "expected"),
    [
        pytest.param(0, False, False, id="error"),
        pytest.param(3, True, False, id="no-virtual-terminal-processing"),
        pytest.param(7, True, True, id="virtual-terminal-processing"),
    ],
)
def test_supports_virtual_terminal_processing(mock_windll: Mock, value: int, success: bool, expected: bool):
    def fake_get_console_mode(_handle, mode):
        mode.value = value

        return success

    mock_windll.kernel32.GetConsoleMode.side_effect = fake_get_console_mode
    mock_windll.kernel32.GetLastError.return_value = 87

    windows_console = WindowsConsole()
    assert windows_console.supports_virtual_terminal_processing() == expected
    assert mock_windll.kernel32.GetConsoleMode.call_args_list == [call(mock_windll.kernel32.GetStdHandle.return_value, ANY)]


def test_clear_line(mock_windll: Mock):
    def fake_get_console_screen_buffer_info(_handle, console_screen_buffer_info):
        console_screen_buffer_info.dwSize.X = 144
        console_screen_buffer_info.dwSize.Y = 42
        console_screen_buffer_info.dwCursorPosition.X = 20
        console_screen_buffer_info.dwCursorPosition.Y = 15
        console_screen_buffer_info.wAttributes = 0

        return True

    mock_windll.kernel32.GetConsoleScreenBufferInfo.side_effect = fake_get_console_screen_buffer_info

    windows_console = WindowsConsole()
    windows_console.clear_line()
    assert mock_windll.kernel32.GetConsoleScreenBufferInfo.call_args_list == [
        call(mock_windll.kernel32.GetStdHandle.return_value, ANY),
    ]
    assert mock_windll.kernel32.FillConsoleOutputCharacterW.call_args_list == [
        call(
            mock_windll.kernel32.GetStdHandle.return_value,
            EqSimpleCData(WCHAR(" ")),
            EqSimpleCData(DWORD(144)),
            EqStructure(COORD(0, 15)),
            EqSimpleCData(DWORD(0)),
        ),
    ]
    assert mock_windll.kernel32.FillConsoleOutputAttribute.call_args_list == [
        call(
            mock_windll.kernel32.GetStdHandle.return_value,
            EqSimpleCData(WORD(0)),
            EqSimpleCData(DWORD(144)),
            EqStructure(COORD(0, 15)),
            EqSimpleCData(DWORD(0)),
        ),
    ]
    assert mock_windll.kernel32.SetConsoleCursorPosition.call_args_list == [
        call(
            mock_windll.kernel32.GetStdHandle.return_value,
            EqStructure(COORD(0, 15)),
        ),
    ]
