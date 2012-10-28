from . import StreamProcess, StreamError
from ..compat import str, sh, is_win32

class RTMPStream(StreamProcess):
    DefaultPath = is_win32 and "rtmpdump.exe" or "rtmpdump"

    def __init__(self, session, params):
        StreamProcess.__init__(self, session, params)

        self.cmd = self.session.options.get("rtmpdump") or self.DefaultPath
        self.params["flv"] = "-"

    def open(self):
        if "jtv" in self.params and not self._has_jtv_support():
            raise StreamError("Installed rtmpdump does not support --jtv argument")

        return StreamProcess.open(self)

    def _has_jtv_support(self):
        cmd = self._check_cmd()

        try:
            help = cmd(help=True, _err_to_out=True)
        except sh.ErrorReturnCode as err:
            raise StreamError(("Error while checking rtmpdump compatibility: {0}").format(str(err.stdout, "ascii")))

        for line in help.split("\n"):
            if line[:5] == "--jtv":
                return True

        return False

    @classmethod
    def is_usable(cls, session):
        cmd = session.options.get("rtmpdump") or cls.DefaultPath

        return StreamProcess.is_usable(cmd)


