#!/usr/bin/env python3

import sys, os, pbs
import livestreamer
from livestreamer.compat import input, stdout

parser = livestreamer.utils.ArgumentParser(description="Util to play various livestreaming services in a custom player",
                                           fromfile_prefix_chars="@")
parser.add_argument("url", help="URL to stream", nargs="?")
parser.add_argument("stream", help="stream to play", nargs="?")
parser.add_argument("-p", "--player", metavar="player", help="commandline for player", default="vlc")
parser.add_argument("-o", "--output", metavar="filename", help="write stream to file instead of playing it, use - for stdout")
parser.add_argument("-O", "--stdout", action="store_true", help="write stream to stdout instead of playing it")
parser.add_argument("-l", "--plugins", action="store_true", help="print installed plugins")

RCFILE = os.path.expanduser("~/.livestreamerrc")

def exit(msg):
    sys.stderr.write("error: " + msg + "\n")
    sys.exit()

def msg(msg):
    sys.stderr.write(msg + "\n")

def write_stream(fd, out, progress):
    written = 0

    while True:
        data = fd.read(8192)
        if len(data) == 0:
            break

        try:
            out.write(data)
        except IOError:
            break

        written += len(data)

        if progress:
            sys.stderr.write(("\rWritten {0} bytes").format(written))

    if progress and written > 0:
        sys.stderr.write("\n")

    fd.close()

    if out != stdout:
        out.close()

def check_output(output):
    if os.path.isfile(output):
        sys.stderr.write(("File output {0} already exists! Overwrite it? [y/N] ").format(output))
        answer = input()
        answer = answer.strip().lower()

        if answer != "y":
            sys.exit()

    try:
        out = open(output, "wb")
    except IOError as err:
        exit(("Failed to open file {0} - ").format(output, err))

    return out

def handle_url(args):
    try:
        channel = livestreamer.resolve_url(args.url)
    except livestreamer.NoPluginError:
        exit(("No plugin can handle URL: {0}").format(args.url))

    try:
        streams = channel.get_streams()
    except livestreamer.PluginError as err:
        exit(str(err))

    if len(streams) == 0:
        exit(("No streams found on this URL: {0}").format(args.url))

    keys = list(streams.keys())
    keys.sort()
    validstreams = (", ").join(keys)

    if args.stream:
        if args.stream in streams:
            stream = streams[args.stream]
            progress = False
            out = None

            try:
                fd = stream.open()
            except livestreamer.StreamError as err:
                exit(("Could not open stream - {0}").format(err))

            if args.output:
                if args.output == "-":
                    out = stdout
                else:
                    out = check_output(args.output)
                    progress = True
            elif args.stdout:
                out = stdout
            else:
                cmd = args.player + " -"
                player = pbs.sh("-c", cmd, _bg=True, _out=sys.stdout, _err=sys.stderr)
                out = player.process.stdin

            if not out:
                exit("Failed to open a valid stream output")

            try:
                write_stream(fd, out, progress)
            except KeyboardInterrupt:
                sys.exit()
        else:
            msg(("This channel does not have stream: {0}").format(args.stream))
            msg(("Valid streams: {0}").format(validstreams))
    else:
        msg(("Found streams: {0}").format(validstreams))


def print_plugins():
    pluginlist = list(livestreamer.get_plugins().keys())
    msg(("Installed plugins: {0}").format(", ".join(pluginlist)))


def main():
    for name, plugin in livestreamer.get_plugins().items():
        plugin.handle_parser(parser)

    arglist = sys.argv[1:]

    if os.path.exists(RCFILE):
        arglist.insert(0, "@" + RCFILE)

    args = parser.parse_args(arglist)

    for name, plugin in livestreamer.get_plugins().items():
        plugin.handle_args(args)

    if args.url:
        handle_url(args)
    elif args.plugins:
        print_plugins()
    else:
        parser.print_help()
