class Options(object):
    def __init__(self, defaults={}):
        self.options = defaults

    def set(self, key, value):
        self.options[key] = value

    def get(self, key):
        if key in self.options:
            return self.options[key]

__all__ = ["Options"]
