#!/usr/bin/env python3

import sys, os
import livestreamer

parser = livestreamer.utils.ArgumentParser(description="Util to play various livestreaming services in a custom player",
                                           fromfile_prefix_chars="@")
parser.add_argument("url", help="URL to stream", nargs="?")
parser.add_argument("stream", help="stream to play", nargs="?")
parser.add_argument("-p", "--player", metavar="player", help="commandline for player", default="vlc")
parser.add_argument("-o", "--output", metavar="filename", help="write stream to file instead of playing it")
parser.add_argument("-c", "--cmdline", action="store_true", help="print commandline used internally to play stream")
parser.add_argument("-l", "--plugins", action="store_true", help="print installed plugins")

RCFILE = os.path.expanduser("~/.livestreamerrc")

def exit(msg):
    sys.stderr.write("error: " + msg + "\n")
    sys.exit()

def handle_url(args):
    channel = livestreamer.resolve_url(args.url)

    if not channel:
        exit(("No plugin can handle url: {0}").format(args.url))

    streams = channel.get_streams()

    if len(streams) == 0:
        exit(("No streams found on url: {0}").format(args.url))

    keys = list(streams.keys())
    keys.sort()
    validstreams = (", ").join(keys)

    if args.stream:
        if args.stream in streams:
            stream = streams[args.stream]
            cmdline = stream.cmdline(args.output or "-")

            if args.cmdline:
                print(cmdline.format())
                sys.exit()
            else:
                if not args.output:
                    cmdline.pipe = ("{0} -").format(args.player)

                os.system(cmdline.format())
        else:
            print(("This channel does not have stream: {0}").format(args.stream))
            print(("Valid streams: {0}").format(validstreams))
    else:
        print(("Found streams: {0}").format(validstreams))


def print_plugins():
    pluginlist = list(livestreamer.get_plugins().keys())
    print(("Installed plugins: {0}").format(", ".join(pluginlist)))


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
