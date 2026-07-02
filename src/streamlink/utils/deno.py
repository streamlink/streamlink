from __future__ import annotations

from typing import ClassVar

from streamlink.logger import getLogger
from streamlink.utils.path import resolve_executable
from streamlink.utils.processoutput import ProcessOutput


log = getLogger(__name__)


class DenoProcessor(ProcessOutput):
    """
    Utility class for finding and launching Deno on the user's system and processing JavaScript via stdin/stdout.
    """

    # https://docs.deno.com/runtime/reference/cli/run/#usage
    _RUN_FLAGS: ClassVar[frozenset[str]] = frozenset([
        "--ext=js",
        "--no-code-cache",
        "--no-prompt",
        "--no-remote",
        "--no-lock",
        "--node-modules-dir=none",
        "--no-config",
        "--no-npm",
    ])

    stdin: bytes

    def __init__(
        self,
        executable_path: str | None = None,
        stdin: str = "",
        **kwargs,
    ) -> None:
        self._output_lines: list[str] = []
        exec_path = self.resolve_path(executable_path)
        super().__init__(
            [exec_path, "run", *self._RUN_FLAGS, "-"],
            stdin=stdin.encode("utf-8"),
            **kwargs,
        )

    async def arun(self) -> bool:
        log.trace("Running Deno with a stdin payload of %d bytes: %r", len(self.stdin), self.command)
        return await super().arun()

    @property
    def output(self) -> str:
        return "\n".join(self._output_lines)

    def onstdout(self, idx: int, line: str) -> bool | None:
        self._output_lines.append(line)

    def onstderr(self, idx: int, line: str) -> bool | None:
        raise RuntimeError(f"Deno error: {line}")

    @staticmethod
    def resolve_path(executable_path: str | None = None):
        if not executable_path:
            exec_path = resolve_executable(names=["deno"])
        else:
            exec_path = executable_path

        if not exec_path:
            raise FileNotFoundError("Deno not found. Please install the Deno JavaScript runtime on your system.")

        return str(exec_path)
