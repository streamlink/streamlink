class Options(object):
    def __init__(self, defaults=None):
        if not defaults:
            defaults = {}

        self.defaults = defaults
        self.options = defaults.copy()

    def set(self, key, value):
        self.options[key] = value

    def get(self, key):
        if key in self.options:
            return self.options[key]

__all__ = ["Options"]
