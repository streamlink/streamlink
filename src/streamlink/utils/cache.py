from collections import OrderedDict
from typing import Dict, Generic, Optional, TypeVar


TCacheKey = TypeVar("TCacheKey")
TCacheValue = TypeVar("TCacheValue")


class LRUCache(Generic[TCacheKey, TCacheValue]):
    def __init__(self, num: int):
        # TODO: fix type after dropping py36
        self.cache: Dict[TCacheKey, TCacheValue] = OrderedDict()
        self.num = num

    def get(self, key: TCacheKey) -> Optional[TCacheValue]:
        if key not in self.cache:
            return None
        # noinspection PyUnresolvedReferences
        self.cache.move_to_end(key)
        return self.cache[key]

    def set(self, key: TCacheKey, value: TCacheValue) -> None:
        self.cache[key] = value
        # noinspection PyUnresolvedReferences
        self.cache.move_to_end(key)
        if len(self.cache) > self.num:
            # noinspection PyArgumentList
            self.cache.popitem(last=False)
