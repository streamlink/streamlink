from __future__ import annotations

from threading import Event, Thread
from typing import TYPE_CHECKING

from streamlink.utils.thread import NamedThread, wait_for_all_events
from tests.testutils.handshake import Handshake


if TYPE_CHECKING:
    import pytest


def test_named_thread():
    class One(NamedThread):
        pass

    class Two(NamedThread):
        pass

    assert One().name == "One-0"
    assert One().name == "One-1"
    assert Two().name == "Two-0"
    assert Two().name == "Two-1"

    assert One(name="foo").name == "One-foo-0"
    assert One(name="foo").name == "One-foo-1"
    assert One(name="bar").name == "One-bar-0"
    assert One(name="bar").name == "One-bar-1"
    assert One().name == "One-2"


class TestWaitForAllEvents:
    def test_success(self) -> None:
        handshake = Handshake()
        result: bool | None = None
        events = [Event() for _ in range(3)]

        def producer():
            nonlocal result
            with handshake():
                result = wait_for_all_events(*events, timeout=4)

        thread = Thread(target=producer, daemon=True)
        thread.start()

        assert handshake.wait_ready(timeout=1)
        assert result is None
        assert [event.is_set() for event in events] == [False, False, False]

        handshake.go()
        for event in events[:-1]:
            event.set()
            assert not handshake.wait_done(timeout=0)
            assert result is None

        assert [event.is_set() for event in events] == [True, True, False]

        events[-1].set()
        assert handshake.wait_done(timeout=1)
        assert result is True
        assert [event.is_set() for event in events] == [True, True, True]

        thread.join(timeout=1)
        assert not thread.is_alive()

    def test_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        handshake = Handshake()
        result: bool | None = None
        event = Event()
        # simulate an immediate timeout
        monkeypatch.setattr(event, "wait", lambda *_: False)

        def producer():
            nonlocal result
            with handshake():
                result = wait_for_all_events(event, timeout=4)

        thread = Thread(target=producer, daemon=True)
        thread.start()

        assert handshake.wait_ready(timeout=1)
        assert result is None
        assert not event.is_set()

        handshake.step(timeout=1)
        assert result is False

        thread.join(timeout=1)
        assert not thread.is_alive()
