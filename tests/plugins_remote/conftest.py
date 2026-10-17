import pytest

from tests.plugins_remote import PluginTest


@pytest.fixture(autouse=True)
def caplog(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level("debug", logger="streamlink")
    return caplog


def pytest_generate_tests(metafunc: pytest.Metafunc):
    if metafunc.cls is None or not issubclass(metafunc.cls, PluginTest):
        return

    match metafunc.function.__name__:
        case "test_remotes":
            remotes = [k for k in metafunc.cls.__dict__.keys() if k.startswith("remote_")]
            metafunc.parametrize("remote", remotes, ids=[remote.removeprefix("remote_") for remote in remotes])
