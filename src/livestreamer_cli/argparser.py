import argparse

from livestreamer import __version__ as livestreamer_version

from .compat import unicode_filename
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


def nonzero_num(type):
    def func(value):
        value = type(value)
        if value > 0:
            return value
    func.__name__ = "non-zero {0}".format(type.__name__)
    return func


float = nonzero_num(float)
int = nonzero_num(int)

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
parser.add_argument("--config", action="append", metavar="filename",
                    type=unicode_filename,
                    help="Loads additional options from this config file. "
                         "Can be repeated to load multiple files.")
parser.add_argument("-l", "--loglevel", metavar="level", default="info",
                    help="Set log level, valid levels: none, error, warning, "
                          "info, debug")
parser.add_argument("-Q", "--quiet", action="store_true",
                    help="Alias for --loglevel none")
parser.add_argument("-j", "--json", action="store_true",
                    help="Output JSON instead of the normal text output and "
                         "disable log output, useful for external scripting")
parser.add_argument("--no-version-check", action="store_true",
                    help="Do not check for new Livestreamer releases")
parser.add_argument("--yes-run-as-root", action="store_true",
                    help=argparse.SUPPRESS)

group = parser.add_argument_group("stream options")
group.add_argument("--retry-streams", metavar="delay", type=float,
                   help="Will retry fetching streams until streams are found "
                        "while waiting <delay> (seconds) between each attempt")
group.add_argument("--retry-open", metavar="attempts", type=int, default=1,
                   help="Will try <attempts> to open the stream until giving up")
group.add_argument("--stream-types", "--stream-priority", metavar="types",
                   type=comma_list,
                   help="A comma-delimited list of stream types to allow. "
                        "The order will be used to separate streams when "
                        "there are multiple streams with the same name "
                        "and different stream types. Default is "
                        "rtmp,hls,hds,http,akamaihd")
group.add_argument("--stream-sorting-excludes", metavar="streams",
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
group.add_argument("--best-stream-default", action="store_true",
                   help="Use the 'best' stream if no stream is specified.")

httpopt = parser.add_argument_group("HTTP options")
httpopt.add_argument("--http-proxy", metavar="http://hostname:port/",
                     help="Specify a HTTP proxy to use for all HTTP requests")
httpopt.add_argument("--https-proxy", metavar="https://hostname:port/",
                     help="Specify a HTTPS proxy to use for all HTTPS requests")
httpopt.add_argument("--http-cookies", metavar="cookies",
                     help="A semi-colon (;) delimited list of cookies to "
                          "add to each HTTP request, e.g. foo=bar;baz=qux")
httpopt.add_argument("--http-headers", metavar="headers",
                     help="A semi-colon (;) delimited list of headers to "
                          "add to each HTTP request, e.g. foo=bar;baz=qux")
httpopt.add_argument("--http-query-params", metavar="params",
                     help="A semi-colon (;) delimited list of query parameters "
                          "to add to each HTTP request, e.g. foo=bar;baz=qux")
httpopt.add_argument("--http-ignore-env", action="store_true",
                     help="Ignore HTTP settings set in the environment, "
                          "such as environment variables (HTTP_PROXY, etc) "
                          "and ~/.netrc authentication")
httpopt.add_argument("--http-no-ssl-verify", action="store_true",
                     help="Don't verify SSL certificates. Usually a bad idea")
httpopt.add_argument("--http-ssl-cert", metavar="pem",
                     help="SSL certificate to use (pem)")
httpopt.add_argument("--http-ssl-cert-crt-key", metavar=("crt", "key"),
                     nargs=2, help="SSL certificate to use (crt and key)")
httpopt.add_argument("--http-timeout", metavar="timeout", type=float,
                     help="General timeout used by all HTTP requests except "
                          "the ones covered by other options, default is 20.0")

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

streamopt = parser.add_argument_group("stream transport options")
streamopt.add_argument("--hds-live-edge", type=float, metavar="seconds",
                       help="Specify the time live HDS streams will start "
                            "from the edge of stream, default is 10.0")
streamopt.add_argument("--hds-segment-attempts", type=int, metavar="attempts",
                       help="How many attempts should be done to download "
                            "each HDS segment, default is 3")
streamopt.add_argument("--hds-segment-timeout", type=float, metavar="timeout",
                       help="HDS segment connect and read timeout, default is 10.0")
streamopt.add_argument("--hds-timeout", type=float, metavar="timeout",
                       help="Timeout for reading data from HDS streams, "
                            "default is 60.0")
streamopt.add_argument("--hls-live-edge", type=int, metavar="segments",
                       help="How many segments from the end to start "
                            "live HLS streams on, default is 3")
streamopt.add_argument("--hls-segment-attempts", type=int, metavar="attempts",
                       help="How many attempts should be done to download "
                            "each HLS segment, default is 3")
streamopt.add_argument("--hls-segment-timeout", type=float, metavar="timeout",
                       help="HLS segment connect and read timeout, "
                            "default is 10.0")
streamopt.add_argument("--hls-timeout", type=float, metavar="timeout",
                       help="Timeout for reading data from HLS streams, "
                            "default is 60.0")
streamopt.add_argument("--http-stream-timeout", type=float, metavar="timeout",
                       help="Timeout for reading data from HTTP streams, "
                            "default is 60.0")
streamopt.add_argument("--ringbuffer-size", metavar="size", type=int,
                       help="Specify a maximum size (bytes) for the "
                            "ringbuffer, default is 16777216 (16MB)")
streamopt.add_argument("--rtmp-proxy", "--rtmpdump-proxy", metavar="host:port",
                       help="Specify a proxy (SOCKS) that RTMP streams will use")
streamopt.add_argument("--rtmp-rtmpdump", "--rtmpdump", "-r", metavar="path",
                       help="Specify location of the rtmpdump executable "
                            "used by RTMP streams, e.g. /usr/local/bin/rtmpdump")
streamopt.add_argument("--rtmp-timeout", type=float, metavar="timeout",
                       help="Timeout for reading data from RTMP streams, "
                            "default is 60.0")
streamopt.add_argument("--subprocess-cmdline", "--cmdline", "-c",
                       action="store_true",
                       help="Print command-line used internally to play "
                            "stream, this is only available for RTMP streams")
streamopt.add_argument("--subprocess-errorlog", "--errorlog", "-e",
                       action="store_true",
                       help="Log possible errors from internal subprocesses "
                            "to a temporary file, use when debugging rtmpdump "
                            "related issues")
streamopt.add_argument("--stream-url", action="store_true",
                       help="If possible, translate the stream to a URL and "
                            "print it")

pluginopt = parser.add_argument_group("plugin options")
pluginopt.add_argument("--plugin-dirs", metavar="directory", type=comma_list,
                       help="Attempts to load plugins from these directories. "
                            "Multiple directories can be used by separating "
                            "them with a semicolon (;)")
pluginopt.add_argument("--jtv-cookie", "--twitch-cookie", metavar="cookie",
                       help="Specify Twitch/Justin.tv cookies to allow access "
                            "to subscription channels, e.g. "
                            "'_twitch_session_id=xxxxxx; persistent=xxxxx'")
pluginopt.add_argument("--jtv-password", "--twitch-password",
                       help="Use this to access password protected streams.",
                       metavar="password")
pluginopt.add_argument("--twitch-oauth-token", metavar="token",
                       help="Specify a OAuth token to allow Livestreamer to "
                            "access Twitch using your account.")
pluginopt.add_argument("--twitch-oauth-authenticate", action="store_true",
                       help="Opens a web browser where you can grant "
                            "Livestreamer access to your Twitch account.")
pluginopt.add_argument("--ustream-password",
                       help="Use this to access password protected streams.",
                       metavar="password")
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
pluginopt.add_argument("--livestation-email", metavar="email",
                       help="Specify Livestation account email to access "
                            "restricted streams or Premium Quality streams.")
pluginopt.add_argument("--livestation-password", metavar="password",
                       help="Specify Livestation password for account specified.")


# Deprecated options
playeropt.add_argument("-q", "--quiet-player", action="store_true",
                       help=argparse.SUPPRESS)
pluginopt.add_argument("--jtv-legacy-names", "--twitch-legacy-names",
                       action="store_true", help=argparse.SUPPRESS)
pluginopt.add_argument("--gomtv-cookie", metavar="cookie",
                       help=argparse.SUPPRESS)
pluginopt.add_argument("--gomtv-username", metavar="username",
                       help=argparse.SUPPRESS)
pluginopt.add_argument("--gomtv-password", metavar="password",
                       nargs="?", const=True, default=None,
                       help=argparse.SUPPRESS)
streamopt.add_argument("--hds-fragment-buffer", type=int, metavar="fragments",
                       help=argparse.SUPPRESS)

__all__ = ["parser"]
