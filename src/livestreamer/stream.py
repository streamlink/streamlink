from livestreamer.utils import CommandLine

import subprocess, shlex

class Stream(object):
    def __init__(self, params={}):
        self.params = params
        self.process = None

    def open(self):
        if self.process:
            self.close()

        cmdline = self.cmdline().format()
        args = shlex.split(cmdline)

        self.process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def read(self, *args):
        if self.process:
            return self.process.stdout.read(*args)

    def close(self):
        if self.process:
            self.process.kill()
            self.process = None

    def cmdline(self, out=None):
       raise NotImplementedError

class RTMPStream(Stream):
    def cmdline(self, out=None):
        cmd = CommandLine("rtmpdump")

        for key, value in self.params.items():
            if key == "live":
                if value == 1:
                    cmd.args[key] = True

            cmd.args[key] = value

        if out:
            cmd.args["flv"] = out

        return cmd
