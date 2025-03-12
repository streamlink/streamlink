from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from io import BufferedRandom, BufferedWriter
from pathlib import Path

import pytest

from streamlink_cli.output import FileOutput


@contextmanager
def _create_fd(root: Path, name: str) -> Iterator[BufferedRandom]:
    fd = (root / name).open("w+b")
    try:
        yield fd
    finally:
        fd.close()


@pytest.fixture()
def fd(tmp_path: Path):
    with _create_fd(tmp_path, "file") as fd:
        yield fd


@pytest.fixture(autouse=True)
def fake_stdout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    # can't use in-memory io.BytesIO, since fd.fileno() is called on Windows
    with _create_fd(tmp_path, "stdout") as fd:
        monkeypatch.setattr("streamlink_cli.output.file.stdout", fd)
        yield fd


def test_early_close(tmp_path: Path, fd: BufferedRandom):
    filename = tmp_path / "foo" / "bar"
    fo = FileOutput(filename=filename, record=FileOutput(fd=fd))
    assert isinstance(fo.record, FileOutput)
    assert not fo.opened
    assert not fo.record.opened
    assert not filename.exists()

    fo.close()
    fo.record.close()


def test_early_write(tmp_path: Path):
    filename = tmp_path / "foo" / "bar"
    fo = FileOutput(filename=filename)

    assert not fo.opened
    assert not filename.exists()
    with pytest.raises(OSError, match=r"^Output is not opened$"):
        fo.write(b"foo")


def test_open_write_close(tmp_path: Path, fd: BufferedRandom):
    filename = tmp_path / "foo" / "bar"
    fo = FileOutput(filename=filename, record=FileOutput(fd=fd))
    assert fo.fd is None
    assert isinstance(fo.record, FileOutput)

    fo.open()
    assert fo.opened
    assert fo.record.opened
    assert filename.parent.is_dir()
    assert filename.is_file()
    assert isinstance(fo.fd, BufferedWriter)
    assert isinstance(fo.record.fd, BufferedRandom)

    fo.write(b"foo")
    fo.write(b"bar")
    fo.write(b"baz")
    fo.fd.flush()
    fo.record.fd.flush()
    assert filename.read_bytes() == b"foobarbaz"
    fo.record.fd.seek(0)
    assert fo.record.fd.read() == b"foobarbaz"

    fo.close()
    assert not fo.opened
    assert not fo.record.opened
    assert fo.fd.closed
    assert fo.record.fd.closed


def test_write_stdout(fake_stdout: BufferedRandom):
    fo = FileOutput(fd=fake_stdout)
    assert fo.fd is fake_stdout
    assert fo.filename is None
    assert fo.record is None

    fo.open()
    assert fo.opened

    fo.write(b"foo")
    fo.write(b"bar")
    fo.write(b"baz")
    fo.fd.seek(0)
    assert fo.fd.read() == b"foobarbaz"

    fo.close()
    assert not fo.opened
    assert not fo.fd.closed
