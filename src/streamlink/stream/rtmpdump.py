import logging
import re
import subprocess
from operator import itemgetter
from shutil import which

from streamlink import logger
from streamlink.exceptions import StreamError
from streamlink.stream.streamprocess import StreamProcess
from streamlink.utils import escape_librtmp, rtmpparse

log = logging.getLogger(__name__)


class RTMPStream(StreamProcess):
    """RTMP stream using rtmpdump.

    *Attributes:*

    - :attr:`params` A :class:`dict` containing parameters passed to rtmpdump
    """

    __shortname__ = "rtmp"
    logging_parameters = ("quiet", "verbose", "debug", "q", "V", "z")

    def __init__(self, session, params, redirect=False, **kwargs):
        StreamProcess.__init__(self, session, params=params, **kwargs)

        self.timeout = self.session.options.get("rtmp-timeout")
        self.redirect = redirect

        # set rtmpdump logging level
        if self.session.options.get("subprocess-errorlog-path") or \
                self.session.options.get("subprocess-errorlog"):
            # disable any current logging level
            for p in self.logging_parameters:
                self.parameters.pop(p, None)

            if logger.root.level == logging.DEBUG:
                self.parameters["debug"] = True
            else:
                self.parameters["verbose"] = True

    @property
    def cmd(self):
        return self.session.options.get("rtmp-rtmpdump")

    def __repr__(self):
        return "<RTMPStream({0!r}, redirect={1!r}>".format(self.parameters,
                                                           self.redirect)

    def __json__(self):
        return dict(type=RTMPStream.shortname(),
                    args=self.arguments,
                    params=self.parameters)

    def open(self):
        if self.session.options.get("rtmp-proxy"):
            if not self._supports_param("socks"):
                raise StreamError("Installed rtmpdump does not support --socks argument")

            self.parameters["socks"] = self.session.options.get("rtmp-proxy")

        if "jtv" in self.parameters and not self._supports_param("jtv"):
            raise StreamError("Installed rtmpdump does not support --jtv argument")

        if "weeb" in self.parameters and not self._supports_param("weeb"):
            raise StreamError("Installed rtmpdump does not support --weeb argument")

        if self.redirect:
            self._check_redirect()

        self.parameters["flv"] = "-"

        return StreamProcess.open(self)

    def _check_redirect(self, timeout=20):
        params = self.parameters.copy()
        # remove any existing logging parameters
        for p in self.logging_parameters:
            params.pop(p, None)
        # and explicitly set verbose
        params["verbose"] = True

        log.debug("Attempting to find tcURL redirect")

        process = self.spawn(params, timeout=timeout, stderr=subprocess.PIPE)
        self._update_redirect(process.stderr.read())

    def _update_redirect(self, stderr):
        tcurl, redirect = None, None
        stderr = str(stderr, "utf8")

        m = re.search(r"DEBUG: Property: <Name:\s+redirect,\s+STRING:\s+(\w+://.+?)>", stderr)
        if m:
            redirect = m.group(1)

        if redirect:
            log.debug(f"Found redirect tcUrl: {redirect}")

            if "rtmp" in self.parameters:
                tcurl, playpath = rtmpparse(self.parameters["rtmp"])
                if playpath:
                    rtmp = "{redirect}/{playpath}".format(redirect=redirect, playpath=playpath)
                else:
                    rtmp = redirect
                self.parameters["rtmp"] = rtmp

            if "tcUrl" in self.parameters:
                self.parameters["tcUrl"] = redirect

    def _supports_param(self, param, timeout=5.0):
        try:
            rtmpdump = self.spawn(dict(help=True), timeout=timeout, stderr=subprocess.PIPE)
        except StreamError as err:
            raise StreamError("Error while checking rtmpdump compatibility: {0}".format(err.message))

        for line in rtmpdump.stderr.readlines():
            m = re.match(r"^--(\w+)", str(line, "ascii"))

            if not m:
                continue

            if m.group(1) == param:
                return True

        return False

    @classmethod
    def is_usable(cls, session):
        cmd = session.options.get("rtmp-rtmpdump")

        return which(cmd) is not None

    def to_url(self):
        stream_params = dict(self.params)
        params = [stream_params.pop("rtmp", "")]

        if "swfVfy" in self.params:
            stream_params["swfUrl"] = self.params["swfVfy"]
            stream_params["swfVfy"] = True

        if "swfhash" in self.params:
            stream_params["swfVfy"] = True
            stream_params.pop("swfhash", None)
            stream_params.pop("swfsize", None)

        # sort the keys for stability of output
        for key, value in sorted(stream_params.items(), key=itemgetter(0)):
            if isinstance(value, list):
                for svalue in value:
                    params.append("{0}={1}".format(key, escape_librtmp(svalue)))
            else:
                params.append("{0}={1}".format(key, escape_librtmp(value)))

        return " ".join(params)
