import queue
from concurrent.futures import ThreadPoolExecutor as _ThreadPoolExecutor
from sys import version_info


# noinspection PyTypeChecker
class ThreadPoolExecutor(_ThreadPoolExecutor):
    if version_info < (3, 9):
        def shutdown(self, wait=True, cancel_futures=False):  # pragma: no cover
            with self._shutdown_lock:
                self._shutdown = True
                if cancel_futures:
                    # Drain all work items from the queue, and then cancel their
                    # associated futures.
                    while True:
                        try:
                            work_item = self._work_queue.get_nowait()
                        except queue.Empty:
                            break
                        if work_item is not None:
                            work_item.future.cancel()

                # Send a wake-up to prevent threads calling
                # _work_queue.get(block=True) from permanently blocking.
                self._work_queue.put(None)
            if wait:
                for t in self._threads:
                    t.join()
