import string


class LazyFormatter:
    def __init__(self, **lazy_props):
        self.lazy_props = lazy_props

    def __getitem__(self, item):
        value = self.lazy_props[item]
        if callable(value):
            return value()
        else:
            return value

    @classmethod
    def format(cls, *args, **lazy_props):
        if len(args) == 1:
            fmt = args[0]
        else:
            raise TypeError("format() takes exactly 1 positional argument")

        return string.Formatter().vformat(fmt, (), cls(**lazy_props))
