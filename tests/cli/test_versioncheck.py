from unittest.mock import Mock, call

import pytest
import requests_mock as rm

from streamlink_cli.utils.versioncheck import check_version, get_latest, log


@pytest.fixture(autouse=True)
def _logger(caplog: pytest.LogCaptureFixture):
    caplog.set_level(1, "streamlink.cli")


def test_logger_name():
    assert log.name == "streamlink.cli"


class TestGetLatest:
    @pytest.fixture
    def pypi(self, request, requests_mock: rm.Mocker):
        invalid = requests_mock.register_uri(rm.ANY, rm.ANY, exc=rm.exceptions.InvalidRequest("Invalid request"))
        response = requests_mock.register_uri("GET", "https://pypi.python.org/pypi/streamlink/json", **(request.param or {}))
        yield response
        assert not invalid.called  # type: ignore[attr-defined]
        assert response.called_once  # type: ignore[attr-defined]

    @pytest.mark.parametrize("pypi,error", [
        (
            {"status_code": 500},
            "Error while retrieving version data from PyPI API: "
            + "500 Server Error: None for url: https://pypi.python.org/pypi/streamlink/json",
        ),
        (
            {"text": "no JSON"},
            "Could not parse JSON data from PyPI API response",
        ),
        (
            {"json": {"foo": "bar"}},
            "Error while retrieving version data from PyPI API: 'NoneType' object has no attribute 'get'",
        ),
    ], indirect=["pypi"])
    def test_request_error(self, caplog: pytest.LogCaptureFixture, pypi, error):
        assert not get_latest()
        assert [(record.levelname, str(record.message)) for record in caplog.records] == [("error", error)]

    @pytest.mark.parametrize("pypi", [{"json": {"info": {"version": "1.2.3"}}}], indirect=True)
    def test_request_success(self, caplog: pytest.LogCaptureFixture, pypi):
        assert get_latest() == "1.2.3"
        assert not caplog.records


class TestVersionCheck:
    @pytest.fixture(autouse=True)
    def current(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("streamlink_cli.utils.versioncheck.streamlink_version", "1.0.0")

    @pytest.fixture
    def latest(self, request, monkeypatch: pytest.MonkeyPatch):
        mock_get_latest = Mock(return_value=getattr(request, "param", "1.2.3"))
        monkeypatch.setattr("streamlink_cli.utils.versioncheck.get_latest", mock_get_latest)
        yield mock_get_latest

    @pytest.fixture
    def cache(self, request, monkeypatch: pytest.MonkeyPatch):
        Cache = Mock()
        cache = Cache("cli.json")
        cache.get.side_effect = request.param.get
        monkeypatch.setattr("streamlink_cli.utils.versioncheck.Cache", Cache)
        yield cache
        assert cache.called_once

    @pytest.mark.parametrize("cache", [{}], indirect=True)
    def test_auto_uncached_outdated(self, caplog: pytest.LogCaptureFixture, cache: Mock, latest: Mock):
        assert not check_version()
        assert latest.call_args_list == [call()]
        assert cache.set.call_args_list == [
            call("latest_version", "1.2.3", 86400),
            call("version_info_printed", True, 21600),
        ]
        assert [(record.levelname, str(record.message)) for record in caplog.records] == [
            ("info", "A new version of Streamlink (1.2.3) is available!"),
        ]

    @pytest.mark.parametrize("cache,latest", [({}, "1.0.0")], indirect=True)
    def test_auto_uncached_uptodate(self, caplog: pytest.LogCaptureFixture, cache: Mock, latest: Mock):
        assert check_version()
        assert latest.call_args_list == [call()]
        assert cache.set.call_args_list == [
            call("latest_version", "1.0.0", 86400),
        ]
        assert not caplog.records

    @pytest.mark.parametrize("cache", [{"latest_version": "1.2.3", "version_info_printed": False}], indirect=True)
    def test_auto_cached_outdated(self, caplog: pytest.LogCaptureFixture, cache: Mock, latest: Mock):
        assert not check_version()
        assert not latest.call_args_list
        assert cache.set.call_args_list == [call("version_info_printed", True, 21600)]
        assert [(record.levelname, str(record.message)) for record in caplog.records] == [
            ("info", "A new version of Streamlink (1.2.3) is available!"),
        ]

    @pytest.mark.parametrize("cache", [{"latest_version": "1.2.3", "version_info_printed": True}], indirect=True)
    def test_auto_cached_printed(self, caplog: pytest.LogCaptureFixture, cache: Mock, latest: Mock):
        assert check_version()
        assert not latest.call_args_list
        assert not cache.set.call_args_list
        assert not caplog.records

    @pytest.mark.parametrize("cache", [
        {},
        {"version_info_printed": True},
    ], indirect=True)
    def test_forced_outdated(self, caplog: pytest.LogCaptureFixture, cache: Mock, latest: Mock):
        assert not check_version(True)
        assert latest.call_args_list == [call()]
        assert cache.set.call_args_list == [
            call("latest_version", "1.2.3", 86400),
            call("version_info_printed", True, 21600),
        ]
        assert [(record.levelname, str(record.message)) for record in caplog.records] == [
            ("info", "A new version of Streamlink (1.2.3) is available!"),
        ]

    @pytest.mark.parametrize("cache,latest", [
        ({}, "1.0.0"),
        ({"version_info_printed": True}, "1.0.0"),
    ], indirect=True)
    def test_forced_uptodate(self, caplog: pytest.LogCaptureFixture, cache: Mock, latest: Mock):
        assert check_version(True)
        assert latest.call_args_list == [call()]
        assert cache.set.call_args_list == [
            call("latest_version", "1.0.0", 86400),
        ]
        assert [(record.levelname, str(record.message)) for record in caplog.records] == [
            ("info", "Your Streamlink version (1.0.0) is up to date!"),
        ]

    @pytest.mark.parametrize("cache,latest", [({}, "")], indirect=True)
    def test_error_get_latest(self, caplog: pytest.LogCaptureFixture, cache: Mock, latest: Mock):
        assert not check_version(True)
        assert latest.call_args_list == [call()]
        assert not cache.set.call_args_list
        assert not caplog.records  # error gets logged by get_latest()

    @pytest.mark.parametrize("cache,latest", [({}, "not a semver version string")], indirect=True)
    def test_error_get_latest_version(self, caplog: pytest.LogCaptureFixture, cache: Mock, latest: Mock):
        assert not check_version(True)
        assert latest.call_args_list == [call()]
        assert not cache.set.call_args_list
        assert [(record.levelname, str(record.message)) for record in caplog.records] == [
            ("error", f"Error while parsing version: Invalid version string: '{latest.return_value}'"),
        ]
