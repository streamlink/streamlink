#!/usr/bin/env python3

class CommandLine(object):
    def __init__(self, command):
        self.command = command
        self.args = {}

    def arg(self, key, value):
        self.args[key] = value

    def format(self):
        args = []

        for key, value in self.args.items():
            if value == True:
                args.append(("--{0}").format(key))
            else:
                escaped = value.replace('"', '\\"').replace("$", "\$").replace("`", "\`")
                args.append(("--{0} \"{1}\"").format(key, escaped))

        args = (" ").join(args)
        cmdline = ("{0} {1}").format(self.command, args)

        return cmdline
