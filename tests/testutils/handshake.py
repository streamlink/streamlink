from asyncio import Future, get_event_loop
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from threading import Event
from typing import Awaitable, Callable, Generator, Optional, Type


@dataclass
class _HandshakeContext:
    error: Optional[Exception] = None


class Handshake:
    """
    Control execution flow between one producer thread (application logic) and one consumer thread (tests),
    to be able to assert application state at certain points during execution.
    """

    def __init__(self) -> None:
        self._ready = Event()
        self._go = Event()
        self._done = Event()
        self._context = _HandshakeContext()

    @contextmanager
    def __call__(self, exception: Optional[Type[Exception]] = None) -> Generator[_HandshakeContext, None, None]:
        """Execute application logic in this context manager and optionally capture exceptions."""
        try:
            self.ready()
            yield self._context
        except BaseException as err:
            if exception is not None and isinstance(err, exception):
                self._context.error = err
            else:
                raise
        finally:
            self.done()

    def ready(self) -> None:
        """Make producer thread wait indefinitely until consumer thread allows one execution step."""
        self._ready.set()
        self._go.wait()
        self._go.clear()
        self._context.error = None

    def done(self):
        """Tell the cosumer thread that execution has finished."""
        self._ready.clear()
        self._done.set()

    def go(self):
        """Allow producer thread to run."""
        self._go.set()

    def wait_ready(self, timeout: Optional[float] = None) -> bool:
        """Wait for producer thread to be ready and return whether it is ready or not."""
        return self._ready.wait(timeout=timeout)

    def wait_done(self, timeout: Optional[float] = None) -> bool:
        """Wait for producer thread to be done and return whether it is done or not. If an exception was captured, raise it."""
        result = self._done.wait(timeout=timeout)
        self._done.clear()

        error = self._context.error
        if error is not None:
            self._context.error = None
            raise error

        return result

    def step(self, timeout: Optional[float] = None) -> bool:
        """Allow producer thread to run, wait for it to complete and return whether it has finished or not."""
        self.go()
        return self.wait_done(timeout=timeout)

    is_ready: Callable[[Optional[float]], Awaitable[bool]]
    is_done: Callable[[Optional[float]], Awaitable[bool]]
    asyncstep: Callable[[Optional[float]], Awaitable[bool]]


def _sync2async(obj, name, method):
    meth = getattr(obj, method)

    @wraps(meth)
    async def wrapper(*args, **kwargs):
        async def task():
            try:
                value = meth(*args, **kwargs)
            except Exception as err:
                future.set_exception(err)
            else:
                future.set_result(value)

        future = Future()
        get_event_loop().create_task(task())

        return await future

    setattr(obj, name, wrapper)


_sync2async(Handshake, "is_ready", "wait_ready")
_sync2async(Handshake, "is_done", "wait_done")
_sync2async(Handshake, "asyncstep", "step")

del _sync2async
