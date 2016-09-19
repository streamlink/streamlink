from functools import partial
from itertools import product
from operator import eq


class StreamMapper(object):
    """The stream mapper can be used to simplify the process of creating
       stream objects from data.

    :param cmp: This callable is used to compare each mapping's key
                with a value.
    """
    def __init__(self, cmp=eq):
        self._map = []
        self._cmp = cmp

    def map(self, key, func, *args, **kwargs):
        """Creates a key-function mapping.

        The return value from the function should be either
          - A tuple containing a name and stream
          - A iterator of tuples containing a name and stream

        Any extra arguments will be passed to the function.
        """
        self._map.append((key, partial(func, *args, **kwargs)))

    def _cmp_filter(self, args):
        value, (key, func) = args
        return self._cmp(key, value)

    def _mapped_func(self, args):
        value, (key, func) = args
        return func(value)

    def __call__(self, values):
        """Runs through each value and transform it with a mapped function."""
        values = product(values, self._map)
        for value in map(self._mapped_func, filter(self._cmp_filter, values)):
            if isinstance(value, tuple) and len(value) == 2:
                yield value
            else:
                try:
                    # TODO: Replace with "yield from" when dropping Python 2.
                    for __ in value:
                        yield __
                except TypeError:
                    # Non-iterable returned
                    continue
