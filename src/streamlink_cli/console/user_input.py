from __future__ import annotations

from typing import TYPE_CHECKING

from streamlink.user_input import UserInputRequester


if TYPE_CHECKING:
    from streamlink_cli.console.console import ConsoleOutput


class ConsoleUserInputRequester(UserInputRequester):
    """
    Request input from the user on the console using the standard ask/askpass methods
    """

    def __init__(self, console: ConsoleOutput):
        self.console = console

    def ask(self, prompt: str) -> str:
        return self.console.ask(f"{prompt.strip()}: ")

    def ask_password(self, prompt: str) -> str:
        return self.console.ask_password(f"{prompt.strip()}: ")
