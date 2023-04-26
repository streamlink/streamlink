import logging
import re
import shlex
import subprocess
import sys
import warnings
from contextlib import suppress
from pathlib import Path
from shutil import which
from time import sleep
from typing import ClassVar, Dict, List, Optional, TextIO, Type, Union

from streamlink.compat import is_win32
from streamlink.exceptions import StreamlinkWarning
from streamlink.utils.named_pipe import NamedPipeBase
from streamlink_cli.output.abc import Output
from streamlink_cli.output.file import FileOutput
from streamlink_cli.output.http import HTTPOutput
from streamlink_cli.utils import Formatter


log = logging.getLogger("streamlink.cli.output")


class PlayerArgs:
    EXECUTABLES: ClassVar[List[re.Pattern]] = []

    def __init__(
        self,
        path: Path,
        args: str = "",
        title: Optional[str] = None,
        filename: Optional[str] = None,
        namedpipe: Optional[NamedPipeBase] = None,
        http: Optional[HTTPOutput] = None,
    ):
        self.path = path
        self.args = args
        self.title = title

        self._has_var_playerinput = f"{{{PlayerOutput.PLAYER_ARGS_INPUT}}}" in args
        self._has_var_playertitleargs = f"{{{PlayerOutput.PLAYER_ARGS_TITLE}}}" in args

        if namedpipe:
            self._input = self.get_namedpipe(namedpipe)
        elif filename:
            self._input = self.get_filename(filename)
        elif http:
            self._input = self.get_http(http)
        else:
            self._input = self.get_stdin()

    def build(self) -> List[str]:
        args_title = []
        if self.title is not None:
            args_title.extend(self.get_title(self.title))

        # format args via the formatter, so that invalid/unknown variables don't raise a KeyError
        argsformatter = Formatter({
            PlayerOutput.PLAYER_ARGS_INPUT: lambda: subprocess.list2cmdline([self._input]),
            PlayerOutput.PLAYER_ARGS_TITLE: lambda: subprocess.list2cmdline(args_title),
        })
        args = argsformatter.title(self.args)
        args_tokenized = shlex.split(args)

        if not self._has_var_playertitleargs:
            args_tokenized = [*args_title, *args_tokenized]
        if not self._has_var_playerinput:
            args_tokenized.append(self._input)

        return [str(self.path), *args_tokenized]

    # noinspection PyMethodMayBeStatic
    def get_stdin(self) -> str:
        return "-"

    def get_namedpipe(self, namedpipe: NamedPipeBase) -> str:
        return str(namedpipe.path)

    # noinspection PyMethodMayBeStatic
    def get_filename(self, filename: str) -> str:
        return filename

    # noinspection PyMethodMayBeStatic
    def get_http(self, http: HTTPOutput) -> str:
        return http.url

    def get_title(self, title: str) -> List[str]:
        return []


class PlayerArgsVLC(PlayerArgs):
    EXECUTABLES = [
        re.compile(r"^vlc$", re.IGNORECASE),
    ]

    def get_namedpipe(self, namedpipe: NamedPipeBase) -> str:
        if is_win32:
            return f"stream://\\{namedpipe.path}"

        return super().get_namedpipe(namedpipe)

    def get_title(self, title) -> List[str]:
        # allow escaping with \$: see https://wiki.videolan.org/Documentation:Format_String/
        # TODO: remove this feature
        title = title.replace("$", "$$").replace(r"\$$", "$")

        return ["--input-title-format", title]


class PlayerArgsMPV(PlayerArgs):
    EXECUTABLES = [
        re.compile(r"^mpv$", re.IGNORECASE),
    ]

    def get_namedpipe(self, namedpipe: NamedPipeBase) -> str:
        if is_win32:
            return f"file://{namedpipe.path}"

        return super().get_namedpipe(namedpipe)

    def get_title(self, title: str) -> List[str]:
        return [f"--force-media-title={title}"]


class PlayerArgsPotplayer(PlayerArgs):
    EXECUTABLES = [
        re.compile(r"^potplayer(?:mini(?:64)?)?$", re.IGNORECASE),
    ]

    def get_title(self, title: str) -> List[str]:
        if self._input != "-":
            # PotPlayer CLI help:
            # "You can specify titles for URLs by separating them with a backslash (\) at the end of URLs."
            self._input = f"{self._input}\\{title}"

        return []


class PlayerOutput(Output):
    PLAYER_TERMINATE_TIMEOUT = 10.0

    PLAYER_ARGS_INPUT = "playerinput"
    PLAYER_ARGS_TITLE = "playertitleargs"

    PLAYERS: ClassVar[Dict[str, Type[PlayerArgs]]] = {
        "vlc": PlayerArgsVLC,
        "mpv": PlayerArgsMPV,
        "potplayer": PlayerArgsPotplayer,
    }

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

        self.playerargs = self.playerargsfactory(
            path=path,
            args=args,
            title=title,
            namedpipe=namedpipe,
            filename=filename,
            http=http,
        )

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

    @classmethod
    def playerargsfactory(cls, path: Path, **kwargs) -> PlayerArgs:
        executable = path.name
        if is_win32 and executable[-4:].lower() == ".exe":
            executable = executable[:-4]

        for playerclass in cls.PLAYERS.values():
            for re_executable in playerclass.EXECUTABLES:
                if re_executable.search(executable):
                    return playerclass(path=path, **kwargs)

        return PlayerArgs(path=path, **kwargs)

    @property
    def running(self):
        sleep(0.5)
        return self.player.poll() is None

    def _open(self):
        args = self.playerargs.build()

        playerpath = args[0]
        args[0] = which(playerpath)
        if not args[0]:
            if playerpath[:1] in ("\"", "'"):
                warnings.warn(
                    "\n".join([
                        "The --player argument has been changed and now only takes player path values:",
                        "  Player paths with spaces don't have to be wrapped in quotation marks anymore.",
                        "  Custom player arguments need to be set via --player-args.",
                    ]),
                    StreamlinkWarning,
                    stacklevel=1,
                )

            raise FileNotFoundError("Player executable not found")

        if self.record:
            self.record.open()
        if self.call and self.filename:
            self._open_call(args)
        else:
            self._open_subprocess(args)

    def _open_call(self, args: List[str]):
        log.debug(f"Calling: {args!r}")

        subprocess.call(
            args,
            stdout=self.stdout,
            stderr=self.stderr,
        )

    def _open_subprocess(self, args: List[str]):
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
