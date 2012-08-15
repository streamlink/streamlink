import sys

class Logger(object):
    Levels = ["none", "error", "warning", "info", "debug"]
    Format = "[{module}][{level}] {msg}\n"

    output = sys.stdout
    level = 0

    @classmethod
    def set_level(cls, level):
        try:
            index = Logger.Levels.index(level)
        except ValueError:
            return

        cls.level = index

    @classmethod
    def set_output(cls, output):
        cls.output = output

    def __init__(self, module):
        self.module = module

    def msg(self, level, msg, *args):
        if Logger.level < level or level > len(Logger.Levels):
            return

        msg = msg.format(*args)

        self.output.write(Logger.Format.format(module=self.module,
                                               level=Logger.Levels[level],
                                               msg=msg))
        self.output.flush()

    def error(self, msg, *args):
        self.msg(1, msg, *args)

    def warning(self, msg, *args):
        self.msg(2, msg, *args)

    def info(self, msg, *args):
        self.msg(3, msg, *args)

    def debug(self, msg, *args):
        self.msg(4, msg, *args)


__all__ = ["Logger"]
