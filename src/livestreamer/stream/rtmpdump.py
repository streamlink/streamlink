from . import StreamProcess, StreamError
from ..compat import str, sh

import re

class RTMPStream(StreamProcess):
    def __init__(self, session, params):
        StreamProcess.__init__(self, session, params)

        self.cmd = self.session.options.get("rtmpdump")
        self.params["flv"] = "-"

        if self.session.options.get("rtmpdump-proxy"):
            self.params["socks"] = self.session.options.get("rtmpdump-proxy")

    def open(self):
        if "jtv" in self.params and not self._supports_param("jtv"):
            raise StreamError("Installed rtmpdump does not support --jtv argument")

        if "socks" in self.params and not self._supports_param("socks"):
            raise StreamError("Installed rtmpdump does not support --socks argument")

        return StreamProcess.open(self)

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


