#!/usr/bin/env python3

import argparse
import sys, os

from livestreamer import plugins

parser = argparse.ArgumentParser(description="Util to play various livestreaming services in a custom player")
parser.add_argument("url", help="URL to stream", nargs="?")
parser.add_argument("stream", help="stream to play", nargs="?")
parser.add_argument("player", help="commandline for player", nargs="?", default="vlc")
parser.add_argument("-o", "--output", metavar="filename", help="write stream to file instead of playing it")
parser.add_argument("-c", "--cmdline", action="store_true", help="print commandline used internally to play stream")
parser.add_argument("-p", "--plugins", action="store_true", help="print installed plugins")


def exit(msg):
    sys.stderr.write("error: " + msg + "\n")
    sys.exit()

def get_plugin_for_url(url):
    for name, plugin in plugins.get_plugins().items():
        if plugin.can_handle_url(url):
            return (name, plugin)
    return None

def handle_url(args):
    (pluginname, plugin) = get_plugin_for_url(args.url)

    if not plugin:
        exit(("No plugin can handle url: {0}").format(args.url))

    streams = plugin.get_streams(args.url)

    if not streams:
        exit(("No streams found on url: {0}").format(args.url))

    keys = list(streams.keys())
    keys.sort()
    validstreams = (", ").join(keys)

    if args.stream:
        if args.stream in streams:
            stream = streams[args.stream]
            cmdline = plugin.stream_cmdline(stream, args.output or "-")

            if args.cmdline:
                print(cmdline)
                sys.exit()
            else:
                if not args.output:
                    cmdline = ("{0} | {1} -").format(cmdline, args.player)
                os.system(cmdline)
        else:
            print(("This channel does not have stream: {0}").format(args.stream))
            print(("Valid streams: {0}").format(validstreams))
            sys.exit()
    else:
        print(("Found streams: {0}").format(validstreams))


def print_plugins():
    pluginlist = list(plugins.get_plugins().keys())
    print(("Installed plugins: {0}").format(", ".join(pluginlist)))


def main():
    plugins.load_plugins(plugins)

    args = parser.parse_args()

    if args.url:
        handle_url(args)
    elif args.plugins:
        print_plugins()
    else:
        parser.print_help()
