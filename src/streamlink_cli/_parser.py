"""
Utility module for importing Streamlink's argparse.ArgumentParser instance
when building the documentation, man page or command-line shell completions.
"""

from streamlink.session import Streamlink
from streamlink_cli.argparser import build_parser, setup_plugin_args


def get_parser():
    session = Streamlink(plugins_builtin=True, plugins_lazy=False)
    parser = build_parser()
    setup_plugin_args(session, parser)

    return parser
