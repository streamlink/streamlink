import argparse
import getpass
import os
import sys
import subprocess

from livestreamer import *
from livestreamer.compat import input, stdout, file, is_win32
from livestreamer.stream import StreamProcess
from livestreamer.utils import ArgumentParser, NamedPipe

exampleusage = """
example usage:

$ livestreamer twitch.tv/onemoregametv
Found streams: 240p, 360p, 480p, 720p, best, iphonehigh, iphonelow, live
$ livestreamer twitch.tv/onemoregametv 720p

Stream now playbacks in player (default is VLC).

"""

livestreamer = Livestreamer()
logger = livestreamer.logger.new_module("cli")

msg_output = sys.stdout
parser = ArgumentParser(description="CLI program that launches streams from various streaming services in a custom video player",
                        fromfile_prefix_chars="@",
                        formatter_class=argparse.RawDescriptionHelpFormatter,
                        epilog=exampleusage, add_help=False)

parser.add_argument("url", help="URL to stream", nargs="?")
parser.add_argument("stream", help="Stream quality to play, use 'best' for highest quality available",
                    nargs="?")

parser.add_argument("-h", "--help", action="store_true",
                    help="Show this help message and exit")
parser.add_argument("-V", "--version", action="version", version="%(prog)s " + livestreamer.version)
parser.add_argument("-u", "--plugins", action="store_true",
                    help="Print all currently installed plugins")
parser.add_argument("-l", "--loglevel", metavar="level",
                    help="Set log level, valid levels: none, error, warning, info, debug",
                    default="info")

playeropt = parser.add_argument_group("player options")
playeropt.add_argument("-p", "--player", metavar="player",
                       help="Command-line for player, default is 'vlc --file-caching=5000'",
                       default="vlc --file-caching=5000")
playeropt.add_argument("-q", "--quiet-player", action="store_true",
                       help="Hide all player console output")
playeropt.add_argument("-n", "--fifo", action="store_true",
                       help="Play file using a named pipe instead of stdin (Can help with incompatible media players)")

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
                       help="Specify location of rtmpdump executable, eg. /usr/local/bin/rtmpdump")
streamopt.add_argument("--rtmpdump-proxy", metavar="host:port",
                       help="Specify a proxy (SOCKS) that rtmpdump will use")

pluginopt = parser.add_argument_group("plugin options")
pluginopt.add_argument("--plugin-dirs", metavar="directory",
                       help="Attempts to load plugins from these directories. Multiple directories can be used by separating them with a ;.")
pluginopt.add_argument("--jtv-cookie", metavar="cookie",
                       help="Specify JustinTV cookie to allow access to subscription channels")
pluginopt.add_argument("--gomtv-cookie", metavar="cookie",
                       help="Specify GOMTV cookie to allow access to streams")
pluginopt.add_argument("--gomtv-username", metavar="username",
                       help="Specify GOMTV username to allow access to streams")
pluginopt.add_argument("--gomtv-password", metavar="password",
                       help="Specify GOMTV password to allow access to streams (If left blank you will be prompted)",
                       nargs="?", const=True, default=None)

if is_win32:
    RCFILE = os.path.join(os.environ["APPDATA"], "livestreamer", "livestreamerrc")
else:
    RCFILE = os.path.expanduser("~/.livestreamerrc")

def exit(*args, **kw):
    logger.error(*args, **kw)
    sys.exit()

def msg(msg):
    msg_output.write(msg + "\n")

def set_msg_output(output):
    msg_output = output
    livestreamer.set_logoutput(output)

def write_stream(fd, out, progress, player):
    written = 0

    while True:
        if player:
            player.poll()
            if player.returncode is not None:
                logger.info("Player closed")
                break

        try:
            data = fd.read(8192)
        except IOError as err:
            logger.error("Error when reading from stream: {0}", str(err))
            break

        if len(data) == 0:
            break

        try:
            out.write(data)
        except IOError as err:
            logger.error("Error when writing to output: {0}", str(err))
            break

        written += len(data)

        if progress:
            sys.stderr.write(("\rWritten {0} bytes").format(written))

    if progress and written > 0:
        sys.stderr.write("\n")

    logger.info("Stream ended")

def check_output(output, force):
    logger.debug("Checking output")

    if os.path.isfile(output) and not force:
        sys.stderr.write(("File {0} already exists! Overwrite it? [y/N] ").format(output))

        try:
            answer = input()
        except:
            sys.exit()

        answer = answer.strip().lower()

        if answer != "y":
            sys.exit()

    try:
        out = open(output, "wb")
    except IOError as err:
        exit("Failed to open file {0} - {1}", output, err)

    return out

def output_stream(stream, streamname, args):
    progress = False
    out = None
    player = None

    logger.info("Opening stream: {0}", streamname)

    try:
        fd = stream.open()
    except StreamError as err:
        logger.error("Could not open stream: {0}", err)
        return

    logger.debug("Pre-buffering 8192 bytes")
    try:
        prebuffer = fd.read(8192)
    except IOError as err:
        logger.error("Failed to read data from stream: {0}", str(err))
        return

    if len(prebuffer) == 0:
        logger.error("Failed to read data from stream")
        return

    if args.output:
        if args.output == "-":
            out = stdout
        else:
            out = check_output(args.output, args.force)
            progress = True
    elif args.stdout:
        out = stdout
    else:
        if args.fifo:
            pipename = "livestreamerpipe-" + str(os.getpid())

            logger.info("Creating pipe {0}", pipename)

            try:
                out = NamedPipe(pipename)
            except IOError as err:
                exit("Failed to create pipe: {0}", err)

            cmd = args.player + " " + out.path
            pin = sys.stdin
        else:
            cmd = args.player + " -"
            pin = subprocess.PIPE

        if args.quiet_player:
            pout = open(os.devnull, "w")
            perr = open(os.devnull, "w")
        else:
            pout = sys.stderr
            perr = sys.stdout

        logger.info("Starting player: {0}", args.player)
        player = subprocess.Popen(cmd, shell=True, stdout=pout, stderr=perr,
                                  stdin=pin)

        if args.fifo:
            try:
                out.open("wb")
            except IOError as err:
                exit("Failed to open pipe {0} - {1}", pipename, err)
        else:
            out = player.stdin

    if not out:
        exit("Failed to open a valid stream output")

    if is_win32 and isinstance(out, file):
        import msvcrt
        msvcrt.setmode(out.fileno(), os.O_BINARY)

    logger.debug("Writing stream to output")

    try:
        out.write(prebuffer)
    except IOError as err:
        exit("Error when writing to output: {0}", str(err))

    try:
        write_stream(fd, out, progress, player)
    except KeyboardInterrupt:
        pass

    if player:
        try:
            player.kill()
        except:
            pass

    if out != stdout:
        try:
            out.close()
        except:
            pass

    return True

def handle_stream(args, streams):
    streamname = args.stream
    stream = streams[streamname]

    if args.cmdline:
        if isinstance(stream, StreamProcess):
            try:
                cmdline = stream.cmdline()
            except StreamError as err:
                exit(err)

            msg(cmdline)
        else:
            exit("Stream does not use a command-line")
    else:
        success = False
        altcount = 1

        while not success:
            success = output_stream(stream, streamname, args)

            if altcount == 1:
                streamname = args.stream + "_alt"
            else:
                streamname = args.stream + "_alt{0}".format(altcount)

            if streamname in streams:
                stream = streams[streamname]
            else:
                break

            altcount += 1

def handle_url(args):
    try:
        channel = livestreamer.resolve_url(args.url)
    except NoPluginError:
        exit("No plugin can handle URL: {0}", args.url)

    logger.info("Found matching plugin {0} for URL {1}", channel.module, args.url)

    try:
        streams = channel.get_streams()
    except (StreamError, PluginError) as err:
        exit(str(err))

    if len(streams) == 0:
        exit("No streams found on this URL: {0}", args.url)

    keys = list(streams.keys())
    keys.sort()
    validstreams = (", ").join(keys)

    if args.stream:
        if args.stream == "best":
            for name, stream in streams.items():
                if stream is streams["best"] and name != "best":
                    args.stream = name

        if args.stream in streams:
            handle_stream(args, streams)
        else:
            msg(("Invalid stream quality: {0}").format(args.stream))
            msg(("Valid streams: {0}").format(validstreams))
    else:
        msg(("Found streams: {0}").format(validstreams))

def print_plugins():
    pluginlist = list(livestreamer.get_plugins().keys())
    msg(("Installed plugins: {0}").format(", ".join(pluginlist)))

def load_plugins(dirs):
    dirs = [os.path.expanduser(d) for d in dirs.split(";")]
    for directory in dirs:
        if os.path.isdir(directory):
            livestreamer.load_plugins(directory)
        else:
            logger.warning("Plugin directory {0} does not exist!", directory)

def set_options(args):
    if args.gomtv_username and (args.gomtv_password is None or (len(args.gomtv_password) < 1)):
        gomtv_password = getpass.getpass("Enter GOMTV password: ")
    else:
        gomtv_password = args.gomtv_password

    livestreamer.set_option("errorlog", args.errorlog)

    if args.rtmpdump:
        livestreamer.set_option("rtmpdump", args.rtmpdump)

    if args.rtmpdump_proxy:
        livestreamer.set_option("rtmpdump-proxy", args.rtmpdump_proxy)

    if args.jtv_cookie:
        livestreamer.set_plugin_option("justintv", "cookie", args.jtv_cookie)

    if args.gomtv_cookie:
        livestreamer.set_plugin_option("gomtv", "cookie", args.gomtv_cookie)

    if args.gomtv_username:
        livestreamer.set_plugin_option("gomtv", "username", args.gomtv_username)

    if gomtv_password:
        livestreamer.set_plugin_option("gomtv", "password", gomtv_password)

    livestreamer.set_loglevel(args.loglevel)

def main():
    arglist = sys.argv[1:]

    if os.path.exists(RCFILE):
        arglist.insert(0, "@" + RCFILE)

    args = parser.parse_args(arglist)

    if args.stdout or args.output == "-":
        set_msg_output(sys.stderr)

    set_options(args)

    if args.plugin_dirs:
        load_plugins(args.plugin_dirs)

    if args.url:
        handle_url(args)
    elif args.plugins:
        print_plugins()
    else:
        parser.print_help()
