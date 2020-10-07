import os
import inspect

is_win32 = os.name == "nt"

# win/nix compatible devnull
try:
    from subprocess import DEVNULL

    def devnull():
        return DEVNULL
except ImportError:
    def devnull():
        return open(os.path.devnull, 'w')


getargspec = getattr(inspect, "getfullargspec", inspect.getargspec)


__all__ = ["is_win32", "devnull", "getargspec"]
