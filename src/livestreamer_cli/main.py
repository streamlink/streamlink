import errno
import os
import sys
import signal

from livestreamer import (Livestreamer, StreamError, PluginError,
                          NoPluginError)
from livestreamer.stream import StreamProcess

from .argparser import parser
from .compat import stdout, is_win32
from .console import ConsoleOutput
from .constants import CONFIG_FILE, PLUGINS_DIR, STREAM_SYNONYMS
from .output import FileOutput, PlayerOutput
from .utils import NamedPipe, ignored, find_default_player

args = console = livestreamer = None


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
        namedpipe = None
        player = args.player or find_default_player()

        if not player:
            console.exit("The default player (VLC) does not seem to be "
                         "installed. You must specify the path to a player "
                         "executable with --player.")

        if args.fifo:
            pipename = "livestreamerpipe-{0}".format(os.getpid())
            console.logger.info("Creating pipe {0}", pipename)

            try:
                namedpipe = NamedPipe(pipename)
            except IOError as err:
                console.exit("Failed to create pipe: {0}", err)

        console.logger.info("Starting player: {0}", player)

        out = PlayerOutput(player, namedpipe=namedpipe,
                           quiet=not args.verbose_player)

    return out


def output_stream(stream):
    """Open stream, create output and finally write the stream to output."""

    # Attempts to open the stream
    try:
        streamfd = stream.open()
    except StreamError as err:
        console.logger.error("Could not open stream: {0}", err)
        return

    # Read 8192 bytes before proceeding to check for errors.
    # This is to avoid opening the output unnecessarily.
    try:
        console.logger.debug("Pre-buffering 8192 bytes")
        prebuffer = streamfd.read(8192)
    except IOError as err:
        console.logger.error("Failed to read data from stream: {0}", str(err))
        return

    if len(prebuffer) == 0:
        console.logger.error("Failed to read data from stream")
        return

    output = create_output()

    try:
        output.open()
    except IOError as err:
        console.exit("Failed to open output: {0}", err)

    console.logger.debug("Writing stream to output")

    try:
        output.write(prebuffer)
    except IOError as err:
        console.exit("Error when writing to output: {0}", err)

    with ignored(KeyboardInterrupt):
        read_stream(streamfd, output)

    output.close()

    return True


def read_stream(stream, output):
    """Reads data from stream and then writes it to the output."""

    is_player = isinstance(output, PlayerOutput)
    is_fifo = is_player and output.namedpipe
    show_progress = isinstance(output, FileOutput) and output.fd is not stdout
    written = 0

    while True:
        try:
            data = stream.read(8192)
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
            if is_player and err.errno in (errno.EPIPE, errno.EINVAL):
                console.logger.info("Player closed")
            else:
                console.logger.error("Error when writing to output: {0}",
                                     str(err))

            break

        written += len(data)

        if show_progress:
            console.msg_inplace("Written {0} bytes", written)

    if show_progress and written > 0:
        console.msg_inplace_end()

    stream.close()
    console.logger.info("Stream ended")


def handle_stream(streams):
    """Decides what to do with the selected stream.

    Depending on arguments it can be one of these:
     - Output internal command-line
     - Output JSON represenation
     - Output stream data to selected output

    """

    streamname = args.stream
    stream = streams[streamname]

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

    # Output the stream
    else:
        # Find any streams with a '_alt' suffix and attempt
        # to use these in case the main stream is not usable.
        altstreams = list(filter(lambda k: args.stream + "_alt" in k,
                          sorted(streams.keys())))

        for streamname in [args.stream] + altstreams:
            console.logger.info("Opening stream: {0}", streamname)

            success = output_stream(streams[streamname])

            if success:
                break


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
    except NoPluginError:
        console.exit("No plugin can handle URL: {0}", args.url)

    console.logger.info("Found matching plugin {0} for URL {1}",
                        plugin.module, args.url)

    try:
        streams = plugin.get_streams(stream_types=args.stream_types,
                                     sorting_excludes=args.stream_sorting_excludes)
    except (StreamError, PluginError) as err:
        console.exit("{0}", err)

    if len(streams) == 0:
        console.exit("No streams found on this URL: {0}", args.url)

    if args.stream:
        if args.stream in streams:
            if args.stream in STREAM_SYNONYMS:
                for name, stream in streams.items():
                    if stream is streams[args.stream] and name not in STREAM_SYNONYMS:
                        args.stream = name

            handle_stream(streams)
        else:
            err = "Invalid stream specified: {0}".format(args.stream)

            if console.json:
                console.msg_json(dict(streams=streams, plugin=plugin.module,
                                      error=err))
            else:
                validstreams = format_valid_streams(streams)

                console.msg("Valid streams: {0}", validstreams)
                console.exit(err)
    else:
        if console.json:
            console.msg_json(dict(streams=streams, plugin=plugin.module))
        else:
            validstreams = format_valid_streams(streams)
            console.msg("Found streams: {0}", validstreams)


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
