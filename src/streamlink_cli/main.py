import argparse
import errno
import logging
import os
import platform
import signal
import sys
from collections import OrderedDict
from contextlib import closing
from distutils.version import StrictVersion
from functools import partial
from gettext import gettext
from itertools import chain
from pathlib import Path
from time import sleep
from typing import List

import requests
from socks import __version__ as socks_version
from websocket import __version__ as websocket_version

import streamlink.logger as logger
from streamlink import NoPluginError, PluginError, StreamError, Streamlink, __version__ as streamlink_version
from streamlink.cache import Cache
from streamlink.exceptions import FatalPluginError
from streamlink.plugin import Plugin, PluginOptions
from streamlink.stream import StreamIO, StreamProcess
from streamlink.utils import NamedPipe
from streamlink_cli.argparser import build_parser
from streamlink_cli.compat import DeprecatedPath, is_win32, stdout
from streamlink_cli.console import ConsoleOutput, ConsoleUserInputRequester
from streamlink_cli.constants import CONFIG_FILES, DEFAULT_STREAM_METADATA, LOG_DIR, PLUGIN_DIRS, STREAM_SYNONYMS
from streamlink_cli.output import FileOutput, Output, PlayerOutput
from streamlink_cli.utils import Formatter, HTTPServer, datetime, ignored, progress, stream_to_url

ACCEPTABLE_ERRNO = (errno.EPIPE, errno.EINVAL, errno.ECONNRESET)
try:
    ACCEPTABLE_ERRNO += (errno.WSAECONNABORTED,)
except AttributeError:
    pass  # Not windows
QUIET_OPTIONS = ("json", "stream_url", "subprocess_cmdline", "quiet")

args = None
console: ConsoleOutput = None
output: Output = None
plugin: Plugin = None
stream_fd: StreamIO = None
streamlink: Streamlink = None

log = logging.getLogger("streamlink.cli")


def get_formatter(plugin: Plugin):
    return Formatter(
        {
            "url": lambda: args.url,
            "author": lambda: plugin.get_author(),
            "category": lambda: plugin.get_category(),
            "game": lambda: plugin.get_category(),
            "title": lambda: plugin.get_title(),
            "time": lambda: datetime.now()
        },
        {
            "time": lambda dt, fmt: dt.strftime(fmt)
        }
    )


def check_file_output(filename, force):
    """Checks if file already exists and ask the user if it should
    be overwritten if it does."""

    log.debug("Checking file output")

    if os.path.isfile(filename) and not force:
        if sys.stdin.isatty():
            answer = console.ask(f"File {filename} already exists! Overwrite it? [y/N] ")
            if answer.lower() != "y":
                sys.exit()
        else:
            log.error(f"File {filename} already exists, use --force to overwrite it.")
            sys.exit()

    return FileOutput(filename)


def create_output(formatter: Formatter):
    """Decides where to write the stream.

    Depending on arguments it can be one of these:
     - The stdout pipe
     - A subprocess' stdin pipe
     - A named pipe that the subprocess reads from
     - A regular file

    """

    if (args.output or args.stdout) and (args.record or args.record_and_pipe):
        console.exit("Cannot use record options with other file output options.")

    if args.output:
        if args.output == "-":
            out = FileOutput(fd=stdout)
        else:
            out = check_file_output(formatter.filename(args.output, args.fs_safe_rules), args.force)
    elif args.stdout:
        out = FileOutput(fd=stdout)
    elif args.record_and_pipe:
        record = check_file_output(formatter.filename(args.record_and_pipe, args.fs_safe_rules), args.force)
        out = FileOutput(fd=stdout, record=record)
    else:
        http = namedpipe = record = None

        if not args.player:
            console.exit("The default player (VLC) does not seem to be "
                         "installed. You must specify the path to a player "
                         "executable with --player.")

        if args.player_fifo:
            try:
                namedpipe = NamedPipe()
            except OSError as err:
                console.exit(f"Failed to create pipe: {err}")
        elif args.player_http:
            http = create_http_server()

        if args.record:
            record = check_file_output(formatter.filename(args.record, args.fs_safe_rules), args.force)

        log.info(f"Starting player: {args.player}")

        out = PlayerOutput(
            args.player,
            args=args.player_args,
            quiet=not args.verbose_player,
            kill=not args.player_no_close,
            namedpipe=namedpipe,
            http=http,
            record=record,
            title=formatter.title(args.title, defaults=DEFAULT_STREAM_METADATA) if args.title else args.url
        )

    return out


def create_http_server(*_args, **_kwargs):
    """Creates a HTTP server listening on a given host and port.

    If host is empty, listen on all available interfaces, and if port is 0,
    listen on a random high port.
    """

    try:
        http = HTTPServer()
        http.bind(*_args, **_kwargs)
    except OSError as err:
        console.exit(f"Failed to create HTTP server: {err}")

    return http


def iter_http_requests(server, player):
    """Repeatedly accept HTTP connections on a server.

    Forever if the serving externally, or while a player is running if it is not
    empty.
    """

    while not player or player.running:
        try:
            yield server.open(timeout=2.5)
        except OSError:
            continue


def output_stream_http(plugin, initial_streams, formatter: Formatter, external=False, port=0):
    """Continuously output the stream over HTTP."""
    global output

    if not external:
        if not args.player:
            console.exit("The default player (VLC) does not seem to be "
                         "installed. You must specify the path to a player "
                         "executable with --player.")

        server = create_http_server()
        player = output = PlayerOutput(
            args.player,
            args=args.player_args,
            filename=server.url,
            quiet=not args.verbose_player,
            title=formatter.title(args.title, defaults=DEFAULT_STREAM_METADATA) if args.title else args.url
        )

        try:
            log.info(f"Starting player: {args.player}")
            if player:
                player.open()
        except OSError as err:
            console.exit(f"Failed to start player: {args.player} ({err})")
    else:
        server = create_http_server(host=None, port=port)
        player = None

        log.info("Starting server, access with one of:")
        for url in server.urls:
            log.info(" " + url)

    for req in iter_http_requests(server, player):
        user_agent = req.headers.get("User-Agent") or "unknown player"
        log.info(f"Got HTTP request from {user_agent}")

        stream_fd = prebuffer = None
        while not stream_fd and (not player or player.running):
            try:
                streams = initial_streams or fetch_streams(plugin)
                initial_streams = None

                for stream_name in (resolve_stream_name(streams, s) for s in args.stream):
                    if stream_name in streams:
                        stream = streams[stream_name]
                        break
                else:
                    log.info("Stream not available, will re-fetch streams in 10 sec")
                    sleep(10)
                    continue
            except PluginError as err:
                log.error(f"Unable to fetch new streams: {err}")
                continue

            try:
                log.info(f"Opening stream: {stream_name} ({type(stream).shortname()})")
                stream_fd, prebuffer = open_stream(stream)
            except StreamError as err:
                log.error(err)

        if stream_fd and prebuffer:
            log.debug("Writing stream to player")
            read_stream(stream_fd, server, prebuffer, formatter)

        server.close(True)

    player.close()
    server.close()


def output_stream_passthrough(stream, formatter: Formatter):
    """Prepares a filename to be passed to the player."""
    global output

    filename = f'"{stream_to_url(stream)}"'
    output = PlayerOutput(
        args.player,
        args=args.player_args,
        filename=filename,
        call=True,
        quiet=not args.verbose_player,
        title=formatter.title(args.title, defaults=DEFAULT_STREAM_METADATA) if args.title else args.url
    )

    try:
        log.info(f"Starting player: {args.player}")
        output.open()
    except OSError as err:
        console.exit(f"Failed to start player: {args.player} ({err})")
        return False

    return True


def open_stream(stream):
    """Opens a stream and reads 8192 bytes from it.

    This is useful to check if a stream actually has data
    before opening the output.

    """
    global stream_fd

    # Attempts to open the stream
    try:
        stream_fd = stream.open()
    except StreamError as err:
        raise StreamError(f"Could not open stream: {err}")

    # Read 8192 bytes before proceeding to check for errors.
    # This is to avoid opening the output unnecessarily.
    try:
        log.debug("Pre-buffering 8192 bytes")
        prebuffer = stream_fd.read(8192)
    except OSError as err:
        stream_fd.close()
        raise StreamError(f"Failed to read data from stream: {err}")

    if not prebuffer:
        stream_fd.close()
        raise StreamError("No data returned from stream")

    return stream_fd, prebuffer


def output_stream(stream, formatter: Formatter):
    """Open stream, create output and finally write the stream to output."""
    global output

    success_open = False
    for i in range(args.retry_open):
        try:
            stream_fd, prebuffer = open_stream(stream)
            success_open = True
            break
        except StreamError as err:
            log.error(f"Try {i + 1}/{args.retry_open}: Could not open stream {stream} ({err})")

    if not success_open:
        console.exit(f"Could not open stream {stream}, tried {args.retry_open} times, exiting")

    output = create_output(formatter)

    try:
        output.open()
    except OSError as err:
        if isinstance(output, PlayerOutput):
            console.exit(f"Failed to start player: {args.player} ({err})")
        else:
            console.exit(f"Failed to open output: {output.filename} ({err})")

    with closing(output):
        log.debug("Writing stream to output")
        read_stream(stream_fd, output, prebuffer, formatter)

    return True


def read_stream(stream, output, prebuffer, formatter: Formatter, chunk_size=8192):
    """Reads data from stream and then writes it to the output."""
    is_player = isinstance(output, PlayerOutput)
    is_http = isinstance(output, HTTPServer)
    is_fifo = is_player and output.namedpipe
    show_progress = (
        isinstance(output, FileOutput)
        and output.fd is not stdout
        and (sys.stdout.isatty() or args.force_progress)
    )
    show_record_progress = (
        hasattr(output, "record")
        and isinstance(output.record, FileOutput)
        and output.record.fd is not stdout
        and (sys.stdout.isatty() or args.force_progress)
    )

    stream_iterator = chain(
        [prebuffer],
        iter(partial(stream.read, chunk_size), b"")
    )
    if show_progress:
        stream_iterator = progress(
            stream_iterator,
            prefix=os.path.basename(output.filename)
        )
    elif show_record_progress:
        stream_iterator = progress(
            stream_iterator,
            prefix=os.path.basename(output.record.filename)
        )

    try:
        for data in stream_iterator:
            # We need to check if the player process still exists when
            # using named pipes on Windows since the named pipe is not
            # automatically closed by the player.
            if is_win32 and is_fifo:
                output.player.poll()

                if output.player.returncode is not None:
                    log.info("Player closed")
                    break

            try:
                output.write(data)
            except OSError as err:
                if is_player and err.errno in ACCEPTABLE_ERRNO:
                    log.info("Player closed")
                elif is_http and err.errno in ACCEPTABLE_ERRNO:
                    log.info("HTTP connection closed")
                else:
                    console.exit(f"Error when writing to output: {err}, exiting")

                break
    except OSError as err:
        console.exit(f"Error when reading from stream: {err}, exiting")
    finally:
        stream.close()
        log.info("Stream ended")


def handle_stream(plugin, streams, stream_name):
    """Decides what to do with the selected stream.

    Depending on arguments it can be one of these:
     - Output internal command-line
     - Output JSON represenation
     - Continuously output the stream over HTTP
     - Output stream data to selected output

    """

    stream_name = resolve_stream_name(streams, stream_name)
    stream = streams[stream_name]

    # Print internal command-line if this stream
    # uses a subprocess.
    if args.subprocess_cmdline:
        if isinstance(stream, StreamProcess):
            try:
                cmdline = stream.cmdline()
            except StreamError as err:
                console.exit(err)

            console.msg(cmdline)
        else:
            console.exit("The stream specified cannot be translated to a command")

    # Print JSON representation of the stream
    elif args.json:
        console.msg_json(
            stream,
            metadata=plugin.get_metadata()
        )

    elif args.stream_url:
        try:
            console.msg(stream.to_url())
        except TypeError:
            console.exit("The stream specified cannot be translated to a URL")

    # Output the stream
    else:
        # Find any streams with a '_alt' suffix and attempt
        # to use these in case the main stream is not usable.
        alt_streams = list(filter(lambda k: stream_name + "_alt" in k,
                                  sorted(streams.keys())))
        file_output = args.output or args.stdout

        formatter = get_formatter(plugin)

        for stream_name in [stream_name] + alt_streams:
            stream = streams[stream_name]
            stream_type = type(stream).shortname()

            if stream_type in args.player_passthrough and not file_output:
                log.info(f"Opening stream: {stream_name} ({stream_type})")
                success = output_stream_passthrough(stream, formatter)
            elif args.player_external_http:
                return output_stream_http(plugin, streams, formatter, external=True,
                                          port=args.player_external_http_port)
            elif args.player_continuous_http and not file_output:
                return output_stream_http(plugin, streams, formatter)
            else:
                log.info(f"Opening stream: {stream_name} ({stream_type})")
                success = output_stream(stream, formatter)

            if success:
                break


def fetch_streams(plugin):
    """Fetches streams using correct parameters."""

    return plugin.streams(stream_types=args.stream_types,
                          sorting_excludes=args.stream_sorting_excludes)


def fetch_streams_with_retry(plugin, interval, count):
    """Attempts to fetch streams repeatedly
       until some are returned or limit hit."""

    try:
        streams = fetch_streams(plugin)
    except PluginError as err:
        log.error(err)
        streams = None

    if not streams:
        log.info(f"Waiting for streams, retrying every {interval} second(s)")
    attempts = 0

    while not streams:
        sleep(interval)

        try:
            streams = fetch_streams(plugin)
        except FatalPluginError:
            raise
        except PluginError as err:
            log.error(err)

        if count > 0:
            attempts += 1
            if attempts >= count:
                break

    return streams


def resolve_stream_name(streams, stream_name):
    """Returns the real stream name of a synonym."""

    if stream_name in STREAM_SYNONYMS and stream_name in streams:
        for name, stream in streams.items():
            if stream is streams[stream_name] and name not in STREAM_SYNONYMS:
                return name

    return stream_name


def format_valid_streams(plugin, streams):
    """Formats a dict of streams.

    Filters out synonyms and displays them next to
    the stream they point to.

    Streams are sorted according to their quality
    (based on plugin.stream_weight).

    """

    delimiter = ", "
    validstreams = []

    for name, stream in sorted(streams.items(),
                               key=lambda stream: plugin.stream_weight(stream[0])):
        if name in STREAM_SYNONYMS:
            continue

        def synonymfilter(n):
            return stream is streams[n] and n is not name

        synonyms = list(filter(synonymfilter, streams.keys()))

        if len(synonyms) > 0:
            joined = delimiter.join(synonyms)
            name = f"{name} ({joined})"

        validstreams.append(name)

    return delimiter.join(validstreams)


def handle_url():
    """The URL handler.

    Attempts to resolve the URL to a plugin and then attempts
    to fetch a list of available streams.

    Proceeds to handle stream if user specified a valid one,
    otherwise output list of valid streams.

    """

    try:
        plugin = streamlink.resolve_url(args.url)
        setup_plugin_options(streamlink, plugin)
        log.info(f"Found matching plugin {plugin.module} for URL {args.url}")

        if args.retry_max or args.retry_streams:
            retry_streams = 1
            retry_max = 0
            if args.retry_streams:
                retry_streams = args.retry_streams
            if args.retry_max:
                retry_max = args.retry_max
            streams = fetch_streams_with_retry(plugin, retry_streams,
                                               retry_max)
        else:
            streams = fetch_streams(plugin)
    except NoPluginError:
        console.exit(f"No plugin can handle URL: {args.url}")
    except PluginError as err:
        console.exit(err)

    if not streams:
        console.exit(f"No playable streams found on this URL: {args.url}")

    if args.default_stream and not args.stream and not args.json:
        args.stream = args.default_stream

    if args.stream:
        validstreams = format_valid_streams(plugin, streams)
        for stream_name in args.stream:
            if stream_name in streams:
                log.info(f"Available streams: {validstreams}")
                handle_stream(plugin, streams, stream_name)
                return

        err = f"The specified stream(s) '{', '.join(args.stream)}' could not be found"
        if args.json:
            console.msg_json(
                plugin=plugin.module,
                metadata=plugin.get_metadata(),
                streams=streams,
                error=err
            )
        else:
            console.exit(f"{err}.\n       Available streams: {validstreams}")
    elif args.json:
        console.msg_json(
            plugin=plugin.module,
            metadata=plugin.get_metadata(),
            streams=streams
        )
    elif args.stream_url:
        try:
            console.msg(streams[list(streams)[-1]].to_manifest_url())
        except TypeError:
            console.exit("The stream specified cannot be translated to a URL")
    else:
        validstreams = format_valid_streams(plugin, streams)
        console.msg(f"Available streams: {validstreams}")


def print_plugins():
    """Outputs a list of all plugins Streamlink has loaded."""

    pluginlist = list(streamlink.get_plugins().keys())
    pluginlist_formatted = ", ".join(sorted(pluginlist))

    if args.json:
        console.msg_json(pluginlist)
    else:
        console.msg(f"Loaded plugins: {pluginlist_formatted}")


def load_plugins(dirs: List[Path], showwarning: bool = True):
    """Attempts to load plugins from a list of directories."""
    for directory in dirs:
        if directory.is_dir():
            success = streamlink.load_plugins(str(directory))
            if success and type(directory) is DeprecatedPath:
                log.info(f"Loaded plugins from deprecated path, see CLI docs for how to migrate: {directory}")
        elif showwarning:
            log.warning(f"Plugin path {directory} does not exist or is not a directory!")


def setup_args(parser: argparse.ArgumentParser, config_files: List[Path] = None, ignore_unknown: bool = False):
    """Parses arguments."""
    global args
    arglist = sys.argv[1:]

    # Load arguments from config files
    configs = [f"@{config_file}" for config_file in config_files or []]

    args, unknown = parser.parse_known_args(configs + arglist)
    if unknown and not ignore_unknown:
        msg = gettext("unrecognized arguments: %s")
        parser.error(msg % " ".join(unknown))

    # Force lowercase to allow case-insensitive lookup
    if args.stream:
        args.stream = [stream.lower() for stream in args.stream]

    if not args.url and args.url_param:
        args.url = args.url_param


def setup_config_args(parser, ignore_unknown=False):
    config_files = []

    if args.config:
        # We want the config specified last to get highest priority
        for config_file in map(lambda path: Path(path).expanduser(), reversed(args.config)):
            if config_file.is_file():
                config_files.append(config_file)
    else:
        # Only load first available default config
        for config_file in filter(lambda path: path.is_file(), CONFIG_FILES):
            if type(config_file) is DeprecatedPath:
                log.info(f"Loaded config from deprecated path, see CLI docs for how to migrate: {config_file}")
            config_files.append(config_file)
            break

    if streamlink and args.url:
        # Only load first available plugin config
        with ignored(NoPluginError):
            plugin = streamlink.resolve_url(args.url)
            for config_file in CONFIG_FILES:
                config_file = config_file.with_name(f"{config_file.name}.{plugin.module}")
                if not config_file.is_file():
                    continue
                if type(config_file) is DeprecatedPath:
                    log.info(f"Loaded plugin config from deprecated path, see CLI docs for how to migrate: {config_file}")
                config_files.append(config_file)
                break

    if config_files:
        setup_args(parser, config_files, ignore_unknown=ignore_unknown)


def setup_signals():
    # Handle SIGTERM just like SIGINT
    signal.signal(signal.SIGTERM, signal.default_int_handler)


def setup_http_session():
    """Sets the global HTTP settings, such as proxy and headers."""
    if args.http_proxy:
        streamlink.set_option("http-proxy", args.http_proxy)

    if args.https_proxy:
        streamlink.set_option("https-proxy", args.https_proxy)

    if args.http_cookie:
        streamlink.set_option("http-cookies", dict(args.http_cookie))

    if args.http_header:
        streamlink.set_option("http-headers", dict(args.http_header))

    if args.http_query_param:
        streamlink.set_option("http-query-params", dict(args.http_query_param))

    if args.http_ignore_env:
        streamlink.set_option("http-trust-env", False)

    if args.http_no_ssl_verify:
        streamlink.set_option("http-ssl-verify", False)

    if args.http_disable_dh:
        streamlink.set_option("http-disable-dh", True)

    if args.http_ssl_cert:
        streamlink.set_option("http-ssl-cert", args.http_ssl_cert)

    if args.http_ssl_cert_crt_key:
        streamlink.set_option("http-ssl-cert", tuple(args.http_ssl_cert_crt_key))

    if args.http_timeout:
        streamlink.set_option("http-timeout", args.http_timeout)


def setup_plugins(extra_plugin_dir=None):
    """Loads any additional plugins."""
    load_plugins(PLUGIN_DIRS, showwarning=False)

    if extra_plugin_dir:
        load_plugins([Path(path).expanduser() for path in extra_plugin_dir])


def setup_streamlink():
    """Creates the Streamlink session."""
    global streamlink

    streamlink = Streamlink({"user-input-requester": ConsoleUserInputRequester(console)})


def setup_options():
    """Sets Streamlink options."""
    if args.interface:
        streamlink.set_option("interface", args.interface)
    if args.ipv4:
        streamlink.set_option("ipv4", args.ipv4)
    if args.ipv6:
        streamlink.set_option("ipv6", args.ipv6)

    if args.ringbuffer_size:
        streamlink.set_option("ringbuffer-size", args.ringbuffer_size)
    if args.mux_subtitles:
        streamlink.set_option("mux-subtitles", args.mux_subtitles)

    if args.hds_live_edge:
        streamlink.set_option("hds-live-edge", args.hds_live_edge)

    if args.hls_live_edge:
        streamlink.set_option("hls-live-edge", args.hls_live_edge)
    if args.hls_playlist_reload_attempts:
        streamlink.set_option("hls-playlist-reload-attempts", args.hls_playlist_reload_attempts)
    if args.hls_playlist_reload_time:
        streamlink.set_option("hls-playlist-reload-time", args.hls_playlist_reload_time)
    if args.hls_segment_ignore_names:
        streamlink.set_option("hls-segment-ignore-names", args.hls_segment_ignore_names)
    if args.hls_segment_key_uri:
        streamlink.set_option("hls-segment-key-uri", args.hls_segment_key_uri)
    if args.hls_audio_select:
        streamlink.set_option("hls-audio-select", args.hls_audio_select)
    if args.hls_start_offset:
        streamlink.set_option("hls-start-offset", args.hls_start_offset)
    if args.hls_duration:
        streamlink.set_option("hls-duration", args.hls_duration)
    if args.hls_live_restart:
        streamlink.set_option("hls-live-restart", args.hls_live_restart)

    if args.rtmp_rtmpdump:
        streamlink.set_option("rtmp-rtmpdump", args.rtmp_rtmpdump)
    elif args.rtmpdump:
        streamlink.set_option("rtmp-rtmpdump", args.rtmpdump)
    if args.rtmp_proxy:
        streamlink.set_option("rtmp-proxy", args.rtmp_proxy)

    # deprecated
    if args.hds_segment_attempts:
        streamlink.set_option("hds-segment-attempts", args.hds_segment_attempts)
    if args.hds_segment_threads:
        streamlink.set_option("hds-segment-threads", args.hds_segment_threads)
    if args.hds_segment_timeout:
        streamlink.set_option("hds-segment-timeout", args.hds_segment_timeout)
    if args.hds_timeout:
        streamlink.set_option("hds-timeout", args.hds_timeout)
    if args.hls_segment_attempts:
        streamlink.set_option("hls-segment-attempts", args.hls_segment_attempts)
    if args.hls_segment_threads:
        streamlink.set_option("hls-segment-threads", args.hls_segment_threads)
    if args.hls_segment_timeout:
        streamlink.set_option("hls-segment-timeout", args.hls_segment_timeout)
    if args.hls_timeout:
        streamlink.set_option("hls-timeout", args.hls_timeout)
    if args.http_stream_timeout:
        streamlink.set_option("http-stream-timeout", args.http_stream_timeout)
    if args.rtmp_timeout:
        streamlink.set_option("rtmp-timeout", args.rtmp_timeout)

    # generic stream- arguments take precedence over deprecated stream-type arguments
    if args.stream_segment_attempts:
        streamlink.set_option("stream-segment-attempts", args.stream_segment_attempts)
    if args.stream_segment_threads:
        streamlink.set_option("stream-segment-threads", args.stream_segment_threads)
    if args.stream_segment_timeout:
        streamlink.set_option("stream-segment-timeout", args.stream_segment_timeout)
    if args.stream_timeout:
        streamlink.set_option("stream-timeout", args.stream_timeout)

    if args.ffmpeg_ffmpeg:
        streamlink.set_option("ffmpeg-ffmpeg", args.ffmpeg_ffmpeg)
    if args.ffmpeg_verbose:
        streamlink.set_option("ffmpeg-verbose", args.ffmpeg_verbose)
    if args.ffmpeg_verbose_path:
        streamlink.set_option("ffmpeg-verbose-path", args.ffmpeg_verbose_path)
    if args.ffmpeg_fout:
        streamlink.set_option("ffmpeg-fout", args.ffmpeg_fout)
    if args.ffmpeg_video_transcode:
        streamlink.set_option("ffmpeg-video-transcode", args.ffmpeg_video_transcode)
    if args.ffmpeg_audio_transcode:
        streamlink.set_option("ffmpeg-audio-transcode", args.ffmpeg_audio_transcode)
    if args.ffmpeg_copyts:
        streamlink.set_option("ffmpeg-copyts", args.ffmpeg_copyts)
    if args.ffmpeg_start_at_zero:
        streamlink.set_option("ffmpeg-start-at-zero", args.ffmpeg_start_at_zero)

    streamlink.set_option("subprocess-errorlog", args.subprocess_errorlog)
    streamlink.set_option("subprocess-errorlog-path", args.subprocess_errorlog_path)
    streamlink.set_option("locale", args.locale)


def setup_plugin_args(session, parser):
    """Sets Streamlink plugin options."""

    plugin_args = parser.add_argument_group("Plugin options")
    for pname, plugin in session.plugins.items():
        defaults = {}
        group = plugin_args.add_argument_group(pname.capitalize())

        for parg in plugin.arguments:
            if not parg.is_global:
                group.add_argument(parg.argument_name(pname), **parg.options)
                defaults[parg.dest] = parg.default
            else:
                pargdest = parg.dest
                for action in parser._actions:
                    # find matching global argument
                    if pargdest != action.dest:
                        continue
                    defaults[pargdest] = action.default

                    # add plugin to global argument
                    plugins = getattr(action, "plugins", [])
                    plugins.append(pname)
                    setattr(action, "plugins", plugins)

        plugin.options = PluginOptions(defaults)


def setup_plugin_options(session, plugin):
    """Sets Streamlink plugin options."""
    pname = plugin.module
    required = OrderedDict({})

    for parg in plugin.arguments:
        if parg.options.get("help") == argparse.SUPPRESS:
            continue

        value = getattr(args, parg.dest if parg.is_global else parg.namespace_dest(pname))
        session.set_plugin_option(pname, parg.dest, value)

        if not parg.is_global:
            if parg.required:
                required[parg.name] = parg
            # if the value is set, check to see if any of the required arguments are not set
            if parg.required or value:
                try:
                    for rparg in plugin.arguments.requires(parg.name):
                        required[rparg.name] = rparg
                except RuntimeError:
                    log.error(f"{pname} plugin has a configuration error and the arguments cannot be parsed")
                    break

    if required:
        for req in required.values():
            if not session.get_plugin_option(pname, req.dest):
                prompt = f"{req.prompt or f'Enter {pname} {req.name}'}: "
                session.set_plugin_option(
                    pname,
                    req.dest,
                    console.askpass(prompt) if req.sensitive else console.ask(prompt)
                )


def log_root_warning():
    if hasattr(os, "getuid"):
        if os.geteuid() == 0:
            log.info("streamlink is running as root! Be careful!")


def log_current_versions():
    """Show current installed versions"""
    if not logger.root.isEnabledFor(logging.DEBUG):
        return

    # macOS
    if sys.platform == "darwin":
        os_version = f"macOS {platform.mac_ver()[0]}"
    # Windows
    elif sys.platform == "win32":
        os_version = f"{platform.system()} {platform.release()}"
    # Linux / other
    else:
        os_version = platform.platform()

    log.debug(f"OS:         {os_version}")
    log.debug(f"Python:     {platform.python_version()}")
    log.debug(f"Streamlink: {streamlink_version}")
    log.debug(f"Requests({requests.__version__}), "
              f"Socks({socks_version}), "
              f"Websocket({websocket_version})")


def log_current_arguments(session, parser):
    global args
    if not logger.root.isEnabledFor(logging.DEBUG):
        return

    sensitive = set()
    for pname, plugin in session.plugins.items():
        for parg in plugin.arguments:
            if parg.sensitive:
                sensitive.add(parg.argument_name(pname))

    log.debug("Arguments:")
    for action in parser._actions:
        if not hasattr(args, action.dest):
            continue
        value = getattr(args, action.dest)
        if action.default != value:
            name = next(  # pragma: no branch
                (option for option in action.option_strings if option.startswith("--")),
                action.option_strings[0]
            ) if action.option_strings else action.dest
            log.debug(f" {name}={value if name not in sensitive else '*' * 8}")


def check_version(force=False):
    cache = Cache(filename="cli.json")
    latest_version = cache.get("latest_version")

    if force or not latest_version:
        res = requests.get("https://pypi.python.org/pypi/streamlink/json")
        data = res.json()
        latest_version = data.get("info").get("version")
        cache.set("latest_version", latest_version, (60 * 60 * 24))

    version_info_printed = cache.get("version_info_printed")
    if not force and version_info_printed:
        return

    installed_version = StrictVersion(streamlink.version)
    latest_version = StrictVersion(latest_version)

    if latest_version > installed_version:
        log.info(f"A new version of Streamlink ({latest_version}) is available!")
        cache.set("version_info_printed", True, (60 * 60 * 6))
    elif force:
        log.info(f"Your Streamlink version ({installed_version}) is up to date!")

    if force:
        sys.exit()


def setup_logger_and_console(stream=sys.stdout, filename=None, level="info", json=False):
    global console

    if filename == "-":
        filename = LOG_DIR / f"{datetime.now()}.log"
    elif filename:
        filename = Path(filename).expanduser().resolve()

    if filename:
        filename.parent.mkdir(parents=True, exist_ok=True)

    streamhandler = logger.basicConfig(
        stream=stream,
        filename=filename,
        level=level,
        style="{",
        format=("[{asctime}]" if level == "trace" else "") + "[{name}][{levelname}] {message}",
        datefmt="%H:%M:%S" + (".%f" if level == "trace" else "")
    )

    console = ConsoleOutput(streamhandler.stream, json)


def main():
    error_code = 0
    parser = build_parser()

    setup_args(parser, ignore_unknown=True)
    # call argument set up as early as possible to load args from config files
    setup_config_args(parser, ignore_unknown=True)

    # Console output should be on stderr if we are outputting
    # a stream to stdout.
    if args.stdout or args.output == "-" or args.record_and_pipe:
        console_out = sys.stderr
    else:
        console_out = sys.stdout

    # We don't want log output when we are printing JSON or a command-line.
    silent_log = any(getattr(args, attr) for attr in QUIET_OPTIONS)
    log_level = args.loglevel if not silent_log else "none"
    log_file = args.logfile if log_level != "none" else None
    setup_logger_and_console(console_out, log_file, log_level, args.json)

    setup_signals()

    setup_streamlink()
    # load additional plugins
    setup_plugins(args.plugin_dirs)
    setup_plugin_args(streamlink, parser)
    # call setup args again once the plugin specific args have been added
    setup_args(parser)
    setup_config_args(parser)

    # update the logging level if changed by a plugin specific config
    log_level = args.loglevel if not silent_log else "none"
    logger.root.setLevel(log_level)

    setup_http_session()

    log_root_warning()
    log_current_versions()
    log_current_arguments(streamlink, parser)

    if args.version_check or args.auto_version_check:
        with ignored(Exception):
            check_version(force=args.version_check)

    if args.plugins:
        print_plugins()
    elif args.can_handle_url:
        try:
            streamlink.resolve_url(args.can_handle_url)
        except NoPluginError:
            error_code = 1
        except KeyboardInterrupt:
            error_code = 130
    elif args.can_handle_url_no_redirect:
        try:
            streamlink.resolve_url_no_redirect(args.can_handle_url_no_redirect)
        except NoPluginError:
            error_code = 1
        except KeyboardInterrupt:
            error_code = 130
    elif args.url:
        try:
            setup_options()
            handle_url()
        except KeyboardInterrupt:
            # Close output
            if output:
                output.close()
            console.msg("Interrupted! Exiting...")
            error_code = 130
        finally:
            if stream_fd:
                try:
                    log.info("Closing currently open stream...")
                    stream_fd.close()
                except KeyboardInterrupt:
                    error_code = 130
    elif args.help:
        parser.print_help()
    else:
        usage = parser.format_usage()
        console.msg(
            f"{usage}\n"
            f"Use -h/--help to see the available options or read the manual at https://streamlink.github.io"
        )

    sys.exit(error_code)


def parser_helper():
    session = Streamlink()
    parser = build_parser()
    setup_plugin_args(session, parser)
    return parser
