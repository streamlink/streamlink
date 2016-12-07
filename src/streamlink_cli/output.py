import os
import shlex
import subprocess
import sys

from time import sleep

from .compat import is_win32, stdout
from .constants import DEFAULT_PLAYER_ARGUMENTS
from .utils import ignored

if is_win32:
    import msvcrt


class Output(object):
    def __init__(self):
        self.opened = False

    def open(self):
        self._open()
        self.opened = True

    def close(self):
        if self.opened:
            self._close()

        self.opened = False

    def write(self, data):
        if not self.opened:
            raise IOError("Output is not opened")

        return self._write(data)

    def _open(self):
        pass

    def _close(self):
        pass

    def _write(self, data):
        pass


class FileOutput(Output):
    def __init__(self, filename=None, fd=None):
        self.filename = filename
        self.fd = fd

    def _open(self):
        if self.filename:
            self.fd = open(self.filename, "wb")

        if is_win32:
            msvcrt.setmode(self.fd.fileno(), os.O_BINARY)

    def _close(self):
        if self.fd is not stdout:
            self.fd.close()

    def _write(self, data):
        self.fd.write(data)


class PlayerOutput(Output):
    def __init__(self, cmd, args=DEFAULT_PLAYER_ARGUMENTS,
                 filename=None, quiet=True, kill=True,
                 call=False, http=False, namedpipe=None):
        self.cmd = cmd
        self.args = args
        self.kill = kill
        self.call = call
        self.quiet = quiet

        self.filename = filename
        self.namedpipe = namedpipe
        self.http = http

        if self.namedpipe or self.filename or self.http:
            self.stdin = sys.stdin
        else:
            self.stdin = subprocess.PIPE

        if self.quiet:
            self.stdout = open(os.devnull, "w")
            self.stderr = open(os.devnull, "w")
        else:
            self.stdout = sys.stdout
            self.stderr = sys.stderr

    @property
    def running(self):
        sleep(0.5)
        self.player.poll()
        return self.player.returncode is None

    def _create_arguments(self):
        if self.namedpipe:
            filename = self.namedpipe.path
        elif self.filename:
            filename = self.filename
        elif self.http:
            filename = self.http.url
        else:
            filename = "-"

        args = self.args.format(filename=filename)
        cmd = self.cmd
        if is_win32:
            # We want to keep the backslashes on Windows as forcing the user to
            # escape backslashes for paths would be inconvenient.
            cmd = cmd.replace("\\", "\\\\")
            args = args.replace("\\", "\\\\")

        return shlex.split(cmd) + shlex.split(args)

    def _open(self):
        try:
            if self.call and self.filename:
                self._open_call()
            else:
                self._open_subprocess()
        finally:
            if self.quiet:
                # Output streams no longer needed in parent process
                self.stdout.close()
                self.stderr.close()

    def _open_call(self):
        subprocess.call(self._create_arguments(),
                        stdout=self.stdout,
                        stderr=self.stderr)

    def _open_subprocess(self):
        # Force bufsize=0 on all Python versions to avoid writing the
        # unflushed buffer when closing a broken input pipe
        self.player = subprocess.Popen(self._create_arguments(),
                                       stdin=self.stdin, bufsize=0,
                                       stdout=self.stdout,
                                       stderr=self.stderr)

        # Wait 0.5 seconds to see if program exited prematurely
        if not self.running:
            raise OSError("Process exited prematurely")

        if self.namedpipe:
            self.namedpipe.open("wb")
        elif self.http:
            self.http.open()

    def _close(self):
        # Close input to the player first to signal the end of the
        # stream and allow the player to terminate of its own accord
        if self.namedpipe:
            self.namedpipe.close()
        elif self.http:
            self.http.close()
        elif not self.filename:
            self.player.stdin.close()

        if self.kill:
            with ignored(Exception):
                self.player.kill()
        self.player.wait()

    def _write(self, data):
        if self.namedpipe:
            self.namedpipe.write(data)
        elif self.http:
            self.http.write(data)
        else:
            self.player.stdin.write(data)

__all__ = ["PlayerOutput", "FileOutput"]
