import argparse
import re

from string import printable
from textwrap import dedent

from .constants import (
    LIVESTREAMER_VERSION, STREAM_PASSTHROUGH, DEFAULT_PLAYER_ARGUMENTS
)
from .utils import find_default_player


_filesize_re = re.compile("""
    (?P<size>\d+(\.\d+)?)
    (?P<modifier>[Kk]|[Mm])?
    (?:[Bb])?
""", re.VERBOSE)
_keyvalue_re = re.compile("(?P<key>[^=]+)\s*=\s*(?P<value>.*)")
_printable_re = re.compile("[{0}]".format(printable))
_option_re = re.compile("""
    (?P<name>[A-z-]+) # A option name, valid characters are A to z and dash.
    \s*
    (?P<op>=)? # Separating the option and the value with a equals sign is
               # common, but optional.
    \s*
    (?P<value>.*) # The value, anything goes.
""", re.VERBOSE)


class ArgumentParser(argparse.ArgumentParser):
    def convert_arg_line_to_args(self, line):
        # Strip any non-printable characters that might be in the
        # beginning of the line (e.g. Unicode BOM marker).
        match = _printable_re.search(line)
        if not match:
            return
        line = line[match.start():].strip()

        # Skip lines that do not start with a valid option (e.g. comments)
        option = _option_re.match(line)
        if not option:
            return

        name, value = option.group("name", "value")
        if name and value:
            yield "--{0}={1}".format(name, value)
        elif name:
            yield "--{0}".format(name)


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """A nicer help formatter.

    Help for arguments can be indented and contain new lines.
    It will be de-dented and arguments in the help will be
    separated by a blank line for better readability.

    Originally written by Jakub Roztocil of the httpie project.
    """
    def __init__(self, max_help_position=4, *args, **kwargs):
        # A smaller indent for args help.
        kwargs["max_help_position"] = max_help_position
        argparse.RawDescriptionHelpFormatter.__init__(self, *args, **kwargs)

    def _split_lines(self, text, width):
        text = dedent(text).strip() + "\n\n"
        return text.splitlines()


def comma_list(values):
    return [val.strip() for val in values.split(",")]


def comma_list_filter(acceptable):
    def func(p):
        values = comma_list(p)
        return list(filter(lambda v: v in acceptable, values))

    return func


def num(type, min=None, max=None):
    def func(value):
        value = type(value)

        if min is not None and not (value > min):
            raise argparse.ArgumentTypeError(
                "{0} value must be more than {1} but is {2}".format(
                    type.__name__, min, value
                )
            )

        if max is not None and not (value <= max):
            raise argparse.ArgumentTypeError(
                "{0} value must be at most {1} but is {2}".format(
                    type.__name__, max, value
                )
            )

        return value

    func.__name__ = type.__name__

    return func


def filesize(value):
    match = _filesize_re.match(value)
    if not match:
        raise ValueError

    size = float(match.group("size"))
    if not size:
        raise ValueError

    modifier = match.group("modifier")
    if modifier in ("M", "m"):
        size *= 1024 * 1024
    elif modifier in ("K", "k"):
        size *= 1024

    return num(int, min=0)(size)


def keyvalue(value):
    match = _keyvalue_re.match(value)
    if not match:
        raise ValueError

    return match.group("key", "value")


parser = ArgumentParser(
    fromfile_prefix_chars="@",
    formatter_class=HelpFormatter,
    add_help=False,
    usage="%(prog)s [OPTIONS] [URL] [STREAM]",
    description=dedent("""
    Streamlink is command-line utility that extracts streams from
    various services and pipes them into a video player of choice.
    """),
    epilog=dedent("""
    For more in-depth documention see:
      http://docs.streamlink.io/

    Please report broken plugins or bugs to the issue tracker on Github:
      https://github.com/streamlink/streamlink/issues
    """)
)

positional = parser.add_argument_group("Positional arguments")
positional.add_argument(
    "url",
    metavar="URL",
    nargs="?",
    help="""
    A URL to attempt to extract streams from.

    If it's a HTTP URL then "http://" can be omitted.
    """
)
positional.add_argument(
    "stream",
    metavar="STREAM",
    nargs="?",
    type=comma_list,
    help="""
    Stream to play.

    Use "best" or "worst" for highest or lowest quality available.

    Fallback streams can be specified by using a comma-separated list:

      "720p,480p,best"

    If no stream is specified and --default-stream is not used then a
    list of available streams will be printed.
    """
)

general = parser.add_argument_group("General options")
general.add_argument(
    "-h", "--help",
    action="store_true",
    help="""
    Show this help message and exit.
    """
)
general.add_argument(
    "-V", "--version",
    action="version",
    version="%(prog)s {0}".format(LIVESTREAMER_VERSION),
    help="""
    Show version number and exit.
    """
)
general.add_argument(
    "--plugins",
    action="store_true",
    help="""
    Print a list of all currently installed plugins.
    """
)
general.add_argument(
    "--can-handle-url",
    metavar="URL",
    help="""
    Check if Streamlink has a plugin that can handle the specified URL.

    Returns status code 1 for false and 0 for true.

    Useful for external scripting.
    """
)
general.add_argument(
    "--config",
    action="append",
    metavar="FILENAME",
    help="""
    Load options from this config file.

    Can be repeated to load multiple files, in which case
    the options are merged on top of each other where the
    last config has highest priority.
    """
)
general.add_argument(
    "-l", "--loglevel",
    metavar="LEVEL",
    default="info",
    help="""
    Set the log message threshold.

    Valid levels are: none, error, warning, info, debug
    """
)
general.add_argument(
    "-Q", "--quiet",
    action="store_true",
    help="""
    Hide all log output.

    Alias for "--loglevel none".
    """
)
general.add_argument(
    "-j", "--json",
    action="store_true",
    help="""
    Output JSON representations instead of the normal text output.

    Useful for external scripting.
    """
)
general.add_argument(
    "--no-version-check",
    action="store_true",
    help="""
    Do not check for new Streamlink releases.
    """
)
general.add_argument(
    "--version-check",
    action="store_true",
    help="""
    Runs a version check and exits.
    """
)
general.add_argument(
    "--yes-run-as-root",
    action="store_true",
    help=argparse.SUPPRESS
)

player = parser.add_argument_group("Player options")
player.add_argument(
    "-p", "--player",
    metavar="COMMAND",
    default=find_default_player(),
    help="""
    Player to feed stream data to. This is a shell-like syntax to
    support passing options to the player. For example:

      "vlc --file-caching=5000"

    To use a player that is located in a path with spaces you must
    quote the path:

      "'/path/with spaces/vlc' --file-caching=5000"

    By default VLC will be used if it can be found in its default
    location.
    """
)
player.add_argument(
    "-a", "--player-args",
    metavar="ARGUMENTS",
    default=DEFAULT_PLAYER_ARGUMENTS,
    help="""
    This option allows you to customize the default arguments which
    are put together with the value of --player to create a command
    to execute.

    This value can contain formatting variables surrounded by curly
    braces, {{ and }}. If you need to include a brace character, it
    can be escaped by doubling, e.g. {{{{ and }}}}.

    Formatting variables available:

    filename
      This is the filename that the player will use.
      It's usually "-" (stdin), but can also be a URL or a file
      depending on the options used.

    It's usually enough to use --player instead of this unless you
    need to add arguments after the filename.

    Default is "{0}".
    """.format(DEFAULT_PLAYER_ARGUMENTS)
)
player.add_argument(
    "-v", "--verbose-player",
    action="store_true",
    help="""
    Allow the player to display its console output.
    """
)
player.add_argument(
    "-n", "--player-fifo", "--fifo",
    action="store_true",
    help="""
    Make the player read the stream through a named pipe instead of
    the stdin pipe.
    """
)
player.add_argument(
    "--player-http",
    action="store_true",
    help="""
    Make the player read the stream through HTTP instead of
    the stdin pipe.
    """
)
player.add_argument(
    "--player-continuous-http",
    action="store_true",
    help="""
    Make the player read the stream through HTTP, but unlike
    --player-http it will continuously try to open the stream if the
    player requests it.

    This makes it possible to handle stream disconnects if your player
    is capable of reconnecting to a HTTP stream. This is usually
    done by setting your player to a "repeat mode".

    """
)
player.add_argument(
    "--player-external-http",
    action="store_true",
    help="""
    Serve stream data through HTTP without running any player. This is useful
    to allow external devices like smartphones or streaming boxes to watch
    streams they wouldn't be able to otherwise.

    Behavior will be similar to the continuous HTTP option, but no player
    program will be started, and the server will listen on all available
    connections instead of just in the local (loopback) interface.

    The URLs that can be used to access the stream will be printed to the
    console, and the server can be interrupted using CTRL-C.
    """
)
player.add_argument(
    "--player-external-http-port",
    metavar="PORT",
    type=num(int, min=0, max=65535),
    default=0,
    help="""
    A fixed port to use for the external HTTP server if that mode is enabled.
    Omit or set to 0 to use a random high (>1024) port.
    """
)
player.add_argument(
    "--player-passthrough",
    metavar="TYPES",
    type=comma_list_filter(STREAM_PASSTHROUGH),
    default=[],
    help="""
    A comma-delimited list of stream types to pass to the player as a
    URL to let it handle the transport of the stream instead.

    Stream types that can be converted into a playable URL are:

    - {0}

    Make sure your player can handle the stream type when using this.
    """.format("\n    - ".join(STREAM_PASSTHROUGH))
)
player.add_argument(
    "--player-no-close",
    action="store_true",
    help="""
    By default Streamlink will close the player when the stream ends.
    This is to avoid "dead" GUI players lingering after a stream ends.

    It does however have the side-effect of sometimes closing a player
    before it has played back all of its cached data.

    This option will instead let the player decide when to exit.
    """
)

output = parser.add_argument_group("File output options")
output.add_argument(
    "-o", "--output",
    metavar="FILENAME",
    help="""
    Write stream data to FILENAME instead of playing it.

    You will be prompted if the file already exists.
    """
)
output.add_argument(
    "-f", "--force",
    action="store_true",
    help="""
    When using -o, always write to file even if it already exists.
    """
)
output.add_argument(
    "-O", "--stdout",
    action="store_true",
    help="""
    Write stream data to stdout instead of playing it.
    """
)

stream = parser.add_argument_group("Stream options")
stream.add_argument(
    "--default-stream",
    type=comma_list,
    metavar="STREAM",
    help="""
    Open this stream when no stream argument is specified, e.g. "best".
    """
)
stream.add_argument(
    "--retry-streams",
    metavar="DELAY",
    type=num(float, min=0),
    help="""
    Will retry fetching streams until streams are found while
    waiting DELAY (seconds) between each attempt.
    """
)
stream.add_argument(
    "--retry-open",
    metavar="ATTEMPTS",
    type=num(int, min=0),
    default=1,
    help="""
    Will try ATTEMPTS times to open the stream until giving up.

    Default is 1.
    """
)
stream.add_argument(
    "--stream-types", "--stream-priority",
    metavar="TYPES",
    type=comma_list,
    help="""
    A comma-delimited list of stream types to allow.

    The order will be used to separate streams when there are multiple
    streams with the same name but different stream types.

    Default is "rtmp,hls,hds,http,akamaihd".
    """
)
stream.add_argument(
    "--stream-sorting-excludes",
    metavar="STREAMS",
    type=comma_list,
    help="""
    Fine tune best/worst synonyms by excluding unwanted streams.

    Uses a filter expression in the format:

      [operator]<value>

    Valid operators are >, >=, < and <=. If no operator is specified
    then equality is tested.

    For example this will exclude streams ranked higher than "480p":

      ">480p"

    Multiple filters can be used by separating each expression with
    a comma.

    For example this will exclude streams from two quality types:

      ">480p,>medium"

    """
)

transport = parser.add_argument_group("Stream transport options")
transport.add_argument(
    "--hds-live-edge",
    type=num(float, min=0),
    metavar="SECONDS",
    help="""
    The time live HDS streams will start from the edge of stream.

    Default is 10.0.
    """
)
transport.add_argument(
    "--hds-segment-attempts",
    type=num(int, min=0),
    metavar="ATTEMPTS",
    help="""
    How many attempts should be done to download each HDS segment
    before giving up.

    Default is 3.
    """
)
transport.add_argument(
    "--hds-segment-threads",
    type=num(int, max=10),
    metavar="THREADS",
    help="""
    The size of the thread pool used to download HDS segments.
    Minimum value is 1 and maximum is 10.

    Default is 1.
    """
)
transport.add_argument(
    "--hds-segment-timeout",
    type=num(float, min=0),
    metavar="TIMEOUT",
    help="""
    HDS segment connect and read timeout.

    Default is 10.0.
    """
)
transport.add_argument(
    "--hds-timeout",
    type=num(float, min=0),
    metavar="TIMEOUT",
    help="""
    Timeout for reading data from HDS streams.

    Default is 60.0.
    """
)
transport.add_argument(
    "--hls-live-edge",
    type=num(int, min=0),
    metavar="SEGMENTS",
    help="""
    How many segments from the end to start live HLS streams on.

    The lower the value the lower latency from the source you will be,
    but also increases the chance of buffering.

    Default is 3.
    """
)
transport.add_argument(
    "--hls-segment-attempts",
    type=num(int, min=0),
    metavar="ATTEMPTS",
    help="""
    How many attempts should be done to download each HLS segment
    before giving up.

    Default is 3.
    """
)
transport.add_argument(
    "--hls-segment-threads",
    type=num(int, max=10),
    metavar="THREADS",
    help="""
    The size of the thread pool used to download HLS segments.
    Minimum value is 1 and maximum is 10.

    Default is 1.
    """
)
transport.add_argument(
    "--hls-segment-timeout",
    type=num(float, min=0),
    metavar="TIMEOUT",
    help="""
    HLS segment connect and read timeout.

    Default is 10.0.
    """)
transport.add_argument(
    "--hls-timeout",
    type=num(float, min=0),
    metavar="TIMEOUT",
    help="""
    Timeout for reading data from HLS streams.

    Default is 60.0.
    """)
transport.add_argument(
    "--http-stream-timeout",
    type=num(float, min=0),
    metavar="TIMEOUT",
    help="""
    Timeout for reading data from HTTP streams.

    Default is 60.0.
    """
)
transport.add_argument(
    "--ringbuffer-size",
    metavar="SIZE",
    type=filesize,
    help="""
    The maximum size of ringbuffer. Add a M or K suffix to specify mega
    or kilo bytes instead of bytes.

    The ringbuffer is used as a temporary storage between the stream
    and the player. This is to allows us to download the stream faster
    than the player wants to read it.

    The smaller the size, the higher chance of the player buffering
    if there are download speed dips and the higher size the more data
    we can use as a storage to catch up from speed dips.

    It also allows you to temporary pause as long as the ringbuffer
    doesn't get full since we continue to download the stream in the
    background.

    Note: A smaller size is recommended on lower end systems (such as
    Raspberry Pi) when playing stream types that require some extra
    processing (such as HDS) to avoid unnecessary background
    processing.

    Default is "16M".
    """)
transport.add_argument(
    "--rtmp-proxy", "--rtmpdump-proxy",
    metavar="PROXY",
    help="""
    A SOCKS proxy that RTMP streams will use.

    Example: 127.0.0.1:9050
    """
)
transport.add_argument(
    "--rtmp-rtmpdump", "--rtmpdump", "-r",
    metavar="FILENAME",
    help="""
    RTMPDump is used to access RTMP streams. You can specify the
    location of the rtmpdump executable if it is not in your PATH.

    Example: "/usr/local/bin/rtmpdump"
    """
)
transport.add_argument(
    "--rtmp-timeout",
    type=num(float, min=0),
    metavar="TIMEOUT",
    help="""
    Timeout for reading data from RTMP streams.

    Default is 60.0.
    """
)
transport.add_argument(
    "--stream-segment-attempts",
    type=num(int, min=0),
    metavar="ATTEMPTS",
    help="""
    How many attempts should be done to download each segment before giving up.

    This is generic option used by streams not covered by other options,
    such as stream protocols specific to plugins, e.g. UStream.

    Default is 3.
    """
)
transport.add_argument(
    "--stream-segment-threads",
    type=num(int, max=10),
    metavar="THREADS",
    help="""
    The size of the thread pool used to download segments.
    Minimum value is 1 and maximum is 10.

    This is generic option used by streams not covered by other options,
    such as stream protocols specific to plugins, e.g. UStream.

    Default is 1.
    """
)
transport.add_argument(
    "--stream-segment-timeout",
    type=num(float, min=0),
    metavar="TIMEOUT",
    help="""
    Segment connect and read timeout.

    This is generic option used by streams not covered by other options,
    such as stream protocols specific to plugins, e.g. UStream.

    Default is 10.0.
    """)
transport.add_argument(
    "--stream-timeout",
    type=num(float, min=0),
    metavar="TIMEOUT",
    help="""
    Timeout for reading data from streams.

    This is generic option used by streams not covered by other options,
    such as stream protocols specific to plugins, e.g. UStream.

    Default is 60.0.
    """)
transport.add_argument(
    "--stream-url",
    action="store_true",
    help="""
    If possible, translate the stream to a URL and print it.
    """
)
transport.add_argument(
    "--subprocess-cmdline", "--cmdline", "-c",
    action="store_true",
    help="""
    Print command-line used internally to play stream.

    This is only available on RTMP streams.
    """
)
transport.add_argument(
    "--subprocess-errorlog", "--errorlog", "-e",
    action="store_true",
    help="""
    Log possible errors from internal subprocesses to a temporary file.
    The file will be saved in your systems temporary directory.

    Useful when debugging rtmpdump related issues.
    """
)


http = parser.add_argument_group("HTTP options")
http.add_argument(
    "--http-proxy",
    metavar="HTTP_PROXY",
    help="""
    A HTTP proxy to use for all HTTP requests.

    Example: http://hostname:port/
    """
)
http.add_argument(
    "--https-proxy",
    metavar="HTTPS_PROXY",
    help="""
    A HTTPS capable proxy to use for all HTTPS requests.

    Example: http://hostname:port/
    """
)
http.add_argument(
    "--http-cookie",
    metavar="KEY=VALUE",
    type=keyvalue,
    action="append",
    help="""
    A cookie to add to each HTTP request.

    Can be repeated to add multiple cookies.
    """
)
http.add_argument(
    "--http-header",
    metavar="KEY=VALUE",
    type=keyvalue,
    action="append",
    help="""
    A header to add to each HTTP request.

    Can be repeated to add multiple headers.
    """
)
http.add_argument(
    "--http-query-param",
    metavar="KEY=VALUE",
    type=keyvalue,
    action="append",
    help="""
    A query parameter to add to each HTTP request.

    Can be repeated to add multiple query parameters.
    """
)
http.add_argument(
    "--http-ignore-env",
    action="store_true",
    help="""
    Ignore HTTP settings set in the environment such as environment
    variables (HTTP_PROXY, etc) or ~/.netrc authentication.
    """
)
http.add_argument(
    "--http-no-ssl-verify",
    action="store_true",
    help="""
    Don't attempt to verify SSL certificates.

    Usually a bad idea, only use this if you know what you're doing.
    """
)
http.add_argument(
    "--http-ssl-cert",
    metavar="FILENAME",
    help="""
    SSL certificate to use.

    Expects a .pem file.
    """
)
http.add_argument(
    "--http-ssl-cert-crt-key",
    metavar=("CRT_FILENAME", "KEY_FILENAME"),
    nargs=2,
    help="""
    SSL certificate to use.

    Expects a .crt and a .key file.
    """
)
http.add_argument(
    "--http-timeout",
    metavar="TIMEOUT",
    type=num(float, min=0),
    help="""
    General timeout used by all HTTP requests except the ones covered
    by other options.

    Default is 20.0.
    """
)


plugin = parser.add_argument_group("Plugin options")
plugin.add_argument(
    "--plugin-dirs",
    metavar="DIRECTORY",
    type=comma_list,
    help="""
    Attempts to load plugins from these directories.

    Multiple directories can be used by separating them with a
    semi-colon.
    """
)
plugin.add_argument(
    "--twitch-oauth-token",
    metavar="TOKEN",
    help="""
    An OAuth token to use for Twitch authentication.
    Use --twitch-oauth-authenticate to create a token.
    """
)
plugin.add_argument(
    "--twitch-oauth-authenticate",
    action="store_true",
    help="""
    Open a web browser where you can grant Streamlink access
    to your Twitch account which creates a token for use with
    --twitch-oauth-token.
    """
)
plugin.add_argument(
    "--twitch-cookie",
    metavar="COOKIES",
    help="""
    Twitch cookies to authenticate to allow access to subscription channels.

    Example:

      "_twitch_session_id=xxxxxx; persistent=xxxxx"

    Note: This method is the old and clunky way of authenticating with
    Twitch, using --twitch-oauth-authenticate is the recommended and
    simpler way of doing it now.

    """
)
plugin.add_argument(
    "--twitch-disable-hosting",
    action="store_true",
    help="""
    Do not open the stream if the target channel is hosting another channel.
    """
)
plugin.add_argument(
    "--ustream-password",
    metavar="PASSWORD",
    help="""
    A password to access password protected UStream.tv channels.
    """
)
plugin.add_argument(
    "--crunchyroll-username",
    metavar="USERNAME",
    help="""
    A Crunchyroll username to allow access to restricted streams.
    """
)
plugin.add_argument(
    "--crunchyroll-password",
    metavar="PASSWORD",
    nargs="?",
    const=True,
    default=None,
    help="""
    A Crunchyroll password for use with --crunchyroll-username.

    If left blank you will be prompted.
    """
)
plugin.add_argument(
    "--crunchyroll-purge-credentials",
    action="store_true",
    help="""
    Purge cached Crunchyroll credentials to initiate a new session
    and reauthenticate.
    """
)
plugin.add_argument(
    "--crunchyroll-locale",
    metavar="LOCALE",
    help="""
    Indicate which locale to use for Crunchyroll subtitles.

    The locale is formatted as [language_code]_[country_code], by default
    en_US is used.
    """
)
plugin.add_argument(
    "--livestation-email",
    metavar="EMAIL",
    help="""
    A Livestation account email to access restricted or premium
    quality streams.
    """
)
plugin.add_argument(
    "--livestation-password",
    metavar="PASSWORD",
    help="""
    A Livestation account password to use with --livestation-email.
    """
)


# Deprecated options
stream.add_argument(
    "--best-stream-default",
    action="store_true",
    help=argparse.SUPPRESS
)
player.add_argument(
    "-q", "--quiet-player",
    action="store_true",
    help=argparse.SUPPRESS
)
transport.add_argument(
    "--hds-fragment-buffer",
    type=int,
    metavar="fragments",
    help=argparse.SUPPRESS
)
plugin.add_argument(
    "--jtv-legacy-names", "--twitch-legacy-names",
    action="store_true",
    help=argparse.SUPPRESS
)
plugin.add_argument(
    "--gomtv-cookie",
    metavar="cookie",
    help=argparse.SUPPRESS
)
plugin.add_argument(
    "--gomtv-username",
    metavar="username",
    help=argparse.SUPPRESS
)
plugin.add_argument(
    "--gomtv-password",
    metavar="password",
    nargs="?",
    const=True,
    default=None,
    help=argparse.SUPPRESS
)
plugin.add_argument(
    "--jtv-cookie",
    help=argparse.SUPPRESS
)
plugin.add_argument(
    "--jtv-password", "--twitch-password",
    help=argparse.SUPPRESS
)
http.add_argument(
    "--http-cookies",
    metavar="COOKIES",
    help=argparse.SUPPRESS
)
http.add_argument(
    "--http-headers",
    metavar="HEADERS",
    help=argparse.SUPPRESS
)
http.add_argument(
    "--http-query-params",
    metavar="PARAMS",
    help=argparse.SUPPRESS
)

__all__ = ["parser"]
