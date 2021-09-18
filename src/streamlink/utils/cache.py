from collections import OrderedDict
try:
    from typing import Dict, Generic, Optional, TypeVar
    is_typing = True
except ImportError:
    is_typing = False


if is_typing:
    TCacheKey = TypeVar("TCacheKey")
    TCacheValue = TypeVar("TCacheValue")
    _baseClass = Generic[TCacheKey, TCacheValue]
else:
    _baseClass = object


class LRUCache(_baseClass):
    def __init__(self, num):
        # type: (int)
        # TODO: fix type after dropping py36
        self.cache = OrderedDict()
        # type: Dict[TCacheKey, TCacheValue]
        self.num = num

    def get(self, key):
        # type: (TCacheKey) -> Optional[TCacheValue]
        if key not in self.cache:
            return None
        # noinspection PyUnresolvedReferences
        self.cache.move_to_end(key)
        return self.cache[key]

    def set(self, key, value):
        # type: (TCacheKey, TCacheValue) -> None
        self.cache[key] = value
        # noinspection PyUnresolvedReferences
        self.cache.move_to_end(key)
        if len(self.cache) > self.num:
            # noinspection PyArgumentList
            self.cache.popitem(last=False)
