from . import StreamProcess, StreamError
from ..compat import str, is_win32

import sh

class RTMPStream(StreamProcess):
    def __init__(self, session, params):
        StreamProcess.__init__(self, session, params)

        self.rtmpdump = self.session.options.get("rtmpdump") or (is_win32 and "rtmpdump.exe" or "rtmpdump")
        self.params["flv"] = "-"

        try:
            self.cmd = getattr(sh, self.rtmpdump)
        except sh.CommandNotFound as err:
            raise StreamError(("Unable to find {0} command").format(str(err)))

    def open(self):
        if "jtv" in self.params and not self._has_jtv_support():
            raise StreamError("Installed rtmpdump does not support --jtv argument")

        return StreamProcess.open(self)

    def _has_jtv_support(self):
        try:
            help = self.cmd(help=True, _err_to_out=True)
        except sh.ErrorReturnCode as err:
            raise StreamError(("Error while checking rtmpdump compatibility: {0}").format(str(err.stdout, "ascii")))

        for line in help.split("\n"):
            if line[:5] == "--jtv":
                return True

        return False

