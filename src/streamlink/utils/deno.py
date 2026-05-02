from __future__ import annotations

import subprocess
from typing import ClassVar

from streamlink.logger import getLogger
from streamlink.utils.path import resolve_executable
from streamlink.utils.processoutput import ProcessOutput


log = getLogger(__name__)


class DenoProcessor(ProcessOutput):
    # https://docs.deno.com/runtime/reference/cli/run/#usage
    DEFAULT_PARAMS: ClassVar[list[str]] = [
        "--ext=js",
        "--no-code-cache",
        "--no-prompt",
        "--no-remote",
        "--no-lock",
        "--node-modules-dir=none",
        "--no-config",
        "--no-npm",
        "-",
    ]

    def __init__(
        self,
        command: list[str],
        executable_path: str | None = None,
        **kwargs,
    ) -> None:
        self._output_lines: list[str] = []
        exec_path = self.resolve_path(executable_path)
        super().__init__([exec_path, *command], **kwargs)

    @property
    def output(self) -> str:
        return "\n".join(self._output_lines)

    def onstdout(self, idx: int, line: str) -> None:
        self._output_lines.append(line)

    def onstderr(self, idx: int, line: str) -> bool:
        raise RuntimeError(f"Deno error: {line}")

    @staticmethod
    def resolve_path(executable_path: str | None = None):
        if not executable_path:
            exec_path = resolve_executable(names=["deno.exe", "deno"])
        else:
            exec_path = executable_path

        if not exec_path:
            raise FileNotFoundError("Deno not found. Please install Deno from the official website")
        return str(exec_path)

    @classmethod
    def execute(cls, stdin: str, timeout=60) -> str:
        cmd = [cls.resolve_path(), "run", *cls.DEFAULT_PARAMS]
        log.trace("Executing Deno: %r", cmd)
        proc = subprocess.Popen(
            cmd,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )
        try:
            stdout, stderr = proc.communicate(stdin, timeout=timeout)
        except BaseException:
            proc.kill()
            raise

        if proc.returncode or stderr:
            msg = f"Deno process failed (returncode: {proc.returncode})"
            if stderr:
                msg = f"{msg}: {stderr.strip()[:200]}"
            raise RuntimeError(msg)

        log.debug("Deno process completed successfully")
        return stdout
