from __future__ import annotations

import sys
from collections.abc import Sequence
from ctypes import CDLL, POINTER, Structure, byref
from ctypes.wintypes import (
    BOOL,
    DWORD,
    HANDLE,
    SHORT,
    SMALL_RECT,
    WCHAR,
    WORD,
)
from io import TextIOWrapper
from typing import Callable, ClassVar


# https://learn.microsoft.com/en-us/windows/console/coord-str
class COORD(Structure):
    _fields_: ClassVar = [
        ("X", SHORT),
        ("Y", SHORT),
    ]


# https://learn.microsoft.com/en-us/windows/console/console-screen-buffer-info-str
# noinspection PyPep8Naming
class CONSOLE_SCREEN_BUFFER_INFO(Structure):
    _fields_: ClassVar = [
        ("dwSize", COORD),
        ("dwCursorPosition", COORD),
        ("wAttributes", WORD),
        ("srWindow", SMALL_RECT),
        ("dwMaximumWindowSize", COORD),
    ]


class _WinApiCall:
    argtypes: ClassVar[Sequence]
    restype: ClassVar
    method: Callable

    def __init__(self, dll: CDLL):
        self._dll = dll
        method = getattr(dll, self.__class__.__name__)
        method.argtypes = self.argtypes
        method.restype = self.restype
        self.method = method

    def __call__(self, *args):  # pragma: no cover
        return self.method(*args)

    def _call_success(self, *args):
        if not self.method(*args):
            # https://learn.microsoft.com/en-us/windows/win32/api/errhandlingapi/nf-errhandlingapi-getlasterror
            # https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes#system-error-codes
            last_error = self._dll.GetLastError()

            raise OSError(f"Error while calling kernel32.{self.__class__.__name__} ({last_error=:#x})")


class GetStdHandle(_WinApiCall):
    """
    https://learn.microsoft.com/en-us/windows/console/getstdhandle
    """

    STD_OUTPUT_HANDLE = -11
    STD_ERROR_HANDLE = -12

    argtypes: ClassVar = [DWORD]
    restype: ClassVar = HANDLE

    def __call__(self, handle: TextIOWrapper | None) -> HANDLE:
        if handle is sys.stderr:
            std_handle = self.STD_ERROR_HANDLE
        else:
            std_handle = self.STD_OUTPUT_HANDLE

        return self.method(std_handle)


class GetConsoleMode(_WinApiCall):
    """
    https://learn.microsoft.com/en-us/windows/console/getconsolemode
    """

    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 4

    argtypes: ClassVar = [HANDLE, POINTER(DWORD)]
    restype: ClassVar = BOOL

    def __call__(self, console_output: HANDLE) -> int:
        mode = DWORD()
        self._call_success(console_output, mode)

        return mode.value

    def supports_virtual_terminal_processing(self, console_output: HANDLE) -> bool:
        try:
            console_mode = self(console_output)
        except OSError:
            return False

        return console_mode & self.ENABLE_VIRTUAL_TERMINAL_PROCESSING > 0


class GetConsoleScreenBufferInfo(_WinApiCall):
    """
    https://learn.microsoft.com/en-us/windows/console/getconsolescreenbufferinfo
    """

    argtypes: ClassVar = [HANDLE, POINTER(CONSOLE_SCREEN_BUFFER_INFO)]
    restype: ClassVar = BOOL

    def __call__(self, console_output: HANDLE) -> CONSOLE_SCREEN_BUFFER_INFO:
        console_screen_buffer_info = CONSOLE_SCREEN_BUFFER_INFO()
        self._call_success(console_output, byref(console_screen_buffer_info))

        return console_screen_buffer_info


class SetConsoleCursorPosition(_WinApiCall):
    """
    https://learn.microsoft.com/en-us/windows/console/setconsolecursorposition
    """

    argtypes: ClassVar = [HANDLE, COORD]
    restype: ClassVar = BOOL

    def __call__(self, console_output: HANDLE, cursor_position: COORD) -> None:
        self._call_success(console_output, cursor_position)


class FillConsoleOutputAttribute(_WinApiCall):
    """
    https://learn.microsoft.com/en-us/windows/console/fillconsoleoutputattribute
    """

    argtypes: ClassVar = [HANDLE, WORD, DWORD, COORD, POINTER(DWORD)]
    restype: ClassVar = BOOL

    def __call__(self, console_output: HANDLE, attribute: int, length: int, write_coord: COORD) -> int:
        attrs = WORD(attribute)
        size = DWORD(length)
        number_of_attrs_written = DWORD()
        self._call_success(console_output, attrs, size, write_coord, byref(number_of_attrs_written))

        return number_of_attrs_written.value


class FillConsoleOutputCharacterW(_WinApiCall):
    """
    https://learn.microsoft.com/en-us/windows/console/fillconsoleoutputcharacter
    """

    argtypes: ClassVar = [HANDLE, WCHAR, DWORD, COORD, POINTER(DWORD)]
    restype: ClassVar = BOOL

    def __call__(self, console_output: HANDLE, character: str, length: int, write_coord: COORD) -> int:
        char = WCHAR(character)
        size = DWORD(length)
        number_of_chars_written = DWORD()
        self._call_success(console_output, char, size, write_coord, byref(number_of_chars_written))

        return number_of_chars_written.value


class WindowsConsole:
    def __new__(cls, *args, **kwargs):
        try:
            from ctypes import windll  # noqa: PLC0415
        except ImportError:  # pragma: no cover
            return None

        kernel32 = windll.kernel32
        cls.get_std_handle = GetStdHandle(kernel32)
        cls.get_console_mode = GetConsoleMode(kernel32)
        cls.get_console_screen_buffer_info = GetConsoleScreenBufferInfo(kernel32)
        cls.set_console_cursor_position = SetConsoleCursorPosition(kernel32)
        cls.fill_console_output_attribute = FillConsoleOutputAttribute(kernel32)
        cls.fill_console_output_character_w = FillConsoleOutputCharacterW(kernel32)

        return super().__new__(cls)

    def __init__(self, handle: TextIOWrapper | None = None):
        self.handle = self.get_std_handle(handle)

    def supports_virtual_terminal_processing(self):
        return self.get_console_mode.supports_virtual_terminal_processing(self.handle)

    def clear_line(self):
        info = self.get_console_screen_buffer_info(self.handle)

        def_attrs = info.wAttributes
        length = info.dwSize.X
        cursor_position = COORD(X=0, Y=info.dwCursorPosition.Y)
        self.fill_console_output_character_w(self.handle, " ", length, cursor_position)
        self.fill_console_output_attribute(self.handle, def_attrs, length, cursor_position)
        self.set_console_cursor_position(self.handle, cursor_position)
