import os
import subprocess
import sys

from .compat import is_win32, stdout

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
    def __init__(self, cmd, namedpipe=None, quiet=True):
        self.cmd = cmd
        self.namedpipe = namedpipe

        if self.namedpipe:
            self.stdin = sys.stdin
        else:
            self.stdin = subprocess.PIPE

        if quiet:
            self.stdout = open(os.devnull, "w")
            self.stderr = open(os.devnull, "w")
        else:
            self.stdout = sys.stdout
            self.stderr = sys.stderr

    def _open(self):
        if self.namedpipe:
            filename = self.namedpipe.path
        else:
            filename = "-"

        playercmd = "{0} {1}".format(self.cmd, filename)
        self.player = subprocess.Popen(playercmd, shell=True, stdin=self.stdin,
                                       stdout=self.stdout, stderr=self.stderr)

        if self.namedpipe:
            self.namedpipe.open("wb")

    def _close(self):
        try:
            self.player.kill()
        except:
            pass

        if self.namedpipe:
            self.namedpipe.close()

    def _write(self, data):
        if self.namedpipe:
            self.namedpipe.write(data)
        else:
            self.player.stdin.write(data)

__all__ = ["PlayerOutput", "FileOutput"]
