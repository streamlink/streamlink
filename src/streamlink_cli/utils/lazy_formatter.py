import string

class LazyFormatter(object):
    def __init__(self, **lazy_props):
        self.lazy_props = lazy_props

    def __getitem__(self, item):
        value = self.lazy_props[item]
        if value[0] is None:
            return value[1]
        else:
            return value[0]

    @classmethod
    def format(cls, fmt, **lazy_props):
        return string.Formatter().vformat(fmt, (), cls(**lazy_props))
