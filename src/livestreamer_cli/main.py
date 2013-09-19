import errno
import os
import sys
import signal

from time import sleep

from livestreamer import (Livestreamer, StreamError, PluginError,
                          NoPluginError)
from livestreamer.stream import StreamProcess

from .argparser import parser
from .compat import stdout, is_win32
from .console import ConsoleOutput
from .constants import CONFIG_FILE, PLUGINS_DIR, STREAM_SYNONYMS
from .output import FileOutput, PlayerOutput
from .utils import (NamedPipe, HTTPServer, ignored, find_default_player,
                    stream_to_url)

ACCEPTABLE_ERRNO = (errno.EPIPE, errno.EINVAL, errno.ECONNRESET)

args = console = livestreamer = plugin = None


def check_file_output(filename, force):
    """Checks if file already exists and ask the user if it should
    be overwritten if it does."""

    console.logger.debug("Checking file output")

    if os.path.isfile(filename) and not force:
        answer = console.ask("File {0} already exists! Overwrite it? [y/N] ",
                             filename)

        if answer.lower() != "y":
            sys.exit()

    return FileOutput(filename)


def create_output():
    """Decides where to write the stream.

    Depending on arguments it can be one of these:
     - The stdout pipe
     - A subprocess' stdin pipe
     - A named pipe that the subprocess reads from
     - A regular file

    """

    if args.output:
        if args.output == "-":
            out = FileOutput(fd=stdout)
        else:
            out = check_file_output(args.output, args.force)
    elif args.stdout:
        out = FileOutput(fd=stdout)
    else:
        http = namedpipe = None
        player = args.player or find_default_player()

        if not player:
            console.exit("The default player (VLC) does not seem to be "
                         "installed. You must specify the path to a player "
                         "executable with --player.")

        if args.player_fifo:
            pipename = "livestreamerpipe-{0}".format(os.getpid())
            console.logger.info("Creating pipe {0}", pipename)

            try:
                namedpipe = NamedPipe(pipename)
            except IOError as err:
                console.exit("Failed to create pipe: {0}", err)
        elif args.player_http:
            http = create_http_server()

        console.logger.info("Starting player: {0}", player)
        out = PlayerOutput(player, args=args.player_args,
                           quiet=not args.verbose_player,
                           namedpipe=namedpipe, http=http)

    return out


def create_http_server():
    """Creates a HTTP server listening on a random port."""

    try:
        http = HTTPServer()
        http.bind()
    except OSError as err:
        console.exit("Failed to create HTTP server: {0}", err)

    return http


def iter_http_requests(server, player):
    """Accept HTTP connections while the player is running."""

    while player.running:
        try:
            yield server.open(timeout=2.5)
        except OSError:
            continue


def output_stream_http(plugin, streams):
    """Continuously output the stream over HTTP."""

    server = create_http_server()
    player_cmd = args.player or find_default_player()
    player = PlayerOutput(player_cmd, args=args.player_args,
                          filename=server.url,
                          quiet=not args.verbose_player)

    try:
        console.logger.info("Starting player: {0}", player_cmd)
        player.open()
    except OSError as err:
        console.exit("Failed to start player: {0} ({1})",
                     player_cmd, err)

    for req in iter_http_requests(server, player):
        user_agent = req.headers.get("User-Agent") or "unknown player"
        console.logger.info("Got HTTP request from {0}".format(user_agent))

        stream = stream_fd = None
        while not stream_fd:
            if not player.running:
                break

            try:
                streams = streams or fetch_streams(plugin)
                stream = streams.get(args.stream)
            except PluginError as err:
                console.logger.error("Unable to fetch new streams: {0}",
                                     err)

            if not stream:
                console.logger.info("Stream not available, will re-fetch "
                                    "streams in 10 sec")
                streams = None
                sleep(10)
                continue

            try:
                stream_name = resolve_stream_name(streams, args.stream)
                console.logger.info("Opening stream: {0}", stream_name)
                stream_fd, prebuffer = open_stream(stream)
            except StreamError as err:
                console.logger.error("{0}", err)
                stream = streams = None
        else:
            console.logger.debug("Writing stream to player")
            with ignored(KeyboardInterrupt):
                read_stream(stream_fd, server, prebuffer)

        server.close(True)

    player.close()


def output_stream_passthrough(stream):
    """Prepares a filename to be passed to the player."""

    player = args.player or find_default_player()
    filename = '"{0}"'.format(stream_to_url(stream))
    out = PlayerOutput(player, args=args.player_args,
                       filename=filename, call=True,
                       quiet=not args.verbose_player)

    try:
        console.logger.info("Starting player: {0}", player)
        out.open()
    except OSError as err:
        console.exit("Failed to start player: {0} ({1})", player, err)
        return False
    except KeyboardInterrupt:
        pass

    return True


def open_stream(stream):
    """Opens a stream and reads 8192 bytes from it.

    This is useful to check if a stream actually has data
    before opening the output.

    """

    # Attempts to open the stream
    try:
        stream_fd = stream.open()
    except StreamError as err:
        raise StreamError("Could not open stream: {0}".format(err))

    # Read 8192 bytes before proceeding to check for errors.
    # This is to avoid opening the output unnecessarily.
    try:
        console.logger.debug("Pre-buffering 8192 bytes")
        prebuffer = stream_fd.read(8192)
    except IOError as err:
        raise StreamError("Failed to read data from stream: {0}".format(err))

    if not prebuffer:
        raise StreamError("No data returned from stream")

    return stream_fd, prebuffer


def output_stream(stream):
    """Open stream, create output and finally write the stream to output."""

    try:
        stream_fd, prebuffer = open_stream(stream)
    except StreamError as err:
        console.logger.error("{0}", err)
        return

    output = create_output()

    try:
        output.open()
    except (IOError, OSError) as err:
        if isinstance(output, PlayerOutput):
            console.exit("Failed to start player: {0} ({1})",
                         args.player, err)
        else:
            console.exit("Failed to open output: {0} ({1})",
                         args.output, err)

    console.logger.debug("Writing stream to output")

    with ignored(KeyboardInterrupt):
        read_stream(stream_fd, output, prebuffer)

    output.close()

    return True


def read_stream(stream, output, prebuffer):
    """Reads data from stream and then writes it to the output."""

    is_player = isinstance(output, PlayerOutput)
    is_http = isinstance(output, HTTPServer)
    is_fifo = is_player and output.namedpipe
    show_progress = isinstance(output, FileOutput) and output.fd is not stdout
    written = 0

    while True:
        try:
            data = prebuffer or stream.read(8192)
        except IOError as err:
            console.logger.error("Error when reading from stream: {0}",
                                 str(err))
            break

        if len(data) == 0:
            break

        # We need to check if the player process still exists when
        # using named pipes on Windows since the named pipe is not
        # automatically closed by the player.
        if is_win32 and is_fifo:
            output.player.poll()

            if output.player.returncode is not None:
                console.logger.info("Player closed")
                break

        try:
            output.write(data)
        except IOError as err:
            if is_player and err.errno in ACCEPTABLE_ERRNO:
                console.logger.info("Player closed")
            elif is_http and err.errno in ACCEPTABLE_ERRNO:
                console.logger.info("HTTP connection closed")
            else:
                console.logger.error("Error when writing to output: {0}",
                                     err)

            break

        written += len(data)
        prebuffer = None

        if show_progress:
            console.msg_inplace("Written {0} bytes", written)

    if show_progress and written > 0:
        console.msg_inplace_end()

    stream.close()
    console.logger.info("Stream ended")


def handle_stream(plugin, streams):
    """Decides what to do with the selected stream.

    Depending on arguments it can be one of these:
     - Output internal command-line
     - Output JSON represenation
     - Continuously output the stream over HTTP
     - Output stream data to selected output

    """

    stream_name = resolve_stream_name(streams, args.stream)
    stream = streams[stream_name]

    # Print internal command-line if this stream
    # uses a subprocess.
    if args.cmdline:
        if isinstance(stream, StreamProcess):
            try:
                cmdline = stream.cmdline()
            except StreamError as err:
                console.exit("{0}", err)

            console.msg("{0}", cmdline)
        else:
            console.exit("Stream does not use a command-line")

    # Print JSON representation of the stream
    elif console.json:
        console.msg_json(stream)

    # Continuously output the stream over HTTP
    elif args.player_continuous_http:
        output_stream_http(plugin, streams)

    # Output the stream
    else:
        # Find any streams with a '_alt' suffix and attempt
        # to use these in case the main stream is not usable.
        alt_streams = list(filter(lambda k: stream_name + "_alt" in k,
                                  sorted(streams.keys())))

        for stream_name in [stream_name] + alt_streams:
            console.logger.info("Opening stream: {0}", stream_name)
            stream = streams[stream_name]
            stream_type = type(stream).shortname()

            if (stream_type in args.player_passthrough and
                not (args.output or args.stdout)):
                success = output_stream_passthrough(stream)
            else:
                success = output_stream(stream)

            if success:
                break


def fetch_streams(plugin):
    """Fetches streams using correct parameters."""

    return plugin.get_streams(stream_types=args.stream_types,
                              sorting_excludes=args.stream_sorting_excludes)


def resolve_stream_name(streams, stream_name):
    """Returns the real stream name of a synonym."""

    if stream_name in STREAM_SYNONYMS:
        for name, stream in streams.items():
            if stream is streams[stream_name] and name not in STREAM_SYNONYMS:
                return name

    return stream_name


def format_valid_streams(streams):
    """Formats a dict of streams.

    Filters out synonyms and displays them next to
    the stream they point to.

    """

    delimiter = ", "
    validstreams = []

    for name, stream in sorted(streams.items()):
        if name in STREAM_SYNONYMS:
            continue

        synonymfilter = lambda n: stream is streams[n] and n is not name
        synonyms = list(filter(synonymfilter, streams.keys()))

        if len(synonyms) > 0:
            joined = delimiter.join(synonyms)
            name = "{0} ({1})".format(name, joined)

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
        plugin = livestreamer.resolve_url(args.url)
        console.logger.info("Found matching plugin {0} for URL {1}",
                            plugin.module, args.url)
        streams = fetch_streams(plugin)
    except NoPluginError:
        console.exit("No plugin can handle URL: {0}", args.url)
    except PluginError as err:
        console.exit("{0}", err)

    if not streams:
        console.exit("No streams found on this URL: {0}", args.url)

    if args.stream:
        if args.stream in streams:
            handle_stream(plugin, streams)
        else:
            err = "The specified stream '{0}' could not be found".format(args.stream)

            if console.json:
                console.msg_json(dict(streams=streams, plugin=plugin.module,
                                      error=err))
            else:
                validstreams = format_valid_streams(streams)
                console.exit("{0}.\n       Available streams: {1}",
                             err, validstreams)
    else:
        if console.json:
            console.msg_json(dict(streams=streams, plugin=plugin.module))
        else:
            validstreams = format_valid_streams(streams)
            console.msg("Available streams: {0}", validstreams)


def print_plugins():
    """Outputs a list of all plugins Livestreamer has loaded."""

    pluginlist = list(livestreamer.get_plugins().keys())
    pluginlist_formatted = ", ".join(sorted(pluginlist))

    if console.json:
        console.msg_json(pluginlist)
    else:
        console.msg("Loaded plugins: {0}", pluginlist_formatted)


def load_plugins(dirs):
    """Attempts to load plugins from a list of directories."""

    dirs = [os.path.expanduser(d) for d in dirs]

    for directory in dirs:
        if os.path.isdir(directory):
            livestreamer.load_plugins(directory)
        else:
            console.logger.warning("Plugin path {0} does not exist or is not "
                                   "a directory!", directory)


def setup_args():
    """Parses arguments."""
    global args

    arglist = sys.argv[1:]

    # Load additional arguments from livestreamerrc
    if os.path.exists(CONFIG_FILE):
        arglist.insert(0, "@" + CONFIG_FILE)

    args = parser.parse_args(arglist)


def setup_console():
    """Console setup."""
    global console

    # All console related operations is handled via the ConsoleOutput class
    console = ConsoleOutput(sys.stdout, livestreamer)

    # Console output should be on stderr if we are outputting
    # a stream to stdout.
    if args.stdout or args.output == "-":
        console.set_output(sys.stderr)

    # We don't want log output when we are printing JSON or a command-line.
    if not (args.json or args.cmdline or args.quiet):
        console.set_level(args.loglevel)

    if args.quiet_player:
        console.logger.warning("The option --quiet-player is deprecated since "
                               "version 1.4.3 as hiding player output is now "
                               "the default.")

    console.json = args.json

    # Handle SIGTERM just like SIGINT
    signal.signal(signal.SIGTERM, signal.default_int_handler)


def setup_plugins():
    """Loads any additional plugins."""
    if os.path.isdir(PLUGINS_DIR):
        load_plugins([PLUGINS_DIR])

    if args.plugin_dirs:
        load_plugins(args.plugin_dirs)


def setup_livestreamer():
    """Creates the Livestreamer session."""
    global livestreamer

    livestreamer = Livestreamer()


def setup_options():
    """Sets Livestreamer options."""

    if args.gomtv_username and not args.gomtv_password:
        gomtv_password = console.askpass("Enter GOMTV password: ")
    else:
        gomtv_password = args.gomtv_password

    livestreamer.set_option("errorlog", args.errorlog)

    if args.rtmpdump:
        livestreamer.set_option("rtmpdump", args.rtmpdump)

    if args.rtmpdump_proxy:
        livestreamer.set_option("rtmpdump-proxy", args.rtmpdump_proxy)

    if args.hds_live_edge is not None:
        livestreamer.set_option("hds-live-edge", args.hds_live_edge)

    if args.hds_fragment_buffer is not None:
        livestreamer.set_option("hds-fragment-buffer",
                                args.hds_fragment_buffer)

    if args.ringbuffer_size:
        livestreamer.set_option("ringbuffer-size", args.ringbuffer_size)

    if args.jtv_cookie:
        livestreamer.set_plugin_option("justintv", "cookie",
                                       args.jtv_cookie)

    if args.gomtv_cookie:
        livestreamer.set_plugin_option("gomtv", "cookie",
                                       args.gomtv_cookie)

    if args.gomtv_username:
        livestreamer.set_plugin_option("gomtv", "username",
                                       args.gomtv_username)

    if gomtv_password:
        livestreamer.set_plugin_option("gomtv", "password",
                                       gomtv_password)


def check_root():
    if hasattr(os, "getuid"):
        if os.geteuid() == 0 and not args.yes_run_as_root:
            print("livestreamer is not supposed to be run as root. "
                  "If you really must you can do it by passing "
                  "--yes-run-as-root.")
            sys.exit(1)


def main():
    setup_args()
    check_root()
    setup_livestreamer()
    setup_console()
    setup_plugins()

    if args.url:
        setup_options()
        handle_url()
    elif args.plugins:
        print_plugins()
    else:
        parser.print_help()
