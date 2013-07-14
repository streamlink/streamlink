import argparse

from livestreamer import __version__ as livestreamer_version

from .constants import EXAMPLE_USAGE


class ArgumentParser(argparse.ArgumentParser):
    def convert_arg_line_to_args(self, line):
        if len(line) == 0:
            return

        if line[0] == "#":
            return

        split = line.find("=")
        if split > 0:
            key = line[:split].strip()
            val = line[split+1:].strip()
            yield "--%s=%s" % (key, val)
        else:
            yield "--%s" % line

list_type = lambda v: [p.strip() for p in v.split(",")]

parser = ArgumentParser(description="CLI program that launches streams from various streaming services in a custom video player",
                        fromfile_prefix_chars="@",
                        formatter_class=argparse.RawDescriptionHelpFormatter,
                        epilog=EXAMPLE_USAGE, add_help=False)

parser.add_argument("url", help="URL to stream", nargs="?")
parser.add_argument("stream", help="Stream quality to play, use 'best' or 'worst' for highest or lowest quality available",
                    nargs="?")

parser.add_argument("-h", "--help", action="store_true",
                    help="Show this help message and exit")
parser.add_argument("-V", "--version", action="version", version="%(prog)s " + livestreamer_version)
parser.add_argument("-u", "--plugins", action="store_true",
                    help="Print all currently installed plugins")
parser.add_argument("-l", "--loglevel", metavar="level",
                    help="Set log level, valid levels: none, error, warning, info, debug",
                    default="info")
parser.add_argument("-Q", "--quiet", action="store_true",
                       help="Alias for --loglevel none")
parser.add_argument("-j", "--json", action="store_true",
                    help="Output JSON instead of the normal text output and disable log output, useful for external scripting")

playeropt = parser.add_argument_group("player options")
playeropt.add_argument("-p", "--player", metavar="command",
                       help="Player command-line to start, by default Livestreamer will use "
                            "VLC if it is installed.")
playeropt.add_argument("-q", "--quiet-player", action="store_true",
                       help="Hide all player console output. This option does nothing since version 1.4.3 since it is now the default behaviour")
playeropt.add_argument("-v", "--verbose-player", action="store_true",
                       help="Show all player console output")
playeropt.add_argument("-n", "--fifo", action="store_true",
                       help="Play file using a named pipe instead of stdin (can help with incompatible media players)")

outputopt = parser.add_argument_group("file output options")
outputopt.add_argument("-o", "--output", metavar="filename",
                       help="Write stream to file instead of playing it")
outputopt.add_argument("-f", "--force", action="store_true",
                       help="Always write to file even if it already exists")
outputopt.add_argument("-O", "--stdout", action="store_true",
                       help="Write stream to stdout instead of playing it")

streamopt = parser.add_argument_group("stream options")
streamopt.add_argument("-c", "--cmdline", action="store_true",
                       help="Print command-line used internally to play stream, this may not be available on all streams")
streamopt.add_argument("-e", "--errorlog", action="store_true",
                       help="Log possible errors from internal command-line to a temporary file, use when debugging")
streamopt.add_argument("-r", "--rtmpdump", metavar="path",
                       help="Specify location of rtmpdump executable, e.g. /usr/local/bin/rtmpdump")
streamopt.add_argument("--rtmpdump-proxy", metavar="host:port",
                       help="Specify a proxy (SOCKS) that rtmpdump will use")
streamopt.add_argument("--hds-live-edge", type=float, metavar="seconds",
                       help="Specify the time live HDS streams will start from the edge of stream, default is 10.0")
streamopt.add_argument("--hds-fragment-buffer", type=int, metavar="fragments",
                       help=("Specify the maximum amount of fragments to buffer, this "
                             "controls the maximum size of the ringbuffer, default is 10"))
streamopt.add_argument("--ringbuffer-size", metavar="size", type=int,
                       help=("Specify a maximum size (bytes) for the ringbuffer, default is 32768. "
                              "Used by RTMP and HLS. Use --hds-fragment-buffer for HDS"))

pluginopt = parser.add_argument_group("plugin options")
pluginopt.add_argument("--plugin-dirs", metavar="directory",
                       help="Attempts to load plugins from these directories. Multiple directories can be used by separating them with a semicolon (;)")
pluginopt.add_argument("--stream-types", "--stream-priority", metavar="types",
                       default="rtmp,hls,hds,http,akamaihd", type=list_type,
                       help=("A comma-delimited list of stream types to allow. "
                             "The order will be used to separate streams when there are "
                             "multiple streams with the same name and different stream types. "
                             "Default is rtmp,hls,hds,http,akamaihd"))
pluginopt.add_argument("--stream-sorting-excludes", metavar="streams",
                       type=list_type, help="A comma-delimited list of streams to exclude "
                                            "from the sorting used by best/worst synonyms, "
                                            "e.g. 1080p+,1080p")
pluginopt.add_argument("--jtv-cookie", metavar="cookie",
                       help="Specify JustinTV cookie to allow access to subscription channels, e.g. '_twitch_session_id=xxxxxx; persistent=xxxxx;'")
pluginopt.add_argument("--gomtv-cookie", metavar="cookie",
                       help="Specify GOMTV cookie to allow access to streams, e.g. 'SES_MEMBERNO=xxx; SES_STATE=xxx; SES_MEMBERNICK=xxx; SES_USERNICK=xxx;'")
pluginopt.add_argument("--gomtv-username", metavar="username",
                       help="Specify GOMTV username to allow access to streams")
pluginopt.add_argument("--gomtv-password", metavar="password",
                       help="Specify GOMTV password to allow access to streams (if left blank you will be prompted)",
                       nargs="?", const=True, default=None)

__all__ = ["parser"]
