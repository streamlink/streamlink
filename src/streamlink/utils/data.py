try:
    from typing import Any, Dict, List, Union
except ImportError:
    pass


def search_dict(data, key):
    # type: (Union[Dict, List], Any)
    """
    Search for a key in a nested dict, or list of nested dicts, and return the values.

    :param data: dict/list to search
    :param key: key to find
    :return: matches for key
    """
    if isinstance(data, dict):
        for dkey, value in data.items():
            if dkey == key:
                yield value
            for result in search_dict(value, key):
                yield result
    elif isinstance(data, list):
        for value in data:
            for result in search_dict(value, key):
                yield result
