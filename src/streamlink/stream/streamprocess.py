import logging
import os.path
import subprocess
import tempfile
import time
from operator import itemgetter
from shutil import which

from streamlink.compat import devnull
from streamlink.exceptions import StreamError
from streamlink.stream.stream import Stream
from streamlink.stream.wrappers import StreamIOThreadWrapper

log = logging.getLogger(__name__)


class StreamProcessIO(StreamIOThreadWrapper):
    def __init__(self, session, process, fd, **kwargs):
        self.process = process

        super().__init__(session, fd, **kwargs)

    def close(self):
        try:
            self.process.kill()
        except Exception:
            pass
        finally:
            super().close()


class StreamProcess(Stream):
    def __init__(self, session, params=None, args=None, timeout=60.0):
        """

        :param session: Streamlink session
        :param params: keyword arguments mapped to process argument
        :param args: positional arguments
        :param timeout: timeout for process
        """
        super().__init__(session)

        self.parameters = params or {}
        self.arguments = args or []
        self.timeout = timeout
        self.errorlog = self.session.options.get("subprocess-errorlog")
        self.errorlog_path = self.session.options.get("subprocess-errorlog-path")

        if self.errorlog_path:
            self.stderr = open(self.errorlog_path, "w")
        elif self.errorlog:
            self.stderr = tempfile.NamedTemporaryFile(prefix="streamlink", suffix=".err", delete=False)
        else:
            self.stderr = devnull()

    @property
    def cmd(self):
        raise NotImplementedError

    @property
    def params(self):
        return self.parameters

    @classmethod
    def is_usable(cls, session):
        raise NotImplementedError

    def open(self):
        if self.is_usable(self.session):
            process = self.spawn(self.parameters, self.arguments)

            # Wait 0.5 seconds to see if program exited prematurely
            time.sleep(0.5)

            if not process.poll() is None:
                if hasattr(self.stderr, "name"):
                    raise StreamError(("Error while executing subprocess, "
                                       "error output logged to: {0}").format(self.stderr.name))
                else:
                    raise StreamError("Error while executing subprocess")

            return StreamProcessIO(self.session, process, process.stdout, timeout=self.timeout)
        else:
            raise StreamError(
                "{0} is not installed or not supported on your system".format(os.path.basename(self.cmd))
            )

    @classmethod
    def bake(cls, cmd, parameters=None, arguments=None, short_option_prefix="-", long_option_prefix="--"):
        cmdline = [cmd]
        parameters = parameters or {}
        arguments = arguments or []

        def to_option(key):
            if len(key) == 1:  # short argument
                return "{0}{1}".format(short_option_prefix, key)
            else:  # long argument
                return "{0}{1}".format(long_option_prefix, key.replace("_", "-"))

        # sorted for stability
        for k, v in sorted(parameters.items(), key=itemgetter(0)):
            if not isinstance(v, list):  # long argument
                cmdline.append(to_option(k))
                if v is not True:
                    cmdline.append("{0}".format(v))
            else:  # duplicate the argument if given a list of values
                for sv in v:
                    cmdline.append(to_option(k))
                    cmdline.append("{0}".format(sv))

        # positional arguments last
        cmdline.extend(arguments)

        return cmdline

    def spawn(self, parameters=None, arguments=None, stderr=None, timeout=None,
              short_option_prefix="-", long_option_prefix="--"):
        """
        Spawn the process defined in `cmd`

        parameters is converted to options the short and long option prefixes
        if a list is given as the value, the parameter is repeated with each
        value

        If timeout is set the spawn will block until the process returns or
        the timeout expires.

        :param parameters: optional parameters
        :param arguments: positional arguments
        :param stderr: where to redirect stderr to
        :param timeout: timeout for short lived process
        :param long_option_prefix: option prefix, default -
        :param short_option_prefix: long option prefix, default --
        :return: spawned process
        """
        stderr = stderr or self.stderr
        cmd = self.bake(self._check_cmd(), parameters, arguments, short_option_prefix, long_option_prefix)
        log.debug(f"Spawning command: {subprocess.list2cmdline(cmd)}")

        try:
            process = subprocess.Popen(cmd, stderr=stderr, stdout=subprocess.PIPE)
        except OSError as err:
            raise StreamError("Failed to start process: {0} ({1})".format(self._check_cmd(), str(err)))

        if timeout:
            elapsed = 0
            while elapsed < timeout and not process.poll():
                time.sleep(0.25)
                elapsed += 0.25

            # kill after the timeout has expired and the process still hasn't ended
            if not process.poll():
                try:
                    log.debug("Process timeout expired ({0}s), killing process".format(timeout))
                    process.kill()
                except Exception:
                    pass

            process.wait()

        return process

    def cmdline(self):
        return subprocess.list2cmdline(self.bake(self._check_cmd(), self.parameters, self.arguments))

    def _check_cmd(self):
        if not self.cmd:
            raise StreamError("`cmd' attribute not set")

        cmd = which(self.cmd)

        if not cmd:
            raise StreamError("Unable to find `{0}' command".format(self.cmd))

        return cmd


__all__ = ["StreamProcess"]
