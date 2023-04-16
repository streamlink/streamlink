import logging
import os
import re
import shlex
import subprocess
import sys
from contextlib import suppress
from time import sleep

from streamlink.compat import is_win32
from streamlink_cli.constants import PLAYER_ARGS_INPUT_DEFAULT, PLAYER_ARGS_INPUT_FALLBACK, SUPPORTED_PLAYERS
from streamlink_cli.output.abc import Output
from streamlink_cli.utils import Formatter


log = logging.getLogger("streamlink.cli.output")


class PlayerOutput(Output):
    PLAYER_TERMINATE_TIMEOUT = 10.0

    _re_player_args_input = re.compile("|".join(
        re.escape(f"{{{const}}}")
        for const in [PLAYER_ARGS_INPUT_DEFAULT, PLAYER_ARGS_INPUT_FALLBACK]
    ))

    def __init__(self, cmd, args="", filename=None, quiet=True, kill=True,
                 call=False, http=None, namedpipe=None, record=None, title=None):
        super().__init__()
        self.cmd = cmd
        self.args = args
        self.kill = kill
        self.call = call
        self.quiet = quiet

        self.filename = filename
        self.namedpipe = namedpipe
        self.http = http
        self.title = title
        self.player = None
        self.player_name = self.supported_player(self.cmd)
        self.record = record

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
    def supported_player(cls, cmd):
        """
        Check if the current player supports adding a title

        :param cmd: command to test
        :return: name of the player|None
        """
        if not is_win32:
            # under a POSIX system use shlex to find the actual command
            # under windows this is not an issue because executables end in .exe
            cmd = shlex.split(cmd)[0]

        cmd = os.path.basename(cmd.lower())
        for player, possiblecmds in SUPPORTED_PLAYERS.items():
            for possiblecmd in possiblecmds:
                if cmd.startswith(possiblecmd):
                    return player

    def _create_arguments(self):
        if self.namedpipe:
            filename = self.namedpipe.path
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
                    # eg. "http://...\title of this url"
                    self.title = self.title.replace('"', "")
                    filename = filename[:-1] + "\\" + self.title + filename[-1]

        # format args via the formatter, so that invalid/unknown variables don't raise a KeyError
        argsformatter = Formatter({
            PLAYER_ARGS_INPUT_DEFAULT: lambda: filename,
            PLAYER_ARGS_INPUT_FALLBACK: lambda: filename,
        })
        args = argsformatter.title(self.args)
        cmd = self.cmd

        # player command
        if is_win32:
            eargs = subprocess.list2cmdline(extra_args)
            # do not insert and extra " " when there are no extra_args
            return " ".join([cmd] + ([eargs] if eargs else []) + [args])
        return shlex.split(cmd) + extra_args + shlex.split(args)

    def _open(self):
        if self.record:
            self.record.open()
        if self.call and self.filename:
            self._open_call()
        else:
            self._open_subprocess()

    def _open_call(self):
        args = self._create_arguments()
        if is_win32:
            fargs = args
        else:
            fargs = subprocess.list2cmdline(args)
        log.debug(f"Calling: {fargs}")

        subprocess.call(args,
                        stdout=self.stdout,
                        stderr=self.stderr)

    def _open_subprocess(self):
        # Force bufsize=0 on all Python versions to avoid writing the
        # unflushed buffer when closing a broken input pipe
        args = self._create_arguments()
        if is_win32:
            fargs = args
        else:
            fargs = subprocess.list2cmdline(args)
        log.debug(f"Opening subprocess: {fargs}")

        self.player = subprocess.Popen(args,
                                       stdin=self.stdin, bufsize=0,
                                       stdout=self.stdout,
                                       stderr=self.stderr)
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
