import string

class LazyFormatter(object):
    def __init__(self, **lazy_props):
        self.lazy_props = lazy_props

    def __getitem__(self, item):
        value = self.lazy_props[item]
        if callable(value):
            return value()
        else:
            return value

    @classmethod
    def format(cls, fmt, **lazy_props):
        return string.Formatter().vformat(fmt, (), cls(**lazy_props))
