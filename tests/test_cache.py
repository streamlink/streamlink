from datetime import datetime, timedelta, timezone
from json import JSONDecodeError
from pathlib import Path
from typing import Type, Union
from unittest.mock import Mock, patch

import freezegun
import pytest

from streamlink.cache import Cache


@pytest.fixture(autouse=True)
def cache_dir(tmp_path: Path):
    with patch("streamlink.cache.CACHE_DIR", tmp_path):
        yield tmp_path


@pytest.fixture()
def cache(request: pytest.FixtureRequest, cache_dir: Path):
    param = getattr(request, "param", {})
    filename = param.get("filename", "cache.json")
    key_prefix = param.get("key_prefix", None)

    cache = Cache(filename, key_prefix=key_prefix)
    assert cache.filename == cache_dir / filename
    # noinspection PyProtectedMember
    assert not cache._cache

    return cache


class TestPathlibAndStr:
    @pytest.mark.parametrize("filename", [
        pytest.param("foo", id="str"),
        pytest.param(Path("foo"), id="Path"),
    ])
    def test_constructor(self, cache_dir: Path, filename: Union[str, Path]):
        cache = Cache(filename)
        assert cache.filename == cache_dir / Path(filename)


class TestGetterSetter:
    def test_get(self, cache: Cache):
        assert cache.get("missing-value") is None
        assert cache.get("missing-value", default="default") == "default"

    def test_set(self, cache: Cache):
        assert cache.get("value") is None
        cache.set("value", 1)
        assert cache.get("value") == 1
        assert cache._cache

    def test_get_all(self, cache: Cache):
        cache.set("test1", 1)
        cache.set("test2", 2)
        assert cache.get_all() == {"test1": 1, "test2": 2}

    def test_get_all_prune(self, cache: Cache):
        cache.set("test1", 1)
        cache.set("test2", 2, -1)
        assert cache.get_all() == {"test1": 1}


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


class TestExpiration:
    @pytest.mark.parametrize(("expires", "expected"), [
        pytest.param(-20, None, id="past"),
        pytest.param(20, "value", id="future"),
    ])
    def test_expires(self, cache: Cache, expires: float, expected):
        with freezegun.freeze_time("2000-01-01T00:00:00Z"):
            cache.set("key", "value", expires=expires)
            assert cache.get("key") == expected

    @pytest.mark.parametrize(("delta", "expected"), [
        pytest.param(timedelta(seconds=-20), None, id="past"),
        pytest.param(timedelta(seconds=20), "value", id="future"),
    ])
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


class TestIO:
    @pytest.mark.parametrize(("mockpath", "side_effect"), [
        ("pathlib.Path.open", OSError),
        ("json.load", JSONDecodeError),
    ])
    def test_load_fail(self, cache: Cache, mockpath: str, side_effect: Type[Exception]):
        with patch("pathlib.Path.exists", return_value=True):
            with patch(mockpath, side_effect=side_effect):
                cache._load()
        assert not cache._cache

    @pytest.mark.parametrize("side_effect", [
        RecursionError,
        TypeError,
        ValueError,
    ])
    def test_save_fail_jsondump(self, cache: Cache, side_effect: Type[Exception]):
        with patch("json.dump", side_effect=side_effect):
            with pytest.raises(side_effect):
                cache.set("key", "value")
        assert not cache.filename.exists()


class TestCreateDirectory:
    filepath = Path("dir1", "dir2", "cache.json")

    def test_success(self, cache_dir: Path):
        expected = cache_dir / self.filepath
        cache = Cache(self.filepath)
        assert not expected.exists()
        cache.set("key", "value")
        assert expected.exists()

    def test_failure(self, cache_dir: Path):
        with patch("pathlib.Path.mkdir", side_effect=OSError):
            expected = cache_dir / self.filepath
            cache = Cache(self.filepath)
            assert not expected.exists()
            cache.set("key", "value")
            assert not expected.exists()
            assert not list(cache_dir.iterdir())
