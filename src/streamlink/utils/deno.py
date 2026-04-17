import logging
import os
import shlex
import subprocess

from streamlink.utils.path import resolve_executable


log = logging.getLogger(__name__)


class Deno:
    def __init__(self, params: dict | None = None):
        self._DEFAULT_PARAMS = {
            "--ext": "js",
            "--no-code-cache": True,
            "--no-prompt": True,
            "--no-remote": True,
            "--no-lock": True,
            "--node-modules-dir": "none",
            "--no-config": True,
            "--no-npm": True,
            "--cached-only": True,
        }

        self._exec_path = resolve_executable("deno")
        if not self._exec_path:
            raise FileNotFoundError("Deno not found. Please install Deno from the official website")
        self._params = {**self._DEFAULT_PARAMS, **(params or {})}

    def _build_cmd(self) -> list[str]:
        cmd = [str(self._exec_path), "run"]
        for flag, value in self._params.items():
            if value is True:
                cmd.append(str(flag))
            elif value is not False and value is not None:
                cmd.append(f"{flag}={value}")
        cmd.append("-")
        return cmd

    def execute(self, stdin) -> str:
        cmd = self._build_cmd()
        log.debug("Executing Deno: %s", shlex.join(cmd))

        proc = subprocess.Popen(
            cmd,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
            encoding="utf-8",
        )
        try:
            stdout, stderr = proc.communicate(stdin)
        except BaseException:
            proc.kill()
            proc.wait(timeout=0)
            raise

        if proc.returncode or stderr:
            msg = f"Deno process failed (returncode: {proc.returncode})"
            if stderr:
                msg = f"{msg}: {stderr.strip()}"
            raise Exception(msg)

        log.debug("Deno process completed successfully")
        return stdout
