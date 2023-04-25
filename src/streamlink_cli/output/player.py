import logging
import re
import shlex
import subprocess
import sys
from contextlib import suppress
from pathlib import Path
from time import sleep
from typing import List, Optional, TextIO, Union

from streamlink.compat import is_win32
from streamlink.utils.named_pipe import NamedPipeBase
from streamlink_cli.constants import PLAYER_ARGS_INPUT_DEFAULT, PLAYER_ARGS_INPUT_FALLBACK, SUPPORTED_PLAYERS
from streamlink_cli.output.abc import Output
from streamlink_cli.output.file import FileOutput
from streamlink_cli.output.http import HTTPOutput
from streamlink_cli.utils import Formatter


log = logging.getLogger("streamlink.cli.output")


class PlayerOutput(Output):
    PLAYER_TERMINATE_TIMEOUT = 10.0

    _re_player_args_input = re.compile("|".join(
        re.escape(f"{{{const}}}")
        for const in [PLAYER_ARGS_INPUT_DEFAULT, PLAYER_ARGS_INPUT_FALLBACK]
    ))

    player: subprocess.Popen
    stdin: Union[int, TextIO]
    stdout: Union[int, TextIO]
    stderr: Union[int, TextIO]

    def __init__(
        self,
        path: Path,
        args: str = "",
        quiet: bool = True,
        kill: bool = True,
        call: bool = False,
        filename: Optional[str] = None,
        namedpipe: Optional[NamedPipeBase] = None,
        http: Optional[HTTPOutput] = None,
        record: Optional[FileOutput] = None,
        title: Optional[str] = None,
    ):
        super().__init__()

        self.path = path
        self.args = args
        self.kill = kill
        self.call = call
        self.quiet = quiet

        self.filename = filename
        self.namedpipe = namedpipe
        self.http = http
        self.record = record

        self.title = title

        self.player_name = self.supported_player(self.path)

        if self.namedpipe or self.filename or self.http:
            self.stdin = sys.stdin
        else:
            self.stdin = subprocess.PIPE

        if self.quiet:
            self.stdout = subprocess.DEVNULL
            self.stderr = subprocess.DEVNULL
        else:
            self.stdout = sys.stdout
            self.stderr = sys.stderr

        if not self._re_player_args_input.search(self.args):
            self.args += f"{' ' if self.args else ''}{{{PLAYER_ARGS_INPUT_DEFAULT}}}"

    @property
    def running(self):
        sleep(0.5)
        return self.player.poll() is None

    @classmethod
    def supported_player(cls, path: Path) -> Optional[str]:
        for player, possiblecmds in SUPPORTED_PLAYERS.items():
            if path.name.lower() in possiblecmds:
                return player

    def _create_arguments(self) -> List[str]:
        if self.namedpipe:
            filename = str(self.namedpipe.path)
            if is_win32:
                if self.player_name == "vlc":
                    filename = f"stream://\\{filename}"
                elif self.player_name == "mpv":
                    filename = f"file://{filename}"
        elif self.filename:
            filename = self.filename
        elif self.http:
            filename = self.http.url
        else:
            filename = "-"

        extra_args = []
        if self.title is not None:
            # vlc
            if self.player_name == "vlc":
                # see https://wiki.videolan.org/Documentation:Format_String/, allow escaping with \$
                self.title = self.title.replace("$", "$$").replace(r"\$$", "$")
                extra_args.extend(["--input-title-format", self.title])

            # mpv
            if self.player_name == "mpv":
                # property expansion is only available in MPV's --title parameter
                extra_args.append(f"--force-media-title={self.title}")

            # potplayer
            if self.player_name == "potplayer":
                if filename != "-":
                    # PotPlayer - About - Command Line
                    # You can specify titles for URLs by separating them with a backslash (\) at the end of URLs.
                    filename = f"{filename}\\{self.title}"

        # format args via the formatter, so that invalid/unknown variables don't raise a KeyError
        argsformatter = Formatter({
            PLAYER_ARGS_INPUT_DEFAULT: lambda: subprocess.list2cmdline([filename]),
            PLAYER_ARGS_INPUT_FALLBACK: lambda: subprocess.list2cmdline([filename]),
        })
        args = argsformatter.title(self.args)
        args_tokenized = shlex.split(args)

        return [
            str(self.path),
            *extra_args,
            *args_tokenized,
        ]

    def _open(self):
        if self.record:
            self.record.open()
        if self.call and self.filename:
            self._open_call()
        else:
            self._open_subprocess()

    def _open_call(self):
        args = self._create_arguments()
        log.debug(f"Calling: {args!r}")

        subprocess.call(
            args,
            stdout=self.stdout,
            stderr=self.stderr,
        )

    def _open_subprocess(self):
        args = self._create_arguments()
        log.debug(f"Opening subprocess: {args!r}")

        # Force bufsize=0 on all Python versions to avoid writing the
        # unflushed buffer when closing a broken input pipe
        self.player = subprocess.Popen(
            args,
            bufsize=0,
            stdin=self.stdin,
            stdout=self.stdout,
            stderr=self.stderr,
        )
        # Wait 0.5 seconds to see if program exited prematurely
        if not self.running:
            raise OSError("Process exited prematurely")

        if self.namedpipe:
            self.namedpipe.open()
        elif self.http:
            self.http.accept_connection()
            self.http.open()

    def _close(self):
        # Close input to the player first to signal the end of the
        # stream and allow the player to terminate of its own accord
        if self.namedpipe:
            self.namedpipe.close()
        elif self.http:
            self.http.shutdown()
        elif not self.filename:
            self.player.stdin.close()

        if self.record:
            self.record.close()

        if self.kill:
            with suppress(Exception):
                self.player.terminate()
                if not is_win32:
                    t, timeout = 0.0, self.PLAYER_TERMINATE_TIMEOUT
                    while self.player.poll() is None and t < timeout:
                        sleep(0.5)
                        t += 0.5

                    if not self.player.returncode:
                        self.player.kill()
        self.player.wait()

    def _write(self, data):
        if self.record:
            self.record.write(data)

        if self.namedpipe:
            self.namedpipe.write(data)
        elif self.http:
            self.http.write(data)
        else:
            self.player.stdin.write(data)
