from __future__ import annotations

from typing import Any


def search_dict(data: dict | list, key: Any):
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
            yield from search_dict(value, key)
    elif isinstance(data, list):
        for value in data:
            yield from search_dict(value, key)
