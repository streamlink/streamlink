from threading import Lock, Thread
from unittest.mock import patch

import pytest

from tests.testutils.handshake import Handshake


class Producer(Thread):
    def __init__(self, exception=None):
        super().__init__(daemon=True, name="ProducerThread")
        self.handshake = Handshake()
        self.lock = Lock()
        self.value = 0
        self.exception = exception
        self.error = None

    def run(self):
        try:
            for _ in range(2):
                with self.handshake(self.exception):
                    with self.lock:
                        self.action()
        except Exception as err:
            self.error = err

    def action(self):
        self.value += 1


@pytest.fixture()
def producer(request):
    thread = Producer(**getattr(request, "param", {}))
    yield thread
    thread.join(1)
    assert not thread.is_alive()


class TestSynchronization:
    def test_sync(self, producer: Producer):
        assert not producer.handshake.wait_ready(0), "Producer is not yet ready"
        assert not producer.handshake.wait_done(0), "Producer is not done"

        producer.start()
        assert producer.handshake.wait_ready(1), "Producer arrived in ready-state within at most 1 second"
        assert not producer.handshake.wait_done(0), "Producer is not in done-state"
        assert producer.value == 0

        assert producer.handshake.step(1), "Producer manages to execute one iteration within at most 1 second"
        assert not producer.handshake.wait_done(0), "Producer is not in done-state after completing one iteration"
        assert producer.value == 1
        assert producer.handshake.wait_ready(1), "Producer once again arrived in ready-state within at most 1 second"

        # make producer and consumer threads increment the value independently
        producer.handshake.go()
        with producer.lock:
            producer.value += 1
        assert producer.handshake.wait_done(1), "Producer is done after at most 1 second"
        assert producer.value == 3

        assert not producer.handshake.wait_done(0), "Producer is not in done-state anymore"
        assert not producer.handshake.wait_ready(0), "Producer's loop ended, not waiting in ready-state again"

    @pytest.mark.trio()
    async def test_async(self, producer: Producer):
        assert not await producer.handshake.is_ready(0), "Producer is not yet ready"
        assert not await producer.handshake.is_done(0), "Producer is not done"

        producer.start()
        assert await producer.handshake.is_ready(1), "Producer arrived in ready-state within at most 1 second"
        assert not await producer.handshake.is_done(0), "Producer is not in done-state"
        assert producer.value == 0

        assert await producer.handshake.asyncstep(1), "Producer manages to execute one iteration within at most 1 second"
        assert not await producer.handshake.is_done(0), "Producer is not in done-state after completing one iteration"
        assert producer.value == 1
        assert await producer.handshake.is_ready(1), "Producer once again arrived in ready-state within at most 1 second"

        # make producer and consumer threads increment the value independently
        producer.handshake.go()
        is_done = producer.handshake.is_done(1)
        with producer.lock:
            producer.value += 1
        assert await is_done, "Producer is done after at most 1 second"
        assert producer.value == 3

        assert not await producer.handshake.is_done(0), "Producer is not in done-state anymore"
        assert not await producer.handshake.is_ready(0), "Producer's loop ended, not waiting in ready-state again"


class TestNoCaptureExceptions:
    def test_sync(self, producer: Producer):
        producer.start()

        # doesn't catch exception and doesn't raise in consumer thread
        with patch.object(producer, "action", side_effect=Exception):
            assert producer.handshake.step(1), "Doesn't catch any exceptions, doesn't raise in consumer thread"
        producer.join(1)
        assert not producer.is_alive(), "Producer thread has raised exception and has terminated"
        assert isinstance(producer.error, Exception)

    @pytest.mark.trio()
    async def test_async(self, producer: Producer):
        producer.start()

        # doesn't catch exception and doesn't raise in consumer thread
        with patch.object(producer, "action", side_effect=Exception):
            assert await producer.handshake.asyncstep(1), "Doesn't catch any exceptions, doesn't raise in consumer thread"
        producer.join(1)
        assert not producer.is_alive(), "Producer thread has raised exception and has terminated"
        assert isinstance(producer.error, Exception)


class TestCaptureExceptions:
    @pytest.mark.parametrize("producer", [{"exception": TypeError}], indirect=True)
    def test_sync(self, producer: Producer):
        producer.start()

        # catches exception and raises in consumer thread
        with patch.object(producer, "action", side_effect=TypeError):
            with pytest.raises(TypeError):
                producer.handshake.step(1)

        assert not producer.handshake.wait_done(0), "Producer is not in done-state anymore after catching an exception"
        assert producer.handshake.wait_ready(1), "Producer once again arrived in ready-state within at most 1 second"

        with patch.object(producer, "action", side_effect=ValueError):
            assert producer.handshake.step(1), "Doesn't catch different exceptions, doesn't raise in consumer thread"
        producer.join(1)
        assert not producer.is_alive(), "Producer thread has raised exception and has terminated"
        assert isinstance(producer.error, ValueError)

    @pytest.mark.trio()
    @pytest.mark.parametrize("producer", [{"exception": TypeError}], indirect=True)
    async def test_async(self, producer: Producer):
        producer.start()

        # catches exception and raises in consumer thread
        with patch.object(producer, "action", side_effect=TypeError):
            with pytest.raises(TypeError):
                await producer.handshake.asyncstep(1)

        assert not await producer.handshake.is_done(0), "Producer is not in done-state anymore after catching an exception"
        assert await producer.handshake.is_ready(1), "Producer once again arrived in ready-state within at most 1 second"

        with patch.object(producer, "action", side_effect=ValueError):
            assert await producer.handshake.asyncstep(1), "Doesn't catch different exceptions, doesn't raise in consumer thread"
        producer.join(1)
        assert not producer.is_alive(), "Producer thread has raised exception and has terminated"
        assert isinstance(producer.error, ValueError)
