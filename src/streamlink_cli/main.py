import errno
import os
import requests
import sys
import signal
import webbrowser

from contextlib import closing
from distutils.version import StrictVersion
from functools import partial
from itertools import chain
from time import sleep

from streamlink import (Streamlink, StreamError, PluginError,
                          NoPluginError)
from streamlink.cache import Cache
from streamlink.stream import StreamProcess
from streamlink.plugins.twitch import TWITCH_CLIENT_ID

from .argparser import parser
from .compat import stdout, is_win32
from .console import ConsoleOutput
from .constants import CONFIG_FILES, PLUGINS_DIR, STREAM_SYNONYMS
from .output import FileOutput, PlayerOutput
from .utils import NamedPipe, HTTPServer, ignored, progress, stream_to_url

ACCEPTABLE_ERRNO = (errno.EPIPE, errno.EINVAL, errno.ECONNRESET)
QUIET_OPTIONS = ("json", "stream_url", "subprocess_cmdline", "quiet")

args = console = streamlink = plugin = stream_fd = output = None


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

        if not args.player:
            console.exit("The default player (VLC) does not seem to be "
                         "installed. You must specify the path to a player "
                         "executable with --player.")

        if args.player_fifo:
            pipename = "streamlinkpipe-{0}".format(os.getpid())
            console.logger.info("Creating pipe {0}", pipename)

            try:
                namedpipe = NamedPipe(pipename)
            except IOError as err:
                console.exit("Failed to create pipe: {0}", err)
        elif args.player_http:
            http = create_http_server()

        console.logger.info("Starting player: {0}", args.player)
        out = PlayerOutput(args.player, args=args.player_args,
                           quiet=not args.verbose_player,
                           kill=not args.player_no_close,
                           namedpipe=namedpipe, http=http)

    return out


def create_http_server(host=None, port=0):
    """Creates a HTTP server listening on a given host and port.

    If host is empty, listen on all available interfaces, and if port is 0,
    listen on a random high port.
    """

    try:
        http = HTTPServer()
        http.bind(host=host, port=port)
    except OSError as err:
        console.exit("Failed to create HTTP server: {0}", err)

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


def output_stream_http(plugin, initial_streams, external=False, port=0):
    """Continuously output the stream over HTTP."""
    global output

    if not external:
        if not args.player:
            console.exit("The default player (VLC) does not seem to be "
                         "installed. You must specify the path to a player "
                         "executable with --player.")

        server = create_http_server()
        player = output = PlayerOutput(args.player, args=args.player_args,
                                       filename=server.url,
                                       quiet=not args.verbose_player)

        try:
            console.logger.info("Starting player: {0}", args.player)
            if player:
                player.open()
        except OSError as err:
            console.exit("Failed to start player: {0} ({1})",
                         args.player, err)
    else:
        server = create_http_server(host=None, port=port)
        player = None

        console.logger.info("Starting server, access with one of:")
        for url in server.urls:
            console.logger.info(" " + url)

    for req in iter_http_requests(server, player):
        user_agent = req.headers.get("User-Agent") or "unknown player"
        console.logger.info("Got HTTP request from {0}".format(user_agent))

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
                    console.logger.info("Stream not available, will re-fetch "
                                        "streams in 10 sec")
                    sleep(10)
                    continue
            except PluginError as err:
                console.logger.error(u"Unable to fetch new streams: {0}", err)
                continue

            try:
                console.logger.info("Opening stream: {0} ({1})", stream_name,
                                    type(stream).shortname())
                stream_fd, prebuffer = open_stream(stream)
            except StreamError as err:
                console.logger.error("{0}", err)

        if stream_fd and prebuffer:
            console.logger.debug("Writing stream to player")
            read_stream(stream_fd, server, prebuffer)

        server.close(True)

    player.close()
    server.close()


def output_stream_passthrough(stream):
    """Prepares a filename to be passed to the player."""
    global output

    filename = '"{0}"'.format(stream_to_url(stream))
    output = PlayerOutput(args.player, args=args.player_args,
                          filename=filename, call=True,
                          quiet=not args.verbose_player)

    try:
        console.logger.info("Starting player: {0}", args.player)
        output.open()
    except OSError as err:
        console.exit("Failed to start player: {0} ({1})", args.player, err)
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
    global output

    for i in range(args.retry_open):
        try:
            stream_fd, prebuffer = open_stream(stream)
            break
        except StreamError as err:
            console.logger.error("{0}", err)
    else:
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

    with closing(output):
        console.logger.debug("Writing stream to output")
        read_stream(stream_fd, output, prebuffer)

    return True


def read_stream(stream, output, prebuffer, chunk_size=8192):
    """Reads data from stream and then writes it to the output."""
    is_player = isinstance(output, PlayerOutput)
    is_http = isinstance(output, HTTPServer)
    is_fifo = is_player and output.namedpipe
    show_progress = isinstance(output, FileOutput) and output.fd is not stdout

    stream_iterator = chain(
        [prebuffer],
        iter(partial(stream.read, chunk_size), b"")
    )
    if show_progress:
        stream_iterator = progress(stream_iterator,
                                   prefix=os.path.basename(args.output))

    try:
        for data in stream_iterator:
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
                    console.logger.error("Error when writing to output: {0}", err)

                break
    except IOError as err:
        console.logger.error("Error when reading from stream: {0}", err)

    stream.close()
    console.logger.info("Stream ended")


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
                console.exit("{0}", err)

            console.msg("{0}", cmdline)
        else:
            console.exit("The stream specified cannot be translated to a command")

    # Print JSON representation of the stream
    elif console.json:
        console.msg_json(stream)

    elif args.stream_url:
        url = stream_to_url(stream)
        if url:
            console.msg("{0}", url)
        else:
            console.exit("The stream specified cannot be translated to a URL")

    # Output the stream
    else:
        # Find any streams with a '_alt' suffix and attempt
        # to use these in case the main stream is not usable.
        alt_streams = list(filter(lambda k: stream_name + "_alt" in k,
                                  sorted(streams.keys())))
        file_output = args.output or args.stdout

        for stream_name in [stream_name] + alt_streams:
            stream = streams[stream_name]
            stream_type = type(stream).shortname()

            if stream_type in args.player_passthrough and not file_output:
                console.logger.info("Opening stream: {0} ({1})", stream_name,
                                    stream_type)
                success = output_stream_passthrough(stream)
            elif args.player_external_http:
                return output_stream_http(plugin, streams, external=True,
                                          port=args.player_external_http_port)
            elif args.player_continuous_http and not file_output:
                return output_stream_http(plugin, streams)
            else:
                console.logger.info("Opening stream: {0} ({1})", stream_name,
                                    stream_type)
                success = output_stream(stream)

            if success:
                break


def fetch_streams(plugin):
    """Fetches streams using correct parameters."""

    return plugin.get_streams(stream_types=args.stream_types,
                              sorting_excludes=args.stream_sorting_excludes)


def fetch_streams_infinite(plugin, interval):
    """Attempts to fetch streams until some are returned."""

    try:
        streams = fetch_streams(plugin)
    except PluginError as err:
        console.logger.error(u"{0}", err)
        streams = None

    if not streams:
        console.logger.info("Waiting for streams, retrying every {0} "
                            "second(s)", args.retry_streams)
    while not streams:
        sleep(args.retry_streams)

        try:
            streams = fetch_streams(plugin)
        except PluginError as err:
            console.logger.error(u"{0}", err)

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
        plugin = streamlink.resolve_url(args.url)
        console.logger.info("Found matching plugin {0} for URL {1}",
                            plugin.module, args.url)

        if args.retry_streams:
            streams = fetch_streams_infinite(plugin, args.retry_streams)
        else:
            streams = fetch_streams(plugin)
    except NoPluginError:
        console.exit("No plugin can handle URL: {0}", args.url)
    except PluginError as err:
        console.exit(u"{0}", err)

    if not streams:
        console.exit("No streams found on this URL: {0}", args.url)

    if args.best_stream_default:
        args.default_stream = ["best"]

    if args.default_stream and not args.stream and not args.json:
        args.stream = args.default_stream

    if args.stream:
        validstreams = format_valid_streams(plugin, streams)
        for stream_name in args.stream:
            if stream_name in streams:
                console.logger.info("Available streams: {0}", validstreams)
                handle_stream(plugin, streams, stream_name)
                return

        err = ("The specified stream(s) '{0}' could not be "
               "found".format(", ".join(args.stream)))

        if console.json:
            console.msg_json(dict(streams=streams, plugin=plugin.module,
                                  error=err))
        else:
            console.exit("{0}.\n       Available streams: {1}",
                         err, validstreams)
    else:
        if console.json:
            console.msg_json(dict(streams=streams, plugin=plugin.module))
        else:
            validstreams = format_valid_streams(plugin, streams)
            console.msg("Available streams: {0}", validstreams)


def print_plugins():
    """Outputs a list of all plugins Streamlink has loaded."""

    pluginlist = list(streamlink.get_plugins().keys())
    pluginlist_formatted = ", ".join(sorted(pluginlist))

    if console.json:
        console.msg_json(pluginlist)
    else:
        console.msg("Loaded plugins: {0}", pluginlist_formatted)


def authenticate_twitch_oauth():
    """Opens a web browser to allow the user to grant Streamlink
       access to their Twitch account."""

    client_id = TWITCH_CLIENT_ID
    redirect_uri = "http://streamlink.tanuki.se/en/develop/twitch_oauth.html"
    url = ("https://api.twitch.tv/kraken/oauth2/authorize/"
           "?response_type=token&client_id={0}&redirect_uri="
           "{1}&scope=user_read+user_subscriptions").format(client_id, redirect_uri)

    console.msg("Attempting to open a browser to let you authenticate "
                "Streamlink with Twitch")

    try:
        if not webbrowser.open_new_tab(url):
            raise webbrowser.Error
    except webbrowser.Error:
        console.exit("Unable to open a web browser, try accessing this URL "
                     "manually instead:\n{0}".format(url))


def load_plugins(dirs):
    """Attempts to load plugins from a list of directories."""

    dirs = [os.path.expanduser(d) for d in dirs]

    for directory in dirs:
        if os.path.isdir(directory):
            streamlink.load_plugins(directory)
        else:
            console.logger.warning("Plugin path {0} does not exist or is not "
                                   "a directory!", directory)


def setup_args(config_files=[]):
    """Parses arguments."""
    global args
    arglist = sys.argv[1:]

    # Load arguments from config files
    for config_file in filter(os.path.isfile, config_files):
        arglist.insert(0, "@" + config_file)

    args = parser.parse_args(arglist)

    # Force lowercase to allow case-insensitive lookup
    if args.stream:
        args.stream = [stream.lower() for stream in args.stream]


def setup_config_args():
    config_files = []

    if args.url:
        with ignored(NoPluginError):
            plugin = streamlink.resolve_url(args.url)
            config_files += ["{0}.{1}".format(fn, plugin.module) for fn in CONFIG_FILES]

    if args.config:
        # We want the config specified last to get highest priority
        config_files += list(reversed(args.config))
    else:
        # Only load first available default config
        for config_file in filter(os.path.isfile, CONFIG_FILES):
            config_files.append(config_file)
            break

    if config_files:
        setup_args(config_files)


def setup_console():
    """Console setup."""
    global console

    # All console related operations is handled via the ConsoleOutput class
    console = ConsoleOutput(sys.stdout, streamlink)

    # Console output should be on stderr if we are outputting
    # a stream to stdout.
    if args.stdout or args.output == "-":
        console.set_output(sys.stderr)

    # We don't want log output when we are printing JSON or a command-line.
    if not any(getattr(args, attr) for attr in QUIET_OPTIONS):
        console.set_level(args.loglevel)

    if args.quiet_player:
        console.logger.warning("The option --quiet-player is deprecated since "
                               "version 1.4.3 as hiding player output is now "
                               "the default.")

    if args.best_stream_default:
        console.logger.warning("The option --best-stream-default is deprecated "
                               "since version 1.9.0, use '--default-stream best' "
                               "instead.")

    console.json = args.json

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

    if args.http_ssl_cert:
        streamlink.set_option("http-ssl-cert", args.http_ssl_cert)

    if args.http_ssl_cert_crt_key:
        streamlink.set_option("http-ssl-cert", tuple(args.http_ssl_cert_crt_key))

    if args.http_timeout:
        streamlink.set_option("http-timeout", args.http_timeout)

    if args.http_cookies:
        console.logger.warning("The option --http-cookies is deprecated since "
                               "version 1.11.0, use --http-cookie instead.")
        streamlink.set_option("http-cookies", args.http_cookies)

    if args.http_headers:
        console.logger.warning("The option --http-headers is deprecated since "
                               "version 1.11.0, use --http-header instead.")
        streamlink.set_option("http-headers", args.http_headers)

    if args.http_query_params:
        console.logger.warning("The option --http-query-params is deprecated since "
                               "version 1.11.0, use --http-query-param instead.")
        streamlink.set_option("http-query-params", args.http_query_params)


def setup_plugins():
    """Loads any additional plugins."""
    if os.path.isdir(PLUGINS_DIR):
        load_plugins([PLUGINS_DIR])

    if args.plugin_dirs:
        load_plugins(args.plugin_dirs)


def setup_streamlink():
    """Creates the Streamlink session."""
    global streamlink

    streamlink = Streamlink()


def setup_options():
    """Sets Streamlink options."""
    if args.hls_live_edge:
        streamlink.set_option("hls-live-edge", args.hls_live_edge)

    if args.hls_segment_attempts:
        streamlink.set_option("hls-segment-attempts", args.hls_segment_attempts)

    if args.hls_segment_threads:
        streamlink.set_option("hls-segment-threads", args.hls_segment_threads)

    if args.hls_segment_timeout:
        streamlink.set_option("hls-segment-timeout", args.hls_segment_timeout)

    if args.hls_timeout:
        streamlink.set_option("hls-timeout", args.hls_timeout)

    if args.hds_live_edge:
        streamlink.set_option("hds-live-edge", args.hds_live_edge)

    if args.hds_segment_attempts:
        streamlink.set_option("hds-segment-attempts", args.hds_segment_attempts)

    if args.hds_segment_threads:
        streamlink.set_option("hds-segment-threads", args.hds_segment_threads)

    if args.hds_segment_timeout:
        streamlink.set_option("hds-segment-timeout", args.hds_segment_timeout)

    if args.hds_timeout:
        streamlink.set_option("hds-timeout", args.hds_timeout)

    if args.http_stream_timeout:
        streamlink.set_option("http-stream-timeout", args.http_stream_timeout)

    if args.ringbuffer_size:
        streamlink.set_option("ringbuffer-size", args.ringbuffer_size)

    if args.rtmp_proxy:
        streamlink.set_option("rtmp-proxy", args.rtmp_proxy)

    if args.rtmp_rtmpdump:
        streamlink.set_option("rtmp-rtmpdump", args.rtmp_rtmpdump)

    if args.rtmp_timeout:
        streamlink.set_option("rtmp-timeout", args.rtmp_timeout)

    if args.stream_segment_attempts:
        streamlink.set_option("stream-segment-attempts", args.stream_segment_attempts)

    if args.stream_segment_threads:
        streamlink.set_option("stream-segment-threads", args.stream_segment_threads)

    if args.stream_segment_timeout:
        streamlink.set_option("stream-segment-timeout", args.stream_segment_timeout)

    if args.stream_timeout:
        streamlink.set_option("stream-timeout", args.stream_timeout)

    streamlink.set_option("subprocess-errorlog", args.subprocess_errorlog)

    # Deprecated options
    if args.hds_fragment_buffer:
        console.logger.warning("The option --hds-fragment-buffer is deprecated "
                               "and will be removed in the future. Use "
                               "--ringbuffer-size instead")


def setup_plugin_options():
    """Sets Streamlink plugin options."""
    if args.twitch_cookie:
        streamlink.set_plugin_option("twitch", "cookie",
                                       args.twitch_cookie)

    if args.twitch_oauth_token:
        streamlink.set_plugin_option("twitch", "oauth_token",
                                       args.twitch_oauth_token)

    if args.twitch_disable_hosting:
        streamlink.set_plugin_option("twitch", "disable_hosting",
                                       args.twitch_disable_hosting)

    if args.ustream_password:
        streamlink.set_plugin_option("ustreamtv", "password",
                                       args.ustream_password)

    if args.crunchyroll_username:
        streamlink.set_plugin_option("crunchyroll", "username",
                                       args.crunchyroll_username)

    if args.crunchyroll_username and not args.crunchyroll_password:
        crunchyroll_password = console.askpass("Enter Crunchyroll password: ")
    else:
        crunchyroll_password = args.crunchyroll_password

    if crunchyroll_password:
        streamlink.set_plugin_option("crunchyroll", "password",
                                       crunchyroll_password)
    if args.crunchyroll_purge_credentials:
        streamlink.set_plugin_option("crunchyroll", "purge_credentials",
                                       args.crunchyroll_purge_credentials)

    if args.crunchyroll_locale:
        streamlink.set_plugin_option("crunchyroll", "locale",
                                       args.crunchyroll_locale)

    if args.livestation_email:
        streamlink.set_plugin_option("livestation", "email",
                                       args.livestation_email)

    if args.livestation_password:
        streamlink.set_plugin_option("livestation", "password",
                                       args.livestation_password)

    # Deprecated options
    if args.jtv_legacy_names:
        console.logger.warning("The option --jtv/twitch-legacy-names is "
                               "deprecated and will be removed in the future.")

    if args.jtv_cookie:
        console.logger.warning("The option --jtv-cookie is deprecated and "
                               "will be removed in the future.")

    if args.jtv_password:
        console.logger.warning("The option --jtv-password is deprecated "
                               "and will be removed in the future.")

    if args.gomtv_username:
        console.logger.warning("The option --gomtv-username is deprecated "
                               "and will be removed in the future.")

    if args.gomtv_password:
        console.logger.warning("The option --gomtv-password is deprecated "
                               "and will be removed in the future.")

    if args.gomtv_cookie:
        console.logger.warning("The option --gomtv-cookie is deprecated "
                               "and will be removed in the future.")


def check_root():
    if hasattr(os, "getuid"):
        if os.geteuid() == 0 and not args.yes_run_as_root:
            print("streamlink is not supposed to be run as root. "
                  "If you really must you can do it by passing "
                  "--yes-run-as-root.")
            sys.exit(1)


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
        console.logger.info("A new version of Streamlink ({0}) is "
                            "available!".format(latest_version))
        cache.set("version_info_printed", True, (60 * 60 * 6))
    elif force:
        console.logger.info("Your Streamlink version ({0}) is up to date!",
                            installed_version)

    if force:
        sys.exit()


def main():
    setup_args()
    check_root()
    setup_streamlink()
    setup_plugins()
    setup_config_args()
    setup_console()
    setup_http_session()

    if args.version_check or not args.no_version_check:
        with ignored(Exception):
            check_version(force=args.version_check)

    if args.plugins:
        print_plugins()
    elif args.can_handle_url:
        try:
            streamlink.resolve_url(args.can_handle_url)
        except NoPluginError:
            sys.exit(1)
        else:
            sys.exit(0)
    elif args.url:
        try:
            setup_options()
            setup_plugin_options()
            handle_url()
        except KeyboardInterrupt:
            # Close output
            if output:
                output.close()

            # Make sure current stream gets properly cleaned up
            if stream_fd:
                console.msg("Interrupted! Closing currently open stream...")
                try:
                    stream_fd.close()
                except KeyboardInterrupt:
                    sys.exit()
            else:
                console.msg("Interrupted! Exiting...")
    elif args.twitch_oauth_authenticate:
        authenticate_twitch_oauth()
    elif args.help:
        parser.print_help()
    else:
        usage = parser.format_usage()
        msg = (
            "{usage}\nUse -h/--help to see the available options or "
            "read the manual at http://docs.streamlink.io/"
        ).format(usage=usage)
        console.msg(msg)
