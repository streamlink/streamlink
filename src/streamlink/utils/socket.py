from __future__ import annotations

from collections.abc import Callable, Coroutine

import trio


def _factory_find_free_port(name: str, address_family: int) -> Callable[[str], Coroutine[None, None, int]]:
    async def find_free_port(host: str) -> int:  # pragma: no cover
        *_, (*_gai, address) = await trio.socket.getaddrinfo(host, None, address_family, trio.socket.SOCK_STREAM)
        with trio.socket.socket(address_family, trio.socket.SOCK_STREAM) as s:
            await s.bind(address)
            s.listen()
            return s.getsockname()[1]

    find_free_port.__name__ = name

    return find_free_port


find_free_port_ipv4 = _factory_find_free_port("find_free_port_ipv4", trio.socket.AF_INET)
find_free_port_ipv6 = _factory_find_free_port("find_free_port_ipv6", trio.socket.AF_INET6)


del _factory_find_free_port
