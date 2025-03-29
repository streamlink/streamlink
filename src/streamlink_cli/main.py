from __future__ import annotations

import argparse
import importlib.metadata
import logging
import os
import platform
import re
import signal
import ssl
import sys
import warnings
from collections.abc import Mapping
from contextlib import closing, suppress
from gettext import gettext
from pathlib import Path
from time import sleep
from typing import Any, TextIO

import streamlink.logger as logger
from streamlink import NoPluginError, PluginError, StreamError, Streamlink, __version__ as streamlink_version
from streamlink.exceptions import FatalPluginError, StreamlinkDeprecationWarning
from streamlink.plugin import Plugin
from streamlink.stream.stream import Stream, StreamIO
from streamlink.utils.named_pipe import NamedPipe
from streamlink.utils.times import LOCAL as LOCALTIMEZONE
from streamlink_cli.argparser import (
    ArgumentParser,
    build_parser,
    setup_plugin_args,
    setup_plugin_options,
    setup_session_options,
)
from streamlink_cli.compat import stdout
from streamlink_cli.console import ConsoleOutput, ConsoleUserInputRequester
from streamlink_cli.constants import CONFIG_FILES, DEFAULT_STREAM_METADATA, LOG_DIR, PLUGIN_DIRS, STREAM_SYNONYMS
from streamlink_cli.exceptions import StreamlinkCLIError
from streamlink_cli.output import FileOutput, HTTPOutput, PlayerOutput
from streamlink_cli.show_matchers import show_matchers
from streamlink_cli.streamrunner import StreamRunner
from streamlink_cli.utils import Formatter, datetime
from streamlink_cli.utils.versioncheck import check_version


QUIET_OPTIONS = ("json", "stream_url", "quiet")


args: Any = None  # type: ignore[assignment]
console: ConsoleOutput = None  # type: ignore[assignment]
output: FileOutput | PlayerOutput = None  # type: ignore[assignment]
stream_fd: StreamIO = None  # type: ignore[assignment]
streamlink: Streamlink = None  # type: ignore[assignment]


log = logging.getLogger("streamlink.cli")


def get_formatter(plugin: Plugin):
    return Formatter(
        {
            "url": lambda: args.url,
            "plugin": lambda: plugin.module,
            "id": plugin.get_id,
            "author": plugin.get_author,
            "category": plugin.get_category,
            "game": plugin.get_category,
            "title": plugin.get_title,
            "time": lambda: datetime.now(tz=LOCALTIMEZONE),
        },
        {
            "time": lambda dt, fmt: dt.strftime(fmt),
        },
    )


def check_file_output(path: Path, force: bool) -> Path:
    """
    Checks if path already exists and asks the user if it should be overwritten if it does.
    """

    # rewrap path and resolve using `os.path.realpath` instead of `path.resolve()`
    # to avoid a pathlib issues on py39 and below
    realpath = Path(os.path.realpath(path))

    log.info(f"Writing output to\n{realpath}")
    log.debug("Checking file output")

    if realpath.is_file() and not force:
        try:
            answer = console.ask(f"File {path} already exists! Overwrite it? [y/N] ")
        except OSError:
            log.error(f"File {path} already exists, use --force to overwrite it.")
            raise StreamlinkCLIError() from None
        if not answer or answer.lower() != "y":
            raise StreamlinkCLIError()

    return realpath


def create_output(formatter: Formatter) -> FileOutput | PlayerOutput:
    """Decides where to write the stream.

    Depending on arguments it can be one of these:
     - The stdout pipe
     - A subprocess' stdin pipe
     - A named pipe that the subprocess reads from
     - A regular file

    """

    if args.output:
        if args.stdout:
            raise StreamlinkCLIError("The -o/--output argument is incompatible with -O/--stdout")
        if args.record or args.record_and_pipe:
            raise StreamlinkCLIError("The -o/--output argument is incompatible with -r/--record and -R/--record-and-pipe")

        if args.output == "-":
            return FileOutput(fd=stdout)
        else:
            filename = check_file_output(formatter.path(args.output, args.fs_safe_rules), args.force)
            return FileOutput(filename=filename)

    elif args.stdout:
        if args.record_and_pipe:
            raise StreamlinkCLIError("The -O/--stdout argument is incompatible with -R/--record-and-pipe")

        if not args.record or args.record == "-":
            return FileOutput(fd=stdout)
        else:
            filename = check_file_output(formatter.path(args.record, args.fs_safe_rules), args.force)
            return FileOutput(fd=stdout, record=FileOutput(filename=filename))

    elif args.record_and_pipe:
        warnings.warn(
            "-R/--record-and-pipe=... has been deprecated in favor of --stdout --record=...",
            StreamlinkDeprecationWarning,
            stacklevel=1,
        )
        filename = check_file_output(formatter.path(args.record_and_pipe, args.fs_safe_rules), args.force)
        return FileOutput(fd=stdout, record=FileOutput(filename=filename))

    elif args.player:
        http = namedpipe = record = None

        if args.player_fifo:
            try:
                namedpipe = NamedPipe()  # type: ignore[abstract]  # ???
            except OSError as err:
                raise StreamlinkCLIError(f"Failed to create pipe: {err}") from err
        elif args.player_http:
            http = create_http_server()

        if args.record:
            if args.record == "-":
                record = FileOutput(fd=stdout)
            else:
                filename = check_file_output(formatter.path(args.record, args.fs_safe_rules), args.force)
                record = FileOutput(filename=filename)

        log.info(f"Starting player: {args.player}")

        return PlayerOutput(
            path=args.player,
            args=args.player_args,
            env=args.player_env,
            quiet=not args.player_verbose,
            kill=not args.player_no_close,
            namedpipe=namedpipe,
            http=http,
            record=record,
            title=formatter.title(args.title, defaults=DEFAULT_STREAM_METADATA) if args.title else args.url,
        )

    raise StreamlinkCLIError(
        "The default player (VLC) does not seem to be installed."
        + " You must specify the path to a player executable with --player,"
        + " a file path to save the stream with --output,"
        + " or pipe the stream to another program with --stdout.",
    )


def create_http_server(host: str | None = None, port: int = 0) -> HTTPOutput:
    """
    Create an HTTP server listening on a given host and port.
    If host is None, listen on all available interfaces.
    If port is 0, listen on a random high port.
    """

    try:
        httpoutput = HTTPOutput(host, port)
        httpoutput.start_server()
        return httpoutput
    except OSError as err:
        raise StreamlinkCLIError(f"Failed to create HTTP server: {err}") from err


def output_stream_http(
    plugin: Plugin,
    initial_streams: Mapping[str, Stream],
    formatter: Formatter,
    external: bool = False,
    continuous: bool = True,
    port: int = 0,
):
    """Continuously output the stream over HTTP."""
    global output

    if not external:
        if not args.player:
            raise StreamlinkCLIError(
                "The default player (VLC) does not seem to be installed."
                + " You must specify the path to a player executable with --player.",
            )

        server = create_http_server()
        player = output = PlayerOutput(
            path=args.player,
            args=args.player_args,
            env=args.player_env,
            quiet=not args.player_verbose,
            filename=server.url,
            title=formatter.title(args.title, defaults=DEFAULT_STREAM_METADATA) if args.title else args.url,
        )

        try:
            log.info(f"Starting player: {args.player}")
            if player:
                player.open()
        except OSError as err:
            raise StreamlinkCLIError(f"Failed to start player: {args.player} ({err})") from err
    else:
        server = create_http_server(args.player_external_http_interface, port)
        player = None

        log.info("Starting server, access with one of:")
        for url in server.urls:
            log.info(f" {url}")

    initial_streams_used = False
    while not player or player.running:
        try:
            server.accept_connection(timeout=2.5)
            server.open()
        except OSError:
            continue

        user_agent = server.request.headers.get("User-Agent") or "unknown player"
        log.info(f"Got HTTP request from {user_agent}")

        stream_fd = prebuffer = None
        while not stream_fd and (not player or player.running):
            try:
                if not initial_streams_used:
                    streams = initial_streams
                    initial_streams_used = True
                else:
                    streams = fetch_streams(plugin)

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
            stream_runner = StreamRunner(stream_fd, server)
            try:
                stream_runner.run(prebuffer)
            except OSError as err:
                raise StreamlinkCLIError() from err

        if not continuous:
            break

        server.close()

    if player:
        player.close()
    server.shutdown()


def output_stream_passthrough(stream, formatter: Formatter):
    """Prepares a filename to be passed to the player."""
    global output

    try:
        url = stream.to_url()
    except TypeError:
        raise StreamlinkCLIError("The stream specified cannot be translated to a URL") from None

    if not args.player:
        raise StreamlinkCLIError(
            "The default player (VLC) does not seem to be installed."
            + " You must specify the path to a player executable with --player.",
        )

    output = PlayerOutput(
        path=args.player,
        args=args.player_args,
        env=args.player_env,
        quiet=not args.player_verbose,
        call=True,
        filename=url,
        title=formatter.title(args.title, defaults=DEFAULT_STREAM_METADATA) if args.title else args.url,
    )

    try:
        log.info(f"Starting player: {args.player}")
        output.open()
    except OSError as err:
        raise StreamlinkCLIError(f"Failed to start player: {args.player} ({err})") from err

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
        raise StreamError(f"Could not open stream: {err}") from err

    # Read 8192 bytes before proceeding to check for errors.
    # This is to avoid opening the output unnecessarily.
    try:
        log.debug("Pre-buffering 8192 bytes")
        prebuffer = stream_fd.read(8192)
    except OSError as err:
        stream_fd.close()
        raise StreamError(f"Failed to read data from stream: {err}") from err

    if not prebuffer:
        stream_fd.close()
        raise StreamError("No data returned from stream")

    return stream_fd, prebuffer


def output_stream(stream, formatter: Formatter):
    """Open stream, create output and finally write the stream to output."""
    global output

    # create output before opening the stream, so file outputs can prompt on existing output
    output = create_output(formatter)

    success_open = False
    for i in range(args.retry_open):
        try:
            stream_fd, prebuffer = open_stream(stream)
            success_open = True
            break
        except StreamError as err:
            log.error(f"Try {i + 1}/{args.retry_open}: Could not open stream {stream} ({err})")

    if not success_open:
        raise StreamlinkCLIError(f"Could not open stream {stream}, tried {args.retry_open} times, exiting")

    try:
        output.open()
    except OSError as err:
        if isinstance(output, PlayerOutput):
            raise StreamlinkCLIError(f"Failed to start player: {args.player} ({err})") from err
        elif output.filename:
            raise StreamlinkCLIError(f"Failed to open output: {output.filename} ({err})") from err
        else:
            raise StreamlinkCLIError(f"Failed to open output ({err})") from err

    try:
        with closing(output):
            log.debug("Writing stream to output")
            show_progress = (
                args.progress == "force"
                or args.progress == "yes" and (sys.stderr.isatty() if sys.stderr else False)
            )  # fmt: skip
            # TODO: finally clean up the global variable mess and refactor the streamlink_cli package
            # noinspection PyUnboundLocalVariable
            stream_runner = StreamRunner(stream_fd, output, show_progress=show_progress)
            # noinspection PyUnboundLocalVariable
            stream_runner.run(prebuffer)
    except OSError as err:
        raise StreamlinkCLIError() from err

    return True


def handle_stream(plugin: Plugin, streams: Mapping[str, Stream], stream_name: str) -> None:
    """Decides what to do with the selected stream.

    Depending on arguments it can be one of these:
     - Output JSON represenation
     - Output the stream URL
     - Continuously output the stream over HTTP
     - Output stream data to selected output

    """

    stream_name = resolve_stream_name(streams, stream_name)
    stream = streams[stream_name]

    # Print JSON representation of the stream
    if args.json:
        console.msg_json(
            stream,
            metadata=plugin.get_metadata(),
        )

    elif args.stream_url:
        try:
            console.msg(stream.to_url())
        except TypeError:
            raise StreamlinkCLIError("The stream specified cannot be translated to a URL") from None

    else:
        # Find any streams with a '_alt' suffix and attempt
        # to use these in case the main stream is not usable.
        alt_streams = list(filter(lambda k: f"{stream_name}_alt" in k, sorted(streams.keys())))

        file_output = args.output or args.stdout

        formatter = get_formatter(plugin)

        for name in [stream_name, *alt_streams]:
            stream = streams[name]
            stream_type = type(stream).shortname()

            if stream_type in args.player_passthrough and not file_output:
                log.info(f"Opening stream: {name} ({stream_type})")
                success = output_stream_passthrough(stream, formatter)
            elif args.player_external_http:
                return output_stream_http(
                    plugin,
                    streams,
                    formatter,
                    external=True,
                    continuous=args.player_external_http_continuous,
                    port=args.player_external_http_port,
                )
            elif args.player_continuous_http and not file_output:
                return output_stream_http(plugin, streams, formatter)
            else:
                log.info(f"Opening stream: {name} ({stream_type})")
                success = output_stream(stream, formatter)

            if success:
                break


def fetch_streams(plugin: Plugin) -> Mapping[str, Stream]:
    """Fetches streams using correct parameters."""

    return plugin.streams(
        stream_types=args.stream_types,
        sorting_excludes=args.stream_sorting_excludes,
    )


def fetch_streams_with_retry(plugin: Plugin, interval: float, count: int) -> Mapping[str, Stream] | None:
    """Attempts to fetch streams repeatedly until some are returned or limit hit."""

    try:
        streams = fetch_streams(plugin)
    except FatalPluginError:
        raise
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


def resolve_stream_name(streams: Mapping[str, Stream], stream_name: str) -> str:
    """Returns the real stream name of a synonym."""

    if stream_name in STREAM_SYNONYMS and stream_name in streams:
        for name, stream in streams.items():
            if stream is streams[stream_name] and name not in STREAM_SYNONYMS:
                return name

    return stream_name


def format_valid_streams(plugin: Plugin, streams: Mapping[str, Stream]) -> str:
    """Formats a dict of streams.

    Filters out synonyms and displays them next to
    the stream they point to.

    Streams are sorted according to their quality
    (based on plugin.stream_weight).

    """

    delimiter = ", "
    validstreams = []

    for name, stream in sorted(streams.items(), key=lambda s: plugin.stream_weight(s[0])):
        if name in STREAM_SYNONYMS:
            continue

        synonyms = [key for key, value in streams.items() if stream is value and key != name]

        if synonyms:
            joined = delimiter.join(synonyms)
            name = f"{name} ({joined})"

        validstreams.append(name)

    return delimiter.join(validstreams)


def handle_url_wrapper() -> int:
    exit_code = 0
    try:
        handle_url()
    except KeyboardInterrupt:
        # Close output
        if output:
            try:
                output.close()
            except KeyboardInterrupt:
                pass
        console.msg("Interrupted! Exiting...")
        exit_code = 128 + signal.SIGINT
    finally:
        if stream_fd:
            try:
                log.info("Closing currently open stream...")
                stream_fd.close()
            except KeyboardInterrupt:
                exit_code = 128 + signal.SIGINT

    return exit_code


def handle_url():
    """The URL handler.

    Attempts to resolve the URL to a plugin and then attempts
    to fetch a list of available streams.

    Proceeds to handle stream if user specified a valid one,
    otherwise output list of valid streams.

    """

    try:
        pluginname, pluginclass, resolved_url = streamlink.resolve_url(args.url)
        log.info(f"Found matching plugin {pluginname} for URL {args.url}")

        options = setup_plugin_options(streamlink, args, pluginname, pluginclass)
        plugin = pluginclass(streamlink, resolved_url, options)

        if args.retry_max or args.retry_streams:
            retry_streams = 1
            retry_max = 0
            if args.retry_streams:
                retry_streams = args.retry_streams
            if args.retry_max:
                retry_max = args.retry_max
            streams = fetch_streams_with_retry(plugin, retry_streams, retry_max)
        else:
            streams = fetch_streams(plugin)
    except NoPluginError:
        raise StreamlinkCLIError(f"No plugin can handle URL: {args.url}") from None
    except PluginError as err:
        raise StreamlinkCLIError() from err

    if not streams:
        raise StreamlinkCLIError(f"No playable streams found on this URL: {args.url}")

    if args.default_stream and not args.stream and not args.json:
        args.stream = args.default_stream

    if args.stream:
        validstreams = format_valid_streams(plugin, streams)
        for stream_name in args.stream:
            if stream_name in streams:
                log.info(f"Available streams: {validstreams}")
                handle_stream(plugin, streams, stream_name)
                return

        errmsg = f"The specified stream(s) '{', '.join(args.stream)}' could not be found"
        if not args.json:
            raise StreamlinkCLIError(f"{errmsg}.\n       Available streams: {validstreams}")
        console.msg_json(
            plugin=plugin.module,
            metadata=plugin.get_metadata(),
            streams=streams,
            error=errmsg,
        )
        raise StreamlinkCLIError()
    elif args.json:
        console.msg_json(
            plugin=plugin.module,
            metadata=plugin.get_metadata(),
            streams=streams,
        )
    elif args.stream_url:
        try:
            console.msg(streams[list(streams)[-1]].to_manifest_url())
        except TypeError:
            raise StreamlinkCLIError("The stream specified cannot be translated to a URL") from None
    else:
        validstreams = format_valid_streams(plugin, streams)
        console.msg(f"Available streams: {validstreams}")


def check_version_wrapper() -> int:
    force = args.version_check

    try:
        latest = check_version(force=force)
        if not force:
            return 0
        if latest:
            return 0
        return 1
    except KeyboardInterrupt:
        return 128 + signal.SIGINT


def print_plugins():
    """Outputs a list of all plugins Streamlink has loaded."""

    pluginlist = streamlink.plugins.get_names()

    if args.json:
        console.msg_json(pluginlist)
    else:
        console.msg(f"Available plugins: {', '.join(pluginlist)}")


def can_handle_url() -> int:
    url = args.can_handle_url or args.can_handle_url_no_redirect or ""
    follow_redirect = bool(args.can_handle_url)

    try:
        streamlink.resolve_url(url, follow_redirect=follow_redirect)
        return 0
    except NoPluginError:
        return 1
    except KeyboardInterrupt:
        return 128 + signal.SIGINT


def load_plugins(dirs: list[Path], showwarning: bool = True):
    """Attempts to load plugins from a list of directories."""
    for directory in dirs:
        if directory.is_dir():
            streamlink.plugins.load_path(directory)
        elif showwarning:
            log.warning(f"Plugin path {directory} does not exist or is not a directory!")


def setup_args(
    parser: argparse.ArgumentParser,
    config_files: list[Path] | None = None,
    ignore_unknown: bool = False,
):
    """Parses arguments."""
    global args
    arglist = sys.argv[1:]

    # Load arguments from config files
    prefix = parser.fromfile_prefix_chars or "@"
    configs = [f"{prefix}{config_file}" for config_file in config_files or []]

    args, unknown = parser.parse_known_args(configs + arglist)
    if unknown and not ignore_unknown:
        msg = gettext("unrecognized arguments: %s")
        parser.error(msg % " ".join(unknown))

    # Force lowercase to allow case-insensitive lookup
    if args.stream:
        args.stream = [stream.lower() for stream in args.stream]

    if not args.url and args.url_param:
        args.url = args.url_param

    args.silent_log = any(getattr(args, attr) for attr in QUIET_OPTIONS)


def setup_config_args(parser, ignore_unknown=False):
    if args.no_config:
        return

    config_files = []

    if args.config:
        # We want the config specified last to get the highest priority
        config_files.extend(
            config_file
            for config_file in [Path(path).expanduser() for path in reversed(args.config)]
            if config_file.is_file()
        )  # fmt: skip

    else:
        # Only load first available default config
        for config_file in filter(lambda path: path.is_file(), CONFIG_FILES):  # pragma: no branch
            config_files.append(config_file)
            break

    if streamlink and args.url:
        # Only load first available plugin config
        with suppress(NoPluginError):
            pluginname, _pluginclass, _resolved_url = streamlink.resolve_url(args.url)
            for config_file in CONFIG_FILES:  # pragma: no branch
                config_file = config_file.with_name(f"{config_file.name}.{pluginname}")
                if not config_file.is_file():
                    continue
                config_files.append(config_file)
                break

    if config_files:
        setup_args(parser, config_files, ignore_unknown=ignore_unknown)


def setup_signals():
    # restore default behavior of raising a KeyboardInterrupt on SIGINT (and SIGTERM)
    # so cleanup code can be run when the user stops execution
    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, signal.default_int_handler)


def setup_plugins(extra_plugin_dir=None):
    """Loads any additional plugins."""
    load_plugins(PLUGIN_DIRS, showwarning=False)

    if extra_plugin_dir:
        load_plugins([Path(path).expanduser() for path in extra_plugin_dir])


def setup_streamlink():
    """Creates the Streamlink session."""
    global streamlink

    streamlink = Streamlink({"user-input-requester": ConsoleUserInputRequester(console)})


def log_root_warning():
    if hasattr(os, "geteuid"):  # pragma: no branch
        if os.geteuid() == 0:
            log.info("streamlink is running as root! Be careful!")


def log_current_versions() -> None:
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
    log.debug(f"OpenSSL:    {ssl.OPENSSL_VERSION}")
    log.debug(f"Streamlink: {streamlink_version}")

    log.debug("Dependencies:")
    # https://peps.python.org/pep-0508/#names
    re_name = re.compile(r"[A-Z\d](?:[A-Z\d._-]*[A-Z\d])?", re.IGNORECASE)
    dependencies: list[str] = importlib.metadata.requires("streamlink") or []
    dependency_names: set[str] = {
        match[0]
        for match in [re_name.match(item) for item in dependencies]
        if match is not None
    }  # fmt: skip
    # noinspection PyTypeChecker
    for name in sorted(dependency_names, key=str.lower):
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
        log.debug(f" {name}: {version}")


def log_current_arguments(session: Streamlink, parser: argparse.ArgumentParser):
    if not logger.root.isEnabledFor(logging.DEBUG):
        return

    sensitive = set()
    for pname, arguments in session.plugins.iter_arguments():
        for parg in arguments:
            if parg.sensitive:
                sensitive.add(parg.argument_name(pname))

    log.debug("Arguments:")
    seen = set()
    for action in parser._actions:
        if not hasattr(args, action.dest) or action.dest in seen:
            continue
        seen.add(action.dest)
        value = getattr(args, action.dest)
        if action.default != value:
            name = (
                next(  # pragma: no branch
                    (option for option in action.option_strings if option.startswith("--")),
                    action.option_strings[0],
                )
                if action.option_strings
                else action.dest
            )  # fmt: skip
            log.debug(f" {name}={value if name not in sensitive else '*' * 8}")


def setup_console() -> None:
    global console

    console_output: TextIO | None
    if args.quiet:
        console_output = None
    elif args.stdout or args.output == "-" or args.record == "-" or args.record_and_pipe:
        # Console output should be on stderr if we are outputting a stream to stdout
        console_output = sys.stderr
    else:
        console_output = sys.stdout or sys.stderr

    console = ConsoleOutput(console_output=console_output, json=args.json)


def setup_logger() -> None:
    level: str = args.loglevel if not args.silent_log else logging.getLevelName(logger.NONE)
    file: str | None = args.logfile if level != logging.getLevelName(logger.NONE) else None
    fmt: str | None = args.logformat
    datefmt: str | None = args.logdateformat

    verbose = level in (logging.getLevelName(logger.TRACE), logging.getLevelName(logger.ALL))
    if not fmt:
        if verbose:
            fmt = "[{asctime}][{name}][{levelname}] {message}"
        else:
            fmt = "[{name}][{levelname}] {message}"
    if not datefmt:
        if verbose:
            datefmt = "%H:%M:%S.%f"
        else:
            datefmt = "%H:%M:%S"

    if file == "-":
        filename = LOG_DIR / f"{datetime.now(tz=LOCALTIMEZONE)}.log"
    elif file:
        filename = Path(file).expanduser().resolve()
    else:
        filename = None

    if filename:
        filename.parent.mkdir(parents=True, exist_ok=True)

    try:
        streamhandler = logger.basicConfig(
            filename=filename,
            format=fmt,
            datefmt=datefmt,
            style="{",
            level=level,
            stream=console.console_output,
            capture_warnings=True,
        )
    except Exception as err:
        raise StreamlinkCLIError(f"Logging setup error: {err}") from err

    if isinstance(streamhandler, logging.FileHandler):
        console.file_output = streamhandler.stream


def setup(parser: ArgumentParser) -> None:
    setup_args(parser, ignore_unknown=True)
    # call argument set up as early as possible to load args from config files
    setup_config_args(parser, ignore_unknown=True)

    setup_console()
    setup_logger()

    setup_streamlink()
    # load additional plugins
    setup_plugins(args.plugin_dirs)
    setup_plugin_args(streamlink, parser)
    # call setup args again once the plugin specific args have been added
    setup_args(parser)
    setup_config_args(parser)

    # update the logging level if changed by a plugin specific config
    logger.root.setLevel(args.loglevel if not args.silent_log else logger.NONE)

    log_root_warning()
    log_current_versions()
    log_current_arguments(streamlink, parser)

    setup_session_options(streamlink, args)

    setup_signals()


def run(parser: ArgumentParser) -> int:
    exit_code = 0

    if args.version_check or args.auto_version_check:
        exit_code = check_version_wrapper()

    if args.version_check:
        pass
    elif args.help:
        helptext = parser.format_help()
        console.msg(helptext)
    elif args.plugins:
        print_plugins()
    elif args.show_matchers:
        show_matchers(streamlink, console, args.show_matchers)
    elif args.can_handle_url or args.can_handle_url_no_redirect:
        exit_code = can_handle_url()
    elif args.url:
        exit_code = handle_url_wrapper()
    else:
        usage = parser.format_usage()
        console.msg(f"{usage}\nUse -h/--help to see the available options or read the manual at https://streamlink.github.io/")

    return exit_code


def main():
    try:
        parser = build_parser()
        setup(parser)
    except StreamlinkCLIError as err:
        sys.stderr.write(f"{err}\n")
        sys.exit(1)

    try:
        exit_code = run(parser)
    except StreamlinkCLIError as err:
        exit_code = err.code
        if msg := str(err):  # pragma: no branch
            if console.json:
                console.msg_json({"error": msg})
            else:
                console.msg(f"error: {msg}")

    # https://docs.python.org/3/library/signal.html#note-on-sigpipe
    try:
        sys.stdout.flush()
    except (AttributeError, OSError):
        del sys.stdout

    sys.exit(exit_code)
