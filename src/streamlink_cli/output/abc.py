from abc import ABCMeta, abstractmethod


class Output(metaclass=ABCMeta):
    def __init__(self):
        self.opened = False

    def open(self):
        self._open()
        self.opened = True

    def close(self):
        if self.opened:
            self._close()

        self.opened = False

    def write(self, data):
        if not self.opened:
            raise OSError("Output is not opened")

        return self._write(data)

    @abstractmethod
    def _open(self):
        raise NotImplementedError

    @abstractmethod
    def _close(self):
        raise NotImplementedError

    @abstractmethod
    def _write(self, data):
        raise NotImplementedError
