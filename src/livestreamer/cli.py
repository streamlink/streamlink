import sys, os, argparse, subprocess
import livestreamer

from livestreamer.compat import input, stdout, is_win32
from livestreamer.logger import Logger

exampleusage = """
example usage:

$ livestreamer twitch.tv/onemoregametv
Found streams: 240p, 360p, 480p, 720p, best, iphonehigh, iphonelow, live
$ livestreamer twitch.tv/onemoregametv 720p

Stream now playbacks in player (default is VLC).

"""

logger = Logger("cli")
msg_output = sys.stdout
parser = livestreamer.utils.ArgumentParser(description="CLI program that launches streams from various streaming services in a custom video player",
                                           fromfile_prefix_chars="@",
                                           formatter_class=argparse.RawDescriptionHelpFormatter,
                                           epilog=exampleusage, add_help=False)

parser.add_argument("url", help="URL to stream", nargs="?")
parser.add_argument("stream", help="Stream quality to play, use 'best' for highest quality available", nargs="?")

parser.add_argument("-h", "--help", action="store_true", help="Show this help message and exit")
parser.add_argument("-u", "--plugins", action="store_true", help="Print all currently installed plugins")
parser.add_argument("-l", "--loglevel", metavar="level", help="Set log level, valid levels: none, error, warning, info, debug", default="info")

playeropt = parser.add_argument_group("player options")
playeropt.add_argument("-p", "--player", metavar="player", help="Command-line for player, default is 'vlc'", default="vlc")
playeropt.add_argument("-q", "--quiet-player", action="store_true", help="Hide all player console output")

outputopt = parser.add_argument_group("file output options")
outputopt.add_argument("-o", "--output", metavar="filename", help="Write stream to file instead of playing it")
outputopt.add_argument("-f", "--force", action="store_true", help="Always write to file even if it already exists")
outputopt.add_argument("-O", "--stdout", action="store_true", help="Write stream to stdout instead of playing it")

pluginopt = parser.add_argument_group("plugin options")
pluginopt.add_argument("-c", "--cmdline", action="store_true", help="Print command-line used internally to play stream, this may not be available on all streams")
pluginopt.add_argument("-e", "--errorlog", action="store_true", help="Log possible errors from internal command-line to a temporary file, use when debugging")
pluginopt.add_argument("-r", "--rtmpdump", metavar="path", help="Specify location of rtmpdump")
pluginopt.add_argument("-j", "--jtv-cookie", metavar="cookie", help="Specify JustinTV cookie to allow access to subscription channels")

RCFILE = os.path.expanduser("~/.livestreamerrc")

def exit(msg):
    sys.exit(("error: {0}").format(msg))

def msg(msg):
    msg_output.write(msg + "\n")

def set_msg_output(output):
    msg_output = output
    logger.set_output(output)

def write_stream(fd, out, progress):
    written = 0

    while True:
        try:
            data = fd.read(8192)
        except IOError:
            logger.error("Error when reading from stream")
            break

        if len(data) == 0:
            break

        try:
            out.write(data)
        except IOError:
            logger.error("Error when writing to output")
            break

        written += len(data)

        if progress:
            sys.stderr.write(("\rWritten {0} bytes").format(written))

    if progress and written > 0:
        sys.stderr.write("\n")

    logger.info("Stream ended")
    fd.close()

    if out != stdout:
        out.close()

def check_output(output, force):
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
        exit(("Failed to open file {0} - ").format(output, err))

    return out

def output_stream(stream, args):
    progress = False
    out = None
    player = None

    logger.info("Opening stream: {0}", args.stream)

    try:
        fd = stream.open()
    except livestreamer.StreamError as err:
        exit(("Could not open stream - {0}").format(err))

    logger.debug("Pre-buffering 8192 bytes")
    try:
        prebuffer = fd.read(8192)
    except IOError:
        exit("Failed to read data from stream")

    if len(prebuffer) == 0:
        exit("Failed to read data from stream")

    logger.debug("Checking output")

    if args.output:
        if args.output == "-":
            out = stdout
        else:
            out = check_output(args.output, args.force)
            progress = True
    elif args.stdout:
        out = stdout
    else:
        cmd = args.player + " -"

        if args.quiet_player:
            pout = open(os.devnull, "w")
            perr = open(os.devnull, "w")
        else:
            pout = sys.stderr
            perr = sys.stdout

        logger.info("Starting player: {0}", args.player)
        player = subprocess.Popen(cmd, shell=True, stdout=pout, stderr=perr,
                                  stdin=subprocess.PIPE)
        out = player.stdin

    if not out:
        exit("Failed to open a valid stream output")

    if is_win32:
        import msvcrt
        msvcrt.setmode(out.fileno(), os.O_BINARY)

    logger.debug("Writing stream to output")
    out.write(prebuffer)

    try:
        write_stream(fd, out, progress)
    except KeyboardInterrupt:
        pass

    if player:
        try:
            player.kill()
        except:
            pass

def handle_url(args):
    try:
        channel = livestreamer.resolve_url(args.url)
    except livestreamer.NoPluginError:
        exit(("No plugin can handle URL: {0}").format(args.url))

    logger.info("Found matching plugin {0} for URL {1}", channel.module, args.url)

    try:
        streams = channel.get_streams()
    except livestreamer.StreamError as err:
        exit(str(err))
    except livestreamer.PluginError as err:
        exit(str(err))

    if len(streams) == 0:
        exit(("No streams found on this URL: {0}").format(args.url))

    keys = list(streams.keys())
    keys.sort()
    validstreams = (", ").join(keys)

    if args.stream:
        if args.stream in streams:
            stream = streams[args.stream]

            if args.cmdline:
                if isinstance(stream, livestreamer.stream.StreamProcess):
                    msg(stream.cmdline())
                else:
                    exit("Stream does not use a command-line")
            else:
                output_stream(stream, args)
        else:
            msg(("Invalid stream quality: {0}").format(args.stream))
            msg(("Valid streams: {0}").format(validstreams))
    else:
        msg(("Found streams: {0}").format(validstreams))


def print_plugins():
    pluginlist = list(livestreamer.get_plugins().keys())
    msg(("Installed plugins: {0}").format(", ".join(pluginlist)))


def main():
    arglist = sys.argv[1:]

    if os.path.exists(RCFILE):
        arglist.insert(0, "@" + RCFILE)

    args = parser.parse_args(arglist)

    if args.stdout or args.output == "-":
        set_msg_output(sys.stderr)

    livestreamer.options.set("errorlog", args.errorlog)
    livestreamer.options.set("rtmpdump", args.rtmpdump)
    livestreamer.options.set("jtvcookie", args.jtv_cookie)
    logger.set_level(args.loglevel)

    if args.url:
        handle_url(args)
    elif args.plugins:
        print_plugins()
    else:
        parser.print_help()
