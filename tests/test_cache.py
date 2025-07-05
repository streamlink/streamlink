from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from io import BytesIO, TextIOWrapper
from json import JSONDecodeError
from pathlib import Path
from threading import Thread, Timer
from typing import Callable
from unittest.mock import Mock

import freezegun
import pytest

# noinspection PyProtectedMember
from streamlink.cache import WRITE_DEBOUNCE_TIME, Cache
from tests.testutils.handshake import Handshake


@pytest.fixture(autouse=True)
def caplog(caplog: pytest.LogCaptureFixture):
    caplog.set_level(1, "streamlink")
    return caplog


@pytest.fixture()
def mock_load(monkeypatch: pytest.MonkeyPatch):
    mock = Mock()
    monkeypatch.setattr("streamlink.cache.Cache._load", mock)
    return mock


@pytest.fixture()
def mock_schedule_save(monkeypatch: pytest.MonkeyPatch):
    mock = Mock()
    monkeypatch.setattr("streamlink.cache.Cache._schedule_save", mock)
    return mock


@pytest.fixture()
def mock_save(monkeypatch: pytest.MonkeyPatch):
    mock = Mock()
    monkeypatch.setattr("streamlink.cache.Cache._save", mock)
    return mock


@pytest.fixture()
def no_io(mock_load: Mock, mock_schedule_save: Mock, mock_save: Mock):
    return mock_load, mock_schedule_save, mock_save


@pytest.fixture(autouse=True)
def atexit(monkeypatch: pytest.MonkeyPatch):
    stack = []

    def register(func: Callable, *args, **kwargs) -> None:
        stack.append((func, args, kwargs))

    monkeypatch.setattr("streamlink.cache._atexit_register", register)

    return stack


@pytest.fixture(autouse=True)
def mock_json_load(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    side_effect: Callable | Exception = getattr(request, "param", None) or json.load
    mock = Mock(side_effect=side_effect)
    monkeypatch.setattr("json.load", mock)
    return mock


@pytest.fixture(autouse=True)
def cache_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr("streamlink.cache.CACHE_DIR", tmp_path)
    return tmp_path


# noinspection PyProtectedMember
@pytest.fixture()
def cache(request: pytest.FixtureRequest, cache_dir: Path, atexit: list):
    param = getattr(request, "param", {})
    param.setdefault("filename", "cache.json")

    cache = Cache(**param)
    assert cache.filename == cache_dir / param["filename"]
    assert cache._cache_orig == {}
    assert cache._cache == {}
    assert cache._cache_orig is not cache._cache
    assert not cache._loaded
    assert not cache._dirty
    assert not cache._timer
    assert atexit == [(cache._save, (), {})]

    yield cache

    assert cache._cache_orig is not cache._cache
    assert not cache._timer or not cache._timer.is_alive()


@pytest.mark.usefixtures("no_io")
@pytest.mark.parametrize(
    "filename",
    [
        pytest.param("foo", id="str"),
        pytest.param(Path("foo"), id="Path"),
    ],
)
def test_pathlib_and_str(cache_dir: Path, filename: str | Path):
    cache = Cache(filename)
    assert cache.filename == cache_dir / Path(filename)


@pytest.mark.usefixtures("no_io")
class TestGetterSetter:
    def test_get(self, cache: Cache, mock_schedule_save: Mock):
        assert not mock_schedule_save.called
        assert cache.get("missing-value") is None
        assert cache.get("missing-value", default="default") == "default"
        assert not cache._dirty
        assert mock_schedule_save.call_count == 2

    def test_set(self, cache: Cache):
        assert cache.get("value") is None
        cache.set("value", 1)
        assert cache.get("value") == 1
        assert list(cache._cache.keys()) == ["value"]
        assert cache._dirty

    def test_get_all(self, cache: Cache, mock_schedule_save: Mock):
        assert not mock_schedule_save.called
        cache.set("test1", 1)
        cache.set("test2", 2)
        assert cache.get_all() == {"test1": 1, "test2": 2}
        assert mock_schedule_save.call_count == 3

    def test_get_all_prune(self, cache: Cache):
        cache.set("test1", 1)
        cache.set("test2", 2, -1)
        assert cache.get_all() == {"test1": 1}


@pytest.mark.usefixtures("no_io")
def test_atomicity(monkeypatch: pytest.MonkeyPatch, cache: Cache):
    hs_contains = Handshake()  # block inner Cache.get()
    hs_items = Handshake()  # block inner Cache.get_all()
    hs_setitem = Handshake()  # block inner Cache.set()
    hs_getter = Handshake()
    hs_setter = Handshake()
    hs_getall = Handshake()
    result = None

    class BlockingDict(dict):
        def __contains__(self, key):
            with hs_contains():
                return super().__contains__(key)

        def items(self):
            with hs_items():
                return super().items()

        def __setitem__(self, *args, **kwargs):
            with hs_setitem():
                return super().__setitem__(*args, **kwargs)

    monkeypatch.setattr(cache, "_prune", Mock())
    monkeypatch.setattr(cache, "_cache", BlockingDict(foo={"value": "foo"}))

    def getter_thread():
        nonlocal result
        with hs_getter():
            result = cache.get("foo", "default")

    def setter_thread():
        with hs_setter():
            cache.set("foo", "bar")

    def getall_thread():
        nonlocal result
        with hs_getall():
            result = cache.get_all()

    t_getter = Thread(daemon=True, target=getter_thread)
    t_setter = Thread(daemon=True, target=setter_thread)
    t_getall = Thread(daemon=True, target=getall_thread)

    t_getter.start()
    assert hs_getter.wait_ready(timeout=1), "Getter thread is ready"
    assert not hs_contains.wait_ready(timeout=0), "Getter thread had not yet reached inner get()"

    t_setter.start()
    assert hs_setter.wait_ready(timeout=1), "Setter thread is ready"
    assert not hs_setitem.wait_ready(timeout=0), "Setter thread has not yet reached inner set()"

    # 1. `result = cache.get("foo")`
    hs_getter.go()  # Let getter thread make get() call
    assert hs_contains.wait_ready(timeout=1), "Getter thread has reached inner get()"

    # 2. `cache.set("foo", "bar")` while get() hasn't finished yet
    hs_setter.go()  # Let setter thread make set() call
    assert not hs_setitem.wait_ready(timeout=0.05), "Setter thread won't reach inner set()"

    assert result is None
    assert hs_contains.step(timeout=1), "Let __contains__() return"
    assert hs_getter.wait_done(timeout=1), "Wait for getter thread to finish"
    assert result == "foo"

    assert hs_setitem.wait_ready(timeout=1), "Setter thread has reached inner set() after get() completed"

    t_getall.start()
    assert hs_getall.wait_ready(timeout=1), "Getall thread is ready"
    assert not hs_items.wait_ready(timeout=0), "Getall thread had not yet reached inner get_all()"

    # 3. `result = cache.get_all()` while set() hasn't finished yet
    hs_getall.go()  # Let getall thread make get_all() call
    assert not hs_items.wait_ready(timeout=0.05), "Getall thread won't reach inner get_all()"

    assert hs_setitem.step(timeout=1), "Let __setitem__() return"

    assert hs_items.wait_ready(timeout=1), "Getall thread has reached inner get_all()"
    assert hs_items.step(timeout=1), "Let items() return"
    assert hs_getall.wait_done(timeout=1), "Wait for getall thread to finish"
    assert result == {"foo": "bar"}


@pytest.mark.usefixtures("no_io")
class TestPrefix:
    @pytest.mark.parametrize("cache", [{"key_prefix": "test"}], indirect=["cache"])
    def test_key_prefix(self, cache: Cache):
        cache.set("key", 1)
        assert cache.get("key") == 1
        assert "test:key" in cache._cache
        assert cache._cache["test:key"]["value"] == 1

    def test_get_all_prefix(self, cache: Cache):
        cache.set("test1", 1)
        cache.set("test2", 2)
        cache.key_prefix = "test"
        cache.set("test3", 3)
        cache.set("test4", 4)
        assert cache.get_all() == {"test3": 3, "test4": 4}


@pytest.mark.usefixtures("no_io")
class TestExpiration:
    @pytest.mark.parametrize(
        ("expires", "expected"),
        [
            pytest.param(-20, None, id="past"),
            pytest.param(20, "value", id="future"),
        ],
    )
    def test_expires(self, cache: Cache, expires: float, expected):
        with freezegun.freeze_time("2000-01-01T00:00:00Z"):
            cache.set("key", "value", expires=expires)
            assert cache.get("key") == expected

    @pytest.mark.parametrize(
        ("delta", "expected"),
        [
            pytest.param(timedelta(seconds=-20), None, id="past"),
            pytest.param(timedelta(seconds=20), "value", id="future"),
        ],
    )
    def test_expires_at(self, cache: Cache, delta: timedelta, expected):
        with freezegun.freeze_time("2000-01-01T00:00:00Z"):
            cache.set("key", "value", expires_at=datetime.now(tz=timezone.utc) + delta)
            assert cache.get("key") == expected

    def test_expires_at_overflowerror(self, cache: Cache):
        expires_at = Mock(timestamp=Mock(side_effect=OverflowError))
        cache.set("key", "value", expires_at=expires_at)
        assert cache.get("key") is None

    def test_expiration(self, cache: Cache):
        with freezegun.freeze_time("2000-01-01T00:00:00Z") as frozen_time:
            cache.set("key", "value", expires=20)
            assert cache.get("key") == "value"
            frozen_time.tick(timedelta(seconds=20))
            assert cache.get("key") is None


class TestScheduleSave:
    def test_not_dirty(self, caplog: pytest.LogCaptureFixture, cache: Cache, mock_save: Mock):
        assert not cache._dirty
        cache._schedule_save()
        assert not cache._timer
        assert mock_save.call_count == 0
        assert caplog.records == []

    def test_cancel_timer(self, caplog: pytest.LogCaptureFixture, cache: Cache, mock_save: Mock):
        assert not cache._dirty
        cache._timer = Timer(WRITE_DEBOUNCE_TIME, mock_save)
        cache._timer.daemon = True
        cache._timer.start()
        assert cache._timer.is_alive()
        cache._schedule_save()
        cache._timer.join(timeout=1)
        assert not cache._timer.is_alive()
        assert mock_save.call_count == 0
        assert caplog.records == []

    def test_schedule_save(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        cache: Cache,
        mock_save: Mock,
    ):
        cache._cache = {"key": {"value": "foo"}}
        assert cache._dirty
        assert not cache._timer

        cache._schedule_save()
        assert mock_save.call_count == 0
        assert cache._timer
        assert cache._timer.is_alive()

        # Let the timer "expire" by monkeypatching the is_set() method and then setting the inner threading.Event flag.
        # This depends on the implementation details of threading.Timer.
        monkeypatch.setattr(cache._timer.finished, "is_set", lambda: False)
        cache._timer.finished.set()  # same as cancel(), but is_set() will return False, so the callback will be executed
        cache._timer.join(timeout=1)
        assert not cache._timer.is_alive()
        assert mock_save.call_count == 1

        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            ("streamlink.cache", "trace", "Scheduling write to cache file: 3.0s"),
        ]


class TestIO:
    @pytest.fixture()
    def mock_cache_file(self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
        content: bytes | Exception = getattr(request, "param", None) or b"{}"
        if not isinstance(content, bytes):
            mock = Mock(side_effect=content)
        else:
            stream = TextIOWrapper(BytesIO(content), encoding="utf-8")
            mock = Mock(return_value=stream)
        monkeypatch.setattr("pathlib.Path.open", mock)

        return mock

    @pytest.mark.parametrize(
        ("mock_cache_file", "mock_json_load", "log"),
        [
            pytest.param(
                FileNotFoundError("File not found"),
                None,
                [],
                id="file-not-found-error",
            ),
            pytest.param(
                PermissionError("Permission denied"),
                None,
                [
                    (
                        "streamlink.cache",
                        "warning",
                        "Failed loading cache file, continuing without cache: Permission denied",
                    ),
                ],
                id="os-error",
            ),
            pytest.param(
                None,
                JSONDecodeError("cache-file.json", "", 0),
                [
                    (
                        "streamlink.cache",
                        "warning",
                        "Failed loading cache file, continuing without cache: cache-file.json: line 1 column 1 (char 0)",
                    ),
                ],
                id="json-decode-error",
            ),
        ],
        indirect=["mock_cache_file", "mock_json_load"],
    )
    def test_load(self, caplog: pytest.LogCaptureFixture, cache: Cache, mock_cache_file: Mock, mock_json_load: Mock, log: list):
        cache._load()
        assert cache._loaded, "Failed load attempts also set the loaded state to True"
        assert not cache._dirty
        assert cache._cache == {}
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            ("streamlink.cache", "trace", f"Loading cache file: {cache.filename}"),
            *log,
        ]
        assert mock_cache_file.call_count == 1

        cache._load()
        assert mock_cache_file.call_count == 1

    @pytest.mark.usefixtures("mock_schedule_save", "mock_save")
    @pytest.mark.parametrize(
        ("mock_cache_file", "expected", "dirty"),
        [
            pytest.param(
                b"""{"foo": {"value": "\\ud83d\\udc3b", "expires": 946684801}}""",
                "🐻",
                False,
                id="load-no-expiration",
            ),
            pytest.param(
                b"""{"foo": {"value": "\\ud83d\\udc3b", "expires": 946684800}}""",
                None,
                True,
                id="load-with-expiration",
            ),
        ],
        indirect=["mock_cache_file"],
    )
    def test_load_data(self, mock_cache_file: Mock, expected: str | None, dirty: bool):
        with freezegun.freeze_time("2000-01-01T00:00:00Z"):
            cache = Cache("mocked-io")
            assert not cache._loaded
            assert not cache._dirty
            assert cache.get("foo") == expected
            assert cache._loaded
            assert cache._dirty is dirty

    @pytest.mark.parametrize(
        ("patch", "side_effect"),
        [
            pytest.param(
                "pathlib.Path.mkdir",
                PermissionError("Permission denied"),
                id="pathlib-path-mkdir",
            ),
            pytest.param(
                "tempfile.NamedTemporaryFile",
                PermissionError("Permission denied"),
                id="tempfile-namedtemporaryfile",
            ),
            pytest.param(
                "json.dump",
                ValueError(),
                id="json-dump",
            ),
            pytest.param(
                "shutil.move",
                PermissionError("Permission denied"),
                id="shutil-move",
            ),
        ],
    )
    def test_save_fail(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        cache: Cache,
        patch: str,
        side_effect: Exception,
    ):
        mock = Mock(side_effect=side_effect)
        monkeypatch.setattr(patch, mock)

        cache._cache_orig = {"foo": {"value": 1}}
        cache._cache = {"foo": {"value": 2}}
        assert cache._dirty

        cache._save()
        assert mock.call_count == 1
        assert cache._dirty
        assert cache._cache_orig == {"foo": {"value": 1}}
        assert cache._cache == {"foo": {"value": 2}}
        assert not cache.filename.exists()
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            ("streamlink.cache", "trace", f"Writing to cache file: {cache.filename}"),
            ("streamlink.cache", "error", f"Error while writing to cache file: {side_effect}"),
        ]

    @pytest.mark.parametrize("cache", [pytest.param({"filename": Path("foo") / "bar" / "cache.json"})], indirect=True)
    def test_save_success(self, caplog: pytest.LogCaptureFixture, cache: Cache):
        cache._loaded = True
        cache._cache_orig = {"foo": {"value": "bear", "expires": 946684801}}
        cache._cache = {"foo": {"value": "🐻", "expires": 946684801}}
        assert cache._dirty

        cache._save()
        assert not cache._dirty
        assert cache._cache_orig == {"foo": {"value": "🐻", "expires": 946684801}}
        assert cache._cache == cache._cache_orig
        assert cache._cache["foo"] is not cache._cache_orig["foo"]
        assert cache.filename.exists()
        assert (
            cache.filename.read_text(encoding="utf-8")
            == """{\n  "foo": {\n    "value": "\\ud83d\\udc3b",\n    "expires": 946684801\n  }\n}"""
        )
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            ("streamlink.cache", "trace", f"Writing to cache file: {cache.filename}"),
        ]
        with freezegun.freeze_time("2000-01-01T00:00:00Z"):
            assert cache.get("foo") == "🐻"

    def test_save_not_dirty(self, caplog: pytest.LogCaptureFixture, cache: Cache):
        assert not cache._dirty
        cache._save()
        assert not cache.filename.exists()
        assert caplog.records == []

    def test_save_cancel_timer(self, cache: Cache):
        callback = Mock()
        cache._timer = Timer(10, callback)
        cache._timer.daemon = True
        cache._timer.start()
        assert cache._timer.is_alive()
        cache._save()
        cache._timer.join(timeout=1)
        assert not cache._timer.is_alive()
        assert callback.call_count == 0
        assert not cache.filename.exists()

    @pytest.mark.parametrize(
        "mock_cache_file",
        [
            pytest.param(
                b"""{"foo": {"value": "foo", "expires": 946684801}}""",
                id="disabled",
            ),
        ],
        indirect=True,
    )
    def test_disabled(self, caplog: pytest.LogCaptureFixture, mock_cache_file: Mock):
        with freezegun.freeze_time("2000-01-01T00:00:00Z"):
            cache = Cache("mocked-io", disabled=True)
            assert cache._disabled
            assert cache._loaded
            assert cache._cache == {}
            assert cache._cache_orig == {}
            assert mock_cache_file.call_args_list == []

            assert cache.get("foo") is None
            assert not cache._dirty

            cache.set("foo", "bar")
            assert cache._dirty
            assert cache._timer is None

            assert cache.get("foo") == "bar"

            cache._save()
            assert not cache.filename.exists()

        assert [(record.name, record.levelname, record.message) for record in caplog.records] == []
