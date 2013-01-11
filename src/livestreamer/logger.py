import sys

from threading import Lock

class Logger(object):
    Levels = ["none", "error", "warning", "info", "debug"]
    Format = "[{module}][{level}] {msg}\n"

    def __init__(self):
        self.output = sys.stdout
        self.level = 0
        self.lock = Lock()

    def new_module(self, module):
        return LoggerModule(self, module)

    def set_level(self, level):
        try:
            index = Logger.Levels.index(level)
        except ValueError:
            return

        self.level = index

    def set_output(self, output):
        self.output = output

    def msg(self, module, level, msg, *args, **kw):
        if self.level < level or level > len(Logger.Levels):
            return

        msg = msg.format(*args, **kw)

        with self.lock:
            self.output.write(Logger.Format.format(module=module,
                                                   level=Logger.Levels[level],
                                                   msg=msg))
            if hasattr(self.output, "flush"):
                self.output.flush()

class LoggerModule(object):
    def __init__(self, manager, module):
        self.manager = manager
        self.module = module

    def error(self, msg, *args, **kw):
        self.manager.msg(self.module, 1, msg, *args, **kw)

    def warning(self, msg, *args, **kw):
        self.manager.msg(self.module, 2, msg, *args, **kw)

    def info(self, msg, *args, **kw):
        self.manager.msg(self.module, 3, msg, *args, **kw)

    def debug(self, msg, *args, **kw):
        self.manager.msg(self.module, 4, msg, *args, **kw)

__all__ = ["Logger"]
