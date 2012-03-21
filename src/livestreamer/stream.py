from livestreamer.utils import CommandLine

class Stream(object):
    def __init__(self, params={}):
        self.params = params

    def cmdline(self, out):
       raise NotImplementedError

class RTMPStream(Stream):
    def cmdline(self, out):
        cmd = CommandLine("rtmpdump")

        for key, value in self.params.items():
            if key == "live":
                if value == 1:
                    cmd.args[key] = True

            cmd.args[key] = value

        cmd.args["flv"] = out

        return cmd
