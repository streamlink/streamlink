import argparse

from livestreamer import __version__ as livestreamer_version

from .constants import (EXAMPLE_USAGE, STREAM_PASSTHROUGH,
                        DEFAULT_PLAYER_ARGUMENTS)
from .utils import find_default_player

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


def comma_list(values):
    return [val.strip() for val in values.split(",")]


def comma_list_filter(acceptable):
    def func(p):
        values = comma_list(p)
        return list(filter(lambda v: v in acceptable, values))

    return func


parser = ArgumentParser(description="Livestreamer is CLI program that "
                                    "extracts streams from various services "
                                    "and pipes them into a video player of "
                                    "choice.",
                        fromfile_prefix_chars="@",
                        formatter_class=argparse.RawDescriptionHelpFormatter,
                        epilog=EXAMPLE_USAGE, add_help=False)

parser.add_argument("url", help="URL to stream", nargs="?")
parser.add_argument("stream", nargs="?", type=comma_list,
                    help="Stream quality to play, use 'best' or 'worst' for "
                         "highest or lowest quality available. "
                         "Fallback streams can be specified by using a "
                         "comma-separated list, e.g. '720p,480p,best'.")

parser.add_argument("-h", "--help", action="store_true",
                    help="Show this help message and exit")
parser.add_argument("-V", "--version", action="version",
                    version="%(prog)s " + livestreamer_version)
parser.add_argument("--plugins", action="store_true",
                    help="Print all currently installed plugins")
parser.add_argument("-l", "--loglevel", metavar="level", default="info",
                    help="Set log level, valid levels: none, error, warning, "
                          "info, debug")
parser.add_argument("-Q", "--quiet", action="store_true",
                    help="Alias for --loglevel none")
parser.add_argument("-j", "--json", action="store_true",
                    help="Output JSON instead of the normal text output and "
                         "disable log output, useful for external scripting")
parser.add_argument("--http-proxy", metavar="http://hostname:port/",
                    help="Specify a HTTP proxy. This is the same as "
                         "setting the environment variable 'http_proxy'.")
parser.add_argument("--https-proxy", metavar="https://hostname:port/",
                    help="Specify a HTTPS proxy. This is the same as "
                         "setting the environment variable 'https_proxy'.")
parser.add_argument("--yes-run-as-root", action="store_true",
                    help=argparse.SUPPRESS)

playeropt = parser.add_argument_group("player options")
playeropt.add_argument("-p", "--player", metavar="command",
                       default=find_default_player(),
                       help="Player command-line to start, by default VLC "
                            "will be used if it is installed.")
playeropt.add_argument("-a", "--player-args", metavar="arguments",
                       default=DEFAULT_PLAYER_ARGUMENTS,
                       help="The arguments passed to the player. These "
                            "formatting variables are available: filename. "
                            "Default is '{0}'".format(DEFAULT_PLAYER_ARGUMENTS))
playeropt.add_argument("-q", "--quiet-player", action="store_true",
                       help=argparse.SUPPRESS)
playeropt.add_argument("-v", "--verbose-player", action="store_true",
                       help="Show all player console output")
playeropt.add_argument("-n", "--player-fifo", "--fifo", action="store_true",
                       help="Make the player read the stream through a named "
                            "pipe (useful if your player can't read from "
                            "stdin)")
playeropt.add_argument("--player-http", action="store_true",
                       help="Make the player read the stream using HTTP "
                            "(useful if your player can't read from stdin)")
playeropt.add_argument("--player-continuous-http", action="store_true",
                       help="Make the player read the stream using HTTP, but "
                            "unlike --player-http will continuously try to "
                            "open the stream if the player requests it. "
                            "This makes it possible to handle stream "
                            "disconnects if your player is capable of "
                            "reconnecting to a HTTP stream, e.g "
                            "'vlc --repeat'")
playeropt.add_argument("--player-passthrough", metavar="types",
                       type=comma_list_filter(STREAM_PASSTHROUGH), default=[],
                       help="A comma-delimited list of stream types to "
                            "pass to the player as a filename rather than "
                            "piping the data. Make sure your player can "
                            "handle the stream type when using this. "
                            "Supported stream types are: "
                            "{0}".format(", ".join(STREAM_PASSTHROUGH)))
playeropt.add_argument("--player-no-close", action="store_true",
                       help="By default Livestreamer will close the "
                            "player when the stream ends. This option "
                            "will let the player decide when to exit.")

outputopt = parser.add_argument_group("file output options")
outputopt.add_argument("-o", "--output", metavar="filename",
                       help="Write stream to file instead of playing it")
outputopt.add_argument("-f", "--force", action="store_true",
                       help="Always write to file even if it already exists")
outputopt.add_argument("-O", "--stdout", action="store_true",
                       help="Write stream to stdout instead of playing it")

streamopt = parser.add_argument_group("stream options")
streamopt.add_argument("-c", "--cmdline", action="store_true",
                       help="Print command-line used internally to play "
                            "stream, this may not be available on all streams")
streamopt.add_argument("-e", "--errorlog", action="store_true",
                       help="Log possible errors from internal command-line "
                            "to a temporary file, use when debugging rtmpdump "
                            "related issues")
streamopt.add_argument("-r", "--rtmpdump", metavar="path",
                       help="Specify location of rtmpdump executable, "
                            "e.g. /usr/local/bin/rtmpdump")
streamopt.add_argument("--rtmpdump-proxy", metavar="host:port",
                       help="Specify a proxy (SOCKS) that rtmpdump will use")
streamopt.add_argument("--hds-live-edge", type=float, metavar="seconds",
                       help="Specify the time live HDS streams will start "
                            "from the edge of stream, default is 10.0")
streamopt.add_argument("--hds-fragment-buffer", type=int, metavar="fragments",
                       help="Specify the maximum amount of fragments to "
                            "buffer, this controls the maximum size of the "
                            "ringbuffer, default is 10")
streamopt.add_argument("--ringbuffer-size", metavar="size", type=int,
                       help="Specify a maximum size (bytes) for the "
                            "ringbuffer, default is 32768. Used by RTMP and "
                            "HLS. Use --hds-fragment-buffer for HDS")

pluginopt = parser.add_argument_group("plugin options")
pluginopt.add_argument("--plugin-dirs", metavar="directory", type=comma_list,
                       help="Attempts to load plugins from these directories. "
                            "Multiple directories can be used by separating "
                            "them with a semicolon (;)")
pluginopt.add_argument("--stream-types", "--stream-priority", metavar="types",
                       type=comma_list,
                       help="A comma-delimited list of stream types to allow. "
                            "The order will be used to separate streams when "
                            "there are multiple streams with the same name "
                            "and different stream types. Default is "
                            "rtmp,hls,hds,http,akamaihd")
pluginopt.add_argument("--stream-sorting-excludes", metavar="streams",
                       type=comma_list,
                       help="Fine tune best/worst synonyms by excluding "
                            "unwanted streams. Uses a filter expression in "
                            "the format [operator]<value>. For example the "
                            "filter '>480p' will exclude streams ranked "
                            "higher than '480p'. Valid operators are >, >=, < "
                            "and <=. If no operator is specified then "
                            "equality is tested. Multiple filters can be "
                            "used by separating each expression with a comma. "
                            "For example '>480p,>mobile_medium' will exclude "
                            "streams from two quality types.")

pluginopt.add_argument("--jtv-cookie", "--twitch-cookie", metavar="cookie",
                       help="Specify Twitch/Justin.tv cookies to allow access "
                            "to subscription channels, e.g. "
                            "'_twitch_session_id=xxxxxx; persistent=xxxxx'")
pluginopt.add_argument("--jtv-legacy-names", "--twitch-legacy-names",
                       action="store_true", help=argparse.SUPPRESS)
pluginopt.add_argument("--jtv-password", "--twitch-password",
                       help="Use this to access password protected streams.",
                       metavar="password")

pluginopt.add_argument("--twitch-oauth-token", metavar="token",
                       help="Specify a OAuth token to allow Livestreamer to "
                            "access Twitch using your account.")

pluginopt.add_argument("--twitch-oauth-authenticate", action="store_true",
                       help="Opens a web browser where you can grant "
                            "Livestreamer access to your Twitch account.")

pluginopt.add_argument("--gomtv-cookie", metavar="cookie",
                       help="Specify GOMTV cookie to allow access to "
                            "streams, e.g. 'SES_MEMBERNO=xxx; SES_STATE=xxx; "
                            "SES_MEMBERNICK=xxx; SES_USERNICK=xxx;'")
pluginopt.add_argument("--gomtv-username", metavar="username",
                       help="Specify GOMTV username to allow access to "
                            "streams")
pluginopt.add_argument("--gomtv-password", metavar="password",
                       help="Specify GOMTV password to allow access to "
                            "streams (if left blank you will be prompted)",
                       nargs="?", const=True, default=None)

pluginopt.add_argument("--crunchyroll-username", metavar="username",
                       help="Specify Crunchyroll username to allow access to "
                            "restricted streams")
pluginopt.add_argument("--crunchyroll-password", metavar="password",
                       help="Specify Crunchyroll password to allow access to "
                            "restricted streams (if left blank you will be "
                            "prompted)",
                       nargs="?", const=True, default=None)
pluginopt.add_argument("--crunchyroll-purge-credentials", action="store_true",
                       help="Purge Crunchyroll credentials to initiate a new "
                       "session and reauthenticate.")

__all__ = ["parser"]
