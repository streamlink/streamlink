from .streamprocess import StreamProcess
from ..compat import str, urljoin
from ..exceptions import StreamError
from ..packages import pbs as sh
from ..utils import rtmpparse

from time import sleep

import re

class RTMPStream(StreamProcess):
    __shortname__ = "rtmp"

    def __init__(self, session, params, redirect=False, timeout=30):
        StreamProcess.__init__(self, session, params, timeout)

        self.cmd = self.session.options.get("rtmpdump")
        self.redirect = redirect
        self.logger = session.logger.new_module("stream.rtmp")

    def __repr__(self):
        return ("<RTMPStream({0!r}, redirect={1!r}, "
                "timeout={2!r})>").format(self.params, self.redirect,
                                          self.timeout)

    def __json__(self):
        return dict(type=RTMPStream.shortname(),
                    params=self.params)

    def open(self):
        if self.session.options.get("rtmpdump-proxy"):
            if not self._supports_param("socks"):
                raise StreamError("Installed rtmpdump does not support --socks argument")

            self.params["socks"] = self.session.options.get("rtmpdump-proxy")

        if "jtv" in self.params and not self._supports_param("jtv"):
            raise StreamError("Installed rtmpdump does not support --jtv argument")

        if self.redirect:
            self._check_redirect()

        self.params["flv"] = "-"

        return StreamProcess.open(self)

    def _check_redirect(self, timeout=20):
        cmd = self._check_cmd()

        params = self.params.copy()
        params["verbose"] = True
        params["_bg"] = True

        self.logger.debug("Attempting to find tcURL redirect")

        stream = cmd(**params)

        elapsed = 0
        process_alive = True

        while elapsed < timeout and process_alive:
            process_alive = stream.process.returncode is None

            sleep(0.25)
            elapsed += 0.25

        if process_alive:
            try:
                stream.process.kill()
            except:
                pass

        try:
            stderr = stream.stderr()
        except sh.ErrorReturnCode as err:
            self._update_redirect(err.stderr)

    def _update_redirect(self, stderr):
        tcurl, redirect = None, None
        stderr = str(stderr, "utf8")

        m = re.search("DEBUG: Property: <Name:\s+redirect,\s+STRING:\s+(\w+://.+?)>", stderr)
        if m:
            redirect = m.group(1)

        if redirect:
            self.logger.debug("Found redirect tcUrl: {0}", redirect)

            if "rtmp" in self.params:
                tcurl, playpath = rtmpparse(self.params["rtmp"])
                rtmp = urljoin(redirect, playpath)
                self.params["rtmp"] = rtmp

            if "tcUrl" in self.params:
                self.params["tcUrl"] = redirect

    def _supports_param(self, param):
        cmd = self._check_cmd()

        try:
            help = cmd(help=True, _err_to_out=True)
        except sh.ErrorReturnCode as err:
            raise StreamError(("Error while checking rtmpdump compatibility: {0}").format(str(err.stdout, "ascii")))

        for line in help.split("\n"):
            m = re.match("^--(\w+)", line)

            if not m:
                continue

            if m.group(1) == param:
                return True

        return False

    @classmethod
    def is_usable(cls, session):
        cmd = session.options.get("rtmpdump")

        return StreamProcess.is_usable(cmd)


