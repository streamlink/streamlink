from .stream import Stream
from .wrappers import StreamIOThreadWrapper
from ..compat import str
from ..exceptions import StreamError
from ..packages import pbs as sh

import os
import time
import tempfile

class StreamProcessIO(StreamIOThreadWrapper):
    def __init__(self, session, process, **kwargs):
        self.process = process

        StreamIOThreadWrapper.__init__(self, session,
                                       process.stdout,
                                       **kwargs)

    def close(self):
        try:
            self.process.kill()
        except Exception:
            pass

        StreamIOThreadWrapper.close(self)


class StreamProcess(Stream):
    def __init__(self, session, params=None, timeout=60.0):
        Stream.__init__(self, session)

        if not params:
            params = {}

        self.params = params
        self.errorlog = self.session.options.get("subprocess-errorlog")
        self.timeout = timeout

    def open(self):
        cmd = self._check_cmd()
        params = self.params.copy()
        params["_bg"] = True

        if self.errorlog:
            tmpfile = tempfile.NamedTemporaryFile(prefix="livestreamer",
                                                  suffix=".err", delete=False)
            params["_err"] = tmpfile
        else:
            params["_err"] = open(os.devnull, "wb")

        with params["_err"]:
            stream = cmd(**params)

        # Wait 0.5 seconds to see if program exited prematurely
        time.sleep(0.5)

        process_alive = stream.process.returncode is None

        if not process_alive:
            if self.errorlog:
                raise StreamError(("Error while executing subprocess, "
                                   "error output logged to: {0}").format(tmpfile.name))
            else:
                raise StreamError("Error while executing subprocess")

        return StreamProcessIO(self.session, stream.process,
                               timeout=self.timeout)

    def _check_cmd(self):
        try:
            cmd = sh.create_command(self.cmd)
        except sh.CommandNotFound as err:
            raise StreamError("Unable to find {0} command".format(err))

        return cmd

    def cmdline(self):
        cmd = self._check_cmd()

        return str(cmd.bake(**self.params))

    @classmethod
    def is_usable(cls, cmd):
        try:
            cmd = sh.create_command(cmd)
        except sh.CommandNotFound:
            return False

        return True


__all__ = ["StreamProcess"]
