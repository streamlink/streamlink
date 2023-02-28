import argparse
import numbers
import re
from string import printable
from textwrap import dedent
from typing import Any, Callable, Dict, List, Optional, Tuple

from streamlink import __version__ as streamlink_version, logger
from streamlink.session import Streamlink
from streamlink.utils.args import boolean, comma_list, comma_list_filter, filesize, keyvalue, num
from streamlink.utils.times import hours_minutes_seconds
from streamlink_cli.constants import (
    PLAYER_ARGS_INPUT_DEFAULT,
    PLAYER_ARGS_INPUT_FALLBACK,
    STREAM_PASSTHROUGH,
    SUPPORTED_PLAYERS,
)
from streamlink_cli.utils import find_default_player


_printable_re = re.compile(r"[{0}]".format(printable))
_option_re = re.compile(r"""
    (?P<name>[A-z-]+) # A option name, valid characters are A to z and dash.
    \s*
    (?P<op>=)? # Separating the option and the value with a equals sign is
               # common, but optional.
    \s*
    (?P<value>.*) # The value, anything goes.
""", re.VERBOSE)


class ArgumentParser(argparse.ArgumentParser):
    # noinspection PyUnresolvedReferences,PyProtectedMember
    NESTED_ARGUMENT_GROUPS: Dict[Optional[argparse._ArgumentGroup], List[argparse._ArgumentGroup]]

    def __init__(self, *args, **kwargs):
        self.NESTED_ARGUMENT_GROUPS = {}
        super().__init__(*args, **kwargs)

    # noinspection PyUnresolvedReferences,PyProtectedMember
    def add_argument_group(
        self,
        *args,
        parent: Optional[argparse._ArgumentGroup] = None,
        **kwargs,
    ) -> argparse._ArgumentGroup:
        group = super().add_argument_group(*args, **kwargs)
        if parent not in self.NESTED_ARGUMENT_GROUPS:
            self.NESTED_ARGUMENT_GROUPS[parent] = [group]
        else:
            self.NESTED_ARGUMENT_GROUPS[parent].append(group)
        return group

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
            yield f"--{name}={value}"
        elif name:
            yield f"--{name}"

    def _match_argument(self, action, arg_strings_pattern):
        # - https://github.com/streamlink/streamlink/issues/971
        # - https://bugs.python.org/issue9334

        # match the pattern for this action to the arg strings
        nargs_pattern = self._get_nargs_pattern(action)
        match = argparse._re.match(nargs_pattern, arg_strings_pattern)

        # if no match, see if we can emulate optparse and return the
        # required number of arguments regardless of their values
        if match is None:
            nargs = action.nargs if action.nargs is not None else 1
            if isinstance(nargs, numbers.Number) and len(arg_strings_pattern) >= nargs:
                return nargs

        # raise an exception if we weren't able to find a match
        if match is None:
            nargs_errors = {
                None: argparse._("expected one argument"),
                argparse.OPTIONAL: argparse._("expected at most one argument"),
                argparse.ONE_OR_MORE: argparse._("expected at least one argument"),
            }
            default = argparse.ngettext("expected %s argument",
                                        "expected %s arguments",
                                        action.nargs) % action.nargs
            msg = nargs_errors.get(action.nargs, default)
            raise argparse.ArgumentError(action, msg)

        # return the number of arguments matched
        return len(match.group(1))

    # fix `--help` not including nested argument groups
    def format_help(self):
        formatter = self._get_formatter()

        # usage
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)

        # description
        formatter.add_text(self.description)

        def format_group(parent):
            if parent not in self.NESTED_ARGUMENT_GROUPS:
                return
            # positionals, optionals and user-defined groups
            for action_group in self.NESTED_ARGUMENT_GROUPS[parent]:
                formatter.start_section(action_group.title)
                formatter.add_text(action_group.description)
                formatter.add_arguments(action_group._group_actions)
                format_group(action_group)
                formatter.end_section()

        format_group(None)

        # epilog
        formatter.add_text(self.epilog)

        # determine help from format above
        return formatter.format_help()


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
        super().__init__(*args, **kwargs)

    def _split_lines(self, text, width):
        return f"{dedent(text).strip()}\n\n".splitlines()


def build_parser():
    parser = ArgumentParser(
        prog="streamlink",
        fromfile_prefix_chars="@",
        formatter_class=HelpFormatter,
        add_help=False,
        usage="%(prog)s [OPTIONS] <URL> [STREAM]",
        description=dedent("""
        Streamlink is a command-line utility that extracts streams from various
        services and pipes them into a video player of choice.
        """),
        epilog=dedent("""
        For more in-depth documentation see:
          https://streamlink.github.io

        Please report broken plugins or bugs to the issue tracker on Github:
          https://github.com/streamlink/streamlink/issues
        """),
    )

    positional = parser.add_argument_group("Positional arguments")
    positional.add_argument(
        "url",
        metavar="URL",
        nargs="?",
        help="""
        A URL to attempt to extract streams from.

        Usually, the protocol of http(s) URLs can be omitted (`https://`),
        depending on the implementation of the plugin being used.

        Alternatively, the URL can also be specified by using the --url option.
        """,
    )
    positional.add_argument(
        "stream",
        metavar="STREAM",
        nargs="?",
        type=comma_list,
        help="""
        Stream to play.

        Use `best` or `worst` for selecting the highest or lowest available
        quality.

        Fallback streams can be specified by using a comma-separated list:

          "720p,480p,best"

        If no stream is specified and --default-stream is not used, then a list
        of available streams will be printed.
        """,
    )

    general = parser.add_argument_group("General options")
    general.add_argument(
        "-h", "--help",
        action="store_true",
        help="""
        Show this help message and exit.
        """,
    )
    general.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {streamlink_version}",
        help="""
        Show version number and exit.
        """,
    )
    general.add_argument(
        "--plugins",
        action="store_true",
        help="""
        Print a list of all currently installed plugins.
        """,
    )
    general.add_argument(
        "--plugin-dirs",
        metavar="DIRECTORY",
        type=comma_list,
        help="""
        Attempts to load plugins from these directories.

        Multiple directories can be used by separating them with a comma.
        """,
    )
    general.add_argument(
        "--can-handle-url",
        metavar="URL",
        help="""
        Check if Streamlink has a plugin that can handle the specified URL.

        Returns status code `1` for false and `0` for true.

        Useful for external scripting.
        """,
    )
    general.add_argument(
        "--can-handle-url-no-redirect",
        metavar="URL",
        help="""
        Same as --can-handle-url but without following redirects when looking up
        the URL.
        """,
    )
    general.add_argument(
        "--config",
        action="append",
        metavar="FILENAME",
        help="""
        Load options from this config file.

        Can be repeated to load multiple files, in which case the options are
        merged on top of each other where the last config has highest priority.
        """,
    )
    general.add_argument(
        "-l", "--loglevel",
        metavar="LEVEL",
        choices=logger.levels,
        default="info",
        help=f"""
        Set the log message threshold.

        Valid levels are, in order of increasing verbosity:

        {', '.join([f'`{level}`' for level in logger.levels])}

        Default is "info".
        """,
    )
    general.add_argument(
        "--logfile",
        metavar="FILE",
        help="""
        Append log output to `FILE` instead of writing to stdout/stderr.

        User prompts and download progress won't be written to `FILE`.

        A value of `-` (dash) will set the file name to an ISO8601-like string
        and will choose the following default log directories.

        Windows:

          %%TEMP%%\\streamlink\\logs

        macOS:

          ${HOME}/Library/Logs/streamlink

        Linux/BSD:

          ${XDG_STATE_HOME:-${HOME}/.local/state}/streamlink/logs
        """,
    )
    general.add_argument(
        "-Q", "--quiet",
        action="store_true",
        help="""
        Hide all log output.

        Alias for `--loglevel none`.
        """,
    )
    general.add_argument(
        "-j", "--json",
        action="store_true",
        help="""
        Output JSON representations instead of the normal text output.

        Useful for external scripting.
        """,
    )
    general.add_argument(
        "--auto-version-check",
        type=boolean,
        metavar="{yes,true,1,on,no,false,0,off}",
        default=False,
        help="""
        Enable or disable the automatic check for a new version of Streamlink.

        Default is "no".
        """,
    )
    general.add_argument(
        "--version-check",
        action="store_true",
        help="""
        Runs a version check and exits.
        """,
    )
    general.add_argument(
        "--locale",
        type=str,
        metavar="LOCALE",
        help="""
        The preferred locale setting, for selecting the preferred subtitle and
        audio language.

        The locale is formatted as `[language_code]_[country_code]`, eg. `en_US` or
        `es_ES`.

        Default is system locale.
        """,
    )
    general.add_argument(
        "--interface",
        type=str,
        metavar="INTERFACE",
        help="""
        Set the network interface.
        """,
    )
    general.add_argument(
        "-4", "--ipv4",
        action="store_true",
        help="""
        Resolve address names to IPv4 only. This option overrides --ipv6.
        """,
    )
    general.add_argument(
        "-6", "--ipv6",
        action="store_true",
        help="""
        Resolve address names to IPv6 only. This option overrides --ipv4.
        """,
    )

    player = parser.add_argument_group("Player options")
    player.add_argument(
        "-p", "--player",
        metavar="COMMAND",
        default=find_default_player(),
        help="""
        Player to feed stream data to. By default, VLC will be used if it can be
        found in its default location.

        This is a shell-like syntax to support using a specific player:

          %(prog)s --player=vlc <url> [stream]

        Absolute or relative paths can also be passed via this option in the
        event the player's executable can not be resolved:

          %(prog)s --player=/path/to/vlc <url> [stream]
          %(prog)s --player=./vlc-player/vlc <url> [stream]

        To use a player that is located in a path with spaces you must quote the
        parameter or its value:

          %(prog)s "--player=/path/with spaces/vlc" <url> [stream]
          %(prog)s --player "C:\\path\\with spaces\\mpc-hc64.exe" <url> [stream]

        Options may also be passed to the player. For example:

          %(prog)s --player "vlc --file-caching=5000" <url> [stream]

        As an alternative to this, see the --player-args parameter, which does
        not log any custom player arguments.
        """,
    )
    player.add_argument(
        "-a", "--player-args",
        metavar="ARGUMENTS",
        default="",
        help=f"""
        This option allows you to customize the default arguments which are put
        together with the value of --player to create a command to execute.

        It's usually enough to only use --player instead of this unless you need
        to add arguments after the player's input argument or if you don't want
        any of the player arguments to be logged.

        The value can contain formatting variables surrounded by curly braces,
        `{{` and `}}`. If you need to include a brace character, it can be escaped
        by doubling, e.g. `{{{{` and `}}}}`.

        Formatting variables available:

        {{{PLAYER_ARGS_INPUT_DEFAULT}}}
            This is the input that the player will use. For standard input (stdin),
            it is `-` (dash), but it can also be a URL, depending on the options used.

        {{{PLAYER_ARGS_INPUT_FALLBACK}}}
            The old fallback variable name with the same functionality.

        Example:

          %(prog)s -p vlc -a "--play-and-exit {{{PLAYER_ARGS_INPUT_DEFAULT}}}" <url> [stream]

        Note: When neither of the variables are found, `{{{PLAYER_ARGS_INPUT_DEFAULT}}}`
        will be appended to the whole parameter value, to ensure that the player
        always receives an input argument.
        """,
    )
    player.add_argument(
        "-v", "--verbose-player",
        action="store_true",
        help="""
        Allow the player to display its console output.
        """,
    )
    player.add_argument(
        "-n", "--player-fifo", "--fifo",
        action="store_true",
        help="""
        Make the player read the stream through a named pipe instead of the
        stdin pipe.
        """,
    )
    player.add_argument(
        "--player-http",
        action="store_true",
        help="""
        Make the player read the stream through HTTP instead of the stdin pipe.
        """,
    )
    player.add_argument(
        "--player-continuous-http",
        action="store_true",
        help="""
        Make the player read the stream through HTTP, but unlike --player-http
        it will continuously try to open the stream if the player requests it.

        This makes it possible to handle stream disconnects if your player is
        capable of reconnecting to a HTTP stream. This is usually done by
        setting your player to a "repeat mode".
        """,
    )
    player.add_argument(
        "--player-external-http",
        action="store_true",
        help="""
        Serve stream data through HTTP without running any player. This is
        useful to allow external devices like smartphones or streaming boxes to
        watch streams they wouldn't be able to otherwise.

        The default behavior is similar to the --player-continuous-http option,
        but no player program will be started, and the server will listen on all available
        connections instead of just in the local (loopback) interface.

        Optionally, the --player-external-http-continuous option allows for disabling
        the continuous run-mode, so that Streamlink will stop when the stream ends.

        The URLs that can be used to access the stream will be printed to the
        console, and the server can be interrupted using CTRL-C.
        """,
    )
    player.add_argument(
        "--player-external-http-continuous",
        type=boolean,
        metavar="{yes,true,1,on,no,false,0,off}",
        default=True,
        help="""
        Set the run-mode of --player-external-http to continuous or non-continuous.

        In the continuous run-mode, Streamlink will keep running after the stream has ended
        and will wait for the next HTTP request being made unless it gets shut down via CTRL-C.

        If set to non-continuous, Streamlink will stop once the stream has ended.

        Default is true.
        """,
    )
    player.add_argument(
        "--player-external-http-port",
        metavar="PORT",
        type=num(int, min=0, max=65535),
        default=0,
        help="""
        A fixed port to use for the external HTTP server if that mode is
        enabled. Omit or set to `0` to use a random high ( >1024) port.
        """,
    )
    player.add_argument(
        "--player-passthrough",
        metavar="TYPES",
        type=comma_list_filter(STREAM_PASSTHROUGH),
        default=[],
        help="""
        A comma-delimited list of stream types to pass to the player as a URL to
        let it handle the transport of the stream instead.

        Stream types that can be converted into a playable URL are:

        - {0}

        Make sure your player can handle the stream type when using this.
        """.format("\n        - ".join(STREAM_PASSTHROUGH)),
    )
    player.add_argument(
        "--player-no-close",
        action="store_true",
        help="""
        By default Streamlink will close the player when the stream
        ends. This is to avoid "dead" GUI players lingering after a
        stream ends.

        It does however have the side-effect of sometimes closing a
        player before it has played back all of its cached data.

        This option will instead let the player decide when to exit.
        """,
    )
    player.add_argument(
        "-t", "--title",
        metavar="TITLE",
        help=f"""
        Change the title of the video player's window.

        Please see the "Metadata variables" section of Streamlink's CLI documentation for all available metadata variables.

        This option is only supported for the following players: {', '.join(sorted(SUPPORTED_PLAYERS.keys()))}

        VLC specific information:
            VLC does support special formatting variables on its own:
            https://wiki.videolan.org/Documentation:Format_String/

            These variables are accessible in the --title option by adding a backslash
            in front of the dollar sign which VLC uses as its formatting character.

            For example, to put the current date in your VLC window title,
            the string `\\$A` could be inserted inside the --title string.

        Example:

            %(prog)s -p mpv --title "{{author}} - {{category}} - {{title}}" <URL> [STREAM]
        """,
    )

    output = parser.add_argument_group("File output options")
    output.add_argument(
        "-o", "--output",
        metavar="FILENAME",
        help="""
        Write stream data to `FILENAME` instead of playing it. If `FILENAME` is set to `-` (dash), then the stream data will be
        written to stdout, similar to the --stdout argument.

        Non-existent directories and subdirectories will be created if they do not exist, if filesystem permissions allow.

        You will be prompted if the file already exists.

        Please see the "Metadata variables" section of Streamlink's CLI documentation for all available metadata variables.

        Unsupported characters in substituted variables will be replaced with an underscore.

        Example:

            %(prog)s --output "~/recordings/{author}/{category}/{id}-{time:%%Y%%m%%d%%H%%M%%S}.ts" <URL> [STREAM]
        """,
    )
    output.add_argument(
        "-f", "--force",
        action="store_true",
        help="""
        When using --output or --record, always write to file even if it already exists (overwrite).
        """,
    )
    output.add_argument(
        "--force-progress",
        action="store_true",
        help="""
        When using --output or --record,
        show the download progress bar even if there is no terminal.
        """,
    )
    output.add_argument(
        "-O", "--stdout",
        action="store_true",
        help="""
        Write stream data to stdout instead of playing it.
        """,
    )
    output.add_argument(
        "-r", "--record",
        metavar="FILENAME",
        help="""
        Open the stream in the player, while at the same time writing it to `FILENAME`. If `FILENAME` is set to `-` (dash),
        then the stream data will be written to stdout, similar to the --stdout argument, while still opening the player.

        Non-existent directories and subdirectories will be created if they do not exist, if filesystem permissions allow.

        You will be prompted if the file already exists.

        Please see the "Metadata variables" section of Streamlink's CLI documentation for all available metadata variables.

        Unsupported characters in substituted variables will be replaced with an underscore.

        Example:

            %(prog)s --record "~/recordings/{author}/{category}/{id}-{time:%%Y%%m%%d%%H%%M%%S}.ts" <URL> [STREAM]
        """,
    )
    output.add_argument(
        "-R", "--record-and-pipe",
        metavar="FILENAME",
        help="""
        Write stream data to stdout, while at the same time writing it to `FILENAME`.

        Non-existent directories and subdirectories will be created if they do not exist, if filesystem permissions allow.

        You will be prompted if the file already exists.

        Please see the "Metadata variables" section of Streamlink's CLI documentation for all available metadata variables.

        Unsupported characters in substituted variables will be replaced with an underscore.

        Example:

            %(prog)s --record-and-pipe "~/recordings/{author}/{category}/{id}-{time:%%Y%%m%%d%%H%%M%%S}.ts" <URL> [STREAM]
        """,
    )
    output.add_argument(
        "--fs-safe-rules",
        choices=["POSIX", "Windows"],
        type=str,
        help="""
        The rules used to make formatting variables filesystem-safe are chosen
        automatically according to the type of system in use. This overrides
        the automatic detection.

        Intended for use when Streamlink is running on a UNIX-like OS but writing
        to Windows filesystems such as NTFS; USB devices using VFAT or exFAT; CIFS
        shares that are enforcing Windows filename limitations, etc.

        These characters are replaced with an underscore for the rules in use:

        - POSIX: `\\x00-\\x1F /`
        - Windows: `\\x00-\\x1F \\x7F " * / : < > ? \\ |`
        """,
    )

    stream = parser.add_argument_group("Stream options")
    stream.add_argument(
        "--url",
        dest="url_param",
        metavar="URL",
        help="""
        A URL to attempt to extract streams from.

        Usually, the protocol of http(s) URLs can be omitted (`https://`),
        depending on the implementation of the plugin being used.

        This is an alternative to setting the URL using a positional argument
        and can be useful if set in a config file.
        """,
    )
    stream.add_argument(
        "--default-stream",
        type=comma_list,
        metavar="STREAM",
        help="""
        Stream to play.

        Use `best` or `worst` for selecting the highest or lowest available
        quality.

        Fallback streams can be specified by using a comma-separated list:

          "720p,480p,best"

        This is an alternative to setting the stream using a positional argument
        and can be useful if set in a config file.
        """,
    )
    stream.add_argument(
        "--stream-url",
        action="store_true",
        help="""
        If possible, translate the resolved stream to a URL and print it.
        """,
    )
    stream.add_argument(
        "--retry-streams",
        metavar="DELAY",
        type=num(float, min=0),
        help="""
        Retry fetching the list of available streams until streams are found
        while waiting `DELAY` second(s) between each attempt. If unset, only one
        attempt will be made to fetch the list of streams available.

        The number of fetch retry attempts can be capped with --retry-max.
        """,
    )
    stream.add_argument(
        "--retry-max",
        metavar="COUNT",
        type=num(int, min=-1),
        help="""
        When using --retry-streams, stop retrying the fetch after `COUNT` retry
        attempt(s). Fetch will retry infinitely if `COUNT` is zero or unset.

        If --retry-max is set without setting --retry-streams, the delay between
        retries will default to 1 second.
        """,
    )
    stream.add_argument(
        "--retry-open",
        metavar="ATTEMPTS",
        type=num(int, min=0),
        default=1,
        help="""
        After a successful fetch, try `ATTEMPTS` time(s) to open the stream until
        giving up.

        Default is 1.
        """,
    )
    stream.add_argument(
        "--stream-types", "--stream-priority",
        metavar="TYPES",
        type=comma_list,
        help="""
        A comma-delimited list of stream types to allow.

        The order will be used to separate streams when there are multiple
        streams with the same name but different stream types. Any stream type
        not listed will be omitted from the available streams list.  An `*` (asterisk) can
        be used as a wildcard to match any other type of stream, eg. muxed-stream.

        Default is "hls,http,*".
        """,
    )
    stream.add_argument(
        "--stream-sorting-excludes",
        metavar="STREAMS",
        type=comma_list,
        help="""
        Fine tune the `best` and `worst` stream name synonyms by excluding unwanted streams.

        If all of the available streams get excluded, `best` and `worst` will become
        inaccessible and new special stream synonyms `best-unfiltered` and `worst-unfiltered`
        can be used as a fallback selection method.

        Uses a filter expression in the format:

          [operator]<value>

        Valid operators are `>`, `>=`, `<` and `<=`. If no operator is specified then
        equality is tested.

        For example this will exclude streams ranked higher than "480p":

          --stream-sorting-excludes ">480p"

        Multiple filters can be used by separating each expression with a comma.

        For example this will exclude streams from two quality types:

          --stream-sorting-excludes ">480p,>medium"

        """,
    )

    transport = parser.add_argument_group("Stream transport options")
    transport_hls = parser.add_argument_group("HLS options", parent=transport)
    transport_dash = parser.add_argument_group("DASH options", parent=transport)
    transport_ffmpeg = parser.add_argument_group("FFmpeg options", parent=transport)

    transport.add_argument(
        "--ringbuffer-size",
        metavar="SIZE",
        type=filesize,
        help="""
        The maximum size of the ringbuffer. Mega- or kilobytes can be specified via the M or K suffix respectively.

        The ringbuffer is used as a temporary storage between the stream and the player.
        This allows Streamlink to download the stream faster than the player which reads the data from the ringbuffer.

        The smaller the size of the ringbuffer, the higher the chance of the player buffering if the download speed decreases,
        and the higher the size, the more data can be use as a storage to recover from volatile download speeds.

        Most players have their own additional cache and will read the ringbuffer's content as soon as data is available.
        If the player stops reading data while playback is paused, Streamlink will continue to download the stream in the
        background as long as the ringbuffer doesn't get full.

        Default is "16M".

        Note: A smaller size is recommended on lower end systems (such as Raspberry Pi) when playing stream types that require
        some extra processing to avoid unnecessary background processing.
        """,
    )
    transport.add_argument(
        "--stream-segment-attempts",
        type=num(int, min=0),
        metavar="ATTEMPTS",
        help="""
        How many attempts should be done to download each segment before giving up.

        This applies to all different kinds of segmented stream types, such as DASH, HLS, etc.

        Default is 3.
        """,
    )
    transport.add_argument(
        "--stream-segment-threads",
        type=num(int, max=10),
        metavar="THREADS",
        help="""
        The size of the thread pool used to download segments. Minimum value is `1` and maximum is `10`.

        This applies to all different kinds of segmented stream types, such as DASH, HLS, etc.

        Default is 1.
        """,
    )
    transport.add_argument(
        "--stream-segment-timeout",
        type=num(float, min=0),
        metavar="TIMEOUT",
        help="""
        Segment connect and read timeout.

        This applies to all different kinds of segmented stream types, such as DASH, HLS, etc.

        Default is 10.0.
        """,
    )
    transport.add_argument(
        "--stream-timeout",
        type=num(float, min=0),
        metavar="TIMEOUT",
        help="""
        Timeout for reading data from streams.

        This applies to all different kinds of stream types, such as DASH, HLS, HTTP, etc.

        Default is 60.0.
        """,
    )
    transport.add_argument(
        "--mux-subtitles",
        action="store_true",
        help="""
        Automatically mux available subtitles into the output stream.

        Needs to be supported by the used plugin.
        """,
    )

    transport_hls.add_argument(
        "--hls-live-edge",
        type=num(int, min=0),
        metavar="SEGMENTS",
        help="""
        Number of segments from the live stream's current live position to begin streaming.
        The size or length of each segment is determined by the streaming provider.

        Lower values will decrease the latency, but will also increase the chance of buffering, as there is less time for
        Streamlink to download segments and write their data to the output buffer. The number of parallel segment downloads
        can be set with --stream-segment-threads and the HLS playlist reload time to fetch and queue new segments can be
        overridden with --hls-playlist-reload-time.

        Default is 3.

        Note: During live playback, the caching/buffering settings of the used player will add additional latency. To adjust
        this, please refer to the player's own documentation for the required configuration. Player parameters can be set via
        --player-args.
        """,
    )
    transport_hls.add_argument(
        "--hls-segment-stream-data",
        action="store_true",
        help="""
        Immediately write segment data into output buffer while downloading.
        """,
    )
    transport_hls.add_argument(
        "--hls-playlist-reload-attempts",
        type=num(int, min=0),
        metavar="ATTEMPTS",
        help="""
        Max number of attempts when reloading the HLS playlist before giving up.

        Default is 3.
        """,
    )
    transport_hls.add_argument(
        "--hls-playlist-reload-time",
        metavar="TIME",
        help="""
        Set a custom HLS playlist reload time value, either in seconds
        or by using one of the following keywords:

        - segment: The duration of the last segment in the current playlist
        - live-edge: The sum of segment durations of the live edge value minus one
        - default: The playlist's target duration metadata

        Default is default.
        """,
    )
    transport_hls.add_argument(
        "--hls-segment-ignore-names",
        metavar="NAMES",
        type=comma_list,
        help="""
        A comma-delimited list of segment names that will get filtered out.

        Example: --hls-segment-ignore-names 000,001,002

        This will ignore every segment that ends with 000.ts, 001.ts and 002.ts

        Default is None.
        """,
    )
    transport_hls.add_argument(
        "--hls-segment-key-uri",
        metavar="URI",
        type=str,
        help="""
        Override the segment encryption key URIs for encrypted streams.

        The value can be templated using the following variables, which will be
        replaced with their respective part from the source segment URI:

          {url} {scheme} {netloc} {path} {query}

        Examples:

          --hls-segment-key-uri "https://example.com/hls/encryption_key"
          --hls-segment-key-uri "{scheme}://1.2.3.4{path}{query}"
          --hls-segment-key-uri "{scheme}://{netloc}/custom/path/to/key"

        Default is None.
        """,
    )
    transport_hls.add_argument(
        "--hls-audio-select",
        type=comma_list,
        metavar="CODE",
        help="""
        Selects a specific audio source or sources, by language code or name,
        when multiple audio sources are available. Can be `*` (asterisk) to download all
        audio sources.

        Examples:

          --hls-audio-select "English,German"
          --hls-audio-select "en,de"
          --hls-audio-select "*"

        Note: This is only useful in special circumstances where the regular
        locale option fails, such as when multiple sources of the same language
        exists.
        """,
    )
    transport_hls.add_argument(
        "--hls-start-offset",
        type=hours_minutes_seconds,
        metavar="[HH:]MM:SS",
        default=None,
        help="""
        Amount of time to skip from the beginning of the stream. For live
        streams, this is a negative offset from the end of the stream (rewind).

        Default is 00:00:00.
        """,
    )
    transport_hls.add_argument(
        "--hls-duration",
        type=hours_minutes_seconds,
        metavar="[HH:]MM:SS",
        default=None,
        help="""
        Limit the playback duration, useful for watching segments of a stream.
        The actual duration may be slightly longer, as it is rounded to the
        nearest HLS segment.

        Default is unlimited.
        """,
    )
    transport_hls.add_argument(
        "--hls-live-restart",
        action="store_true",
        help="""
        Skip to the beginning of a live stream, or as far back as possible.
        """,
    )

    transport_dash.add_argument(
        "--dash-manifest-reload-attempts",
        type=num(int, min=0),
        metavar="ATTEMPTS",
        help="""
        Max number of attempts when reloading the DASH manifest before giving up.

        Default is 3.
        """,
    )

    transport_hls.add_argument("--hls-segment-attempts", help=argparse.SUPPRESS)
    transport_hls.add_argument("--hls-segment-threads", help=argparse.SUPPRESS)
    transport_hls.add_argument("--hls-segment-timeout", help=argparse.SUPPRESS)
    transport_hls.add_argument("--hls-timeout", help=argparse.SUPPRESS)
    transport.add_argument("--http-stream-timeout", help=argparse.SUPPRESS)

    transport_ffmpeg.add_argument(
        "--ffmpeg-ffmpeg",
        metavar="FILENAME",
        help="""
        FFMPEG is used to access or mux separate video and audio streams. You
        can specify the location of the ffmpeg executable if it is not in your
        `PATH`.

        Example: --ffmpeg-ffmpeg "/usr/local/bin/ffmpeg"
        """,
    )
    transport_ffmpeg.add_argument(
        "--ffmpeg-no-validation",
        action="store_true",
        help="""
        Disable FFmpeg validation and version logging.
        """,
    )
    transport_ffmpeg.add_argument(
        "--ffmpeg-verbose",
        action="store_true",
        help="""
        Write the console output from ffmpeg to the console.
        """,
    )
    transport_ffmpeg.add_argument(
        "--ffmpeg-verbose-path",
        type=str,
        metavar="PATH",
        help="""
        Path to write the output from the ffmpeg console.
        """,
    )
    transport_ffmpeg.add_argument(
        "--ffmpeg-fout",
        type=str,
        metavar="OUTFORMAT",
        help="""
        When muxing streams, set the output format to `OUTFORMAT`.

        Default is "matroska".

        Example: --ffmpeg-fout "mpegts"
        """,
    )
    transport_ffmpeg.add_argument(
        "--ffmpeg-video-transcode",
        metavar="CODEC",
        help="""
        When muxing streams, transcode the video to `CODEC`.

        Default is "copy".

        Example: --ffmpeg-video-transcode "h264"
        """,
    )
    transport_ffmpeg.add_argument(
        "--ffmpeg-audio-transcode",
        metavar="CODEC",
        help="""
        When muxing streams, transcode the audio to `CODEC`.

        Default is "copy".

        Example: --ffmpeg-audio-transcode "aac"
        """,
    )
    transport_ffmpeg.add_argument(
        "--ffmpeg-copyts",
        action="store_true",
        help="""
        Forces the `-copyts` ffmpeg option and does not remove
        the initial start time offset value.
        """,
    )
    transport_ffmpeg.add_argument(
        "--ffmpeg-start-at-zero",
        action="store_true",
        help="""
        Enable the `-start_at_zero` ffmpeg option when using --ffmpeg-copyts.
        """,
    )

    http = parser.add_argument_group("HTTP options")
    http.add_argument(
        "--http-proxy",
        metavar="HTTP_PROXY",
        help="""
        A HTTP proxy to use for all HTTP and HTTPS requests, including WebSocket connections.

        Example: --http-proxy "http://hostname:port/"
        """,
    )
    http.add_argument("--https-proxy", help=argparse.SUPPRESS)
    http.add_argument(
        "--http-cookie",
        metavar="KEY=VALUE",
        type=keyvalue,
        action="append",
        help="""
        A cookie to add to each HTTP request.

        Can be repeated to add multiple cookies.
        """,
    )
    http.add_argument(
        "--http-header",
        metavar="KEY=VALUE",
        type=keyvalue,
        action="append",
        help="""
        A header to add to each HTTP request.

        Can be repeated to add multiple headers.
        """,
    )
    http.add_argument(
        "--http-query-param",
        metavar="KEY=VALUE",
        type=keyvalue,
        action="append",
        help="""
        A query parameter to add to each HTTP request.

        Can be repeated to add multiple query parameters.
        """,
    )
    http.add_argument(
        "--http-ignore-env",
        action="store_true",
        help="""
        Ignore HTTP settings set in the environment such as environment
        variables (`HTTP_PROXY`, etc) or `~/.netrc` authentication.
        """,
    )
    http.add_argument(
        "--http-no-ssl-verify",
        action="store_true",
        help="""
        Don't attempt to verify SSL certificates.

        Usually a bad idea, only use this if you know what you're doing.
        """,
    )
    http.add_argument(
        "--http-disable-dh",
        action="store_true",
        help="""
        Disable Diffie Hellman key exchange

        Usually a bad idea, only use this if you know what you're doing.
        """,
    )
    http.add_argument(
        "--http-ssl-cert",
        metavar="FILENAME",
        help="""
        SSL certificate to use.

        Expects a .pem file.
        """,
    )
    http.add_argument(
        "--http-ssl-cert-crt-key",
        metavar=("CRT_FILENAME", "KEY_FILENAME"),
        nargs=2,
        help="""
        SSL certificate to use.

        Expects a .crt and a .key file.
        """,
    )
    http.add_argument(
        "--http-timeout",
        metavar="TIMEOUT",
        type=num(float, min=0),
        help="""
        General timeout used by all HTTP requests except the ones covered by
        other options.

        Default is 20.0.
        """,
    )

    return parser


def false(_): return False  # noqa: E704


# The order of arguments determines if options get overridden by `Streamlink.set_option()`
_ARGUMENT_TO_SESSIONOPTION: List[Tuple[str, str, Optional[Callable[[Any], Any]]]] = [
    # generic arguments
    ("locale", "locale", None),

    # network arguments
    ("interface", "interface", None),
    ("ipv4", "ipv4", None),
    ("ipv6", "ipv6", None),

    # HTTP session arguments
    ("https_proxy", "https-proxy", None),
    ("http_proxy", "http-proxy", None),
    ("http_cookie", "http-cookies", dict),
    ("http_header", "http-headers", dict),
    ("http_query_param", "http-query-params", dict),
    ("http_ignore_env", "http-trust-env", false),
    ("http_no_ssl_verify", "http-ssl-verify", false),
    ("http_disable_dh", "http-disable-dh", None),
    ("http_ssl_cert", "http-ssl-cert", None),
    ("http_ssl_cert_crt_key", "http-ssl-cert", tuple),
    ("http_timeout", "http-timeout", None),

    # deprecated stream transport arguments (need to be defined first, so following ones can override values)
    ("hls_segment_attempts", "hls-segment-attempts", None),
    ("hls_segment_threads", "hls-segment-threads", None),
    ("hls_segment_timeout", "hls-segment-timeout", None),
    ("hls_timeout", "hls-timeout", None),
    ("http_stream_timeout", "http-stream-timeout", None),

    # stream transport arguments
    ("ringbuffer_size", "ringbuffer-size", None),
    ("mux_subtitles", "mux-subtitles", None),
    ("stream_segment_attempts", "stream-segment-attempts", None),
    ("stream_segment_threads", "stream-segment-threads", None),
    ("stream_segment_timeout", "stream-segment-timeout", None),
    ("stream_timeout", "stream-timeout", None),
    ("hls_live_edge", "hls-live-edge", None),
    ("hls_live_restart", "hls-live-restart", None),
    ("hls_start_offset", "hls-start-offset", None),
    ("hls_duration", "hls-duration", None),
    ("hls_playlist_reload_attempts", "hls-playlist-reload-attempts", None),
    ("hls_playlist_reload_time", "hls-playlist-reload-time", None),
    ("hls_segment_stream_data", "hls-segment-stream-data", None),
    ("hls_segment_ignore_names", "hls-segment-ignore-names", None),
    ("hls_segment_key_uri", "hls-segment-key-uri", None),
    ("hls_audio_select", "hls-audio-select", None),
    ("dash_manifest_reload_attempts", "dash-manifest-reload-attempts", None),
    ("ffmpeg_ffmpeg", "ffmpeg-ffmpeg", None),
    ("ffmpeg_no_validation", "ffmpeg-no-validation", None),
    ("ffmpeg_verbose", "ffmpeg-verbose", None),
    ("ffmpeg_verbose_path", "ffmpeg-verbose-path", None),
    ("ffmpeg_fout", "ffmpeg-fout", None),
    ("ffmpeg_video_transcode", "ffmpeg-video-transcode", None),
    ("ffmpeg_audio_transcode", "ffmpeg-audio-transcode", None),
    ("ffmpeg_copyts", "ffmpeg-copyts", None),
    ("ffmpeg_start_at_zero", "ffmpeg-start-at-zero", None),
]


def setup_session_options(session: Streamlink, args: argparse.Namespace):
    for arg, option, mapper in _ARGUMENT_TO_SESSIONOPTION:
        value = getattr(args, arg)
        if value:
            if mapper is not None:
                value = mapper(value)
            session.set_option(option, value)


__all__ = ["ArgumentParser", "build_parser", "setup_session_options"]
