from collections import OrderedDict
from typing import Generic, Optional, OrderedDict as TOrderedDict, TypeVar


TCacheKey = TypeVar("TCacheKey")
TCacheValue = TypeVar("TCacheValue")


class LRUCache(Generic[TCacheKey, TCacheValue]):
    def __init__(self, num: int):
        self.cache: TOrderedDict[TCacheKey, TCacheValue] = OrderedDict()
        self.num = num

    def get(self, key: TCacheKey) -> Optional[TCacheValue]:
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def set(self, key: TCacheKey, value: TCacheValue) -> None:
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.num:
            self.cache.popitem(last=False)
