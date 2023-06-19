from unittest.mock import ANY, AsyncMock, call

import pytest

from tests.webbrowser.cdp import FakeWebsocketConnection


@pytest.fixture()
def websocket_connection(monkeypatch: pytest.MonkeyPatch):
    fake_websocket_connection = FakeWebsocketConnection()
    mock_connect_websocket_url = AsyncMock(return_value=fake_websocket_connection)
    monkeypatch.setattr("streamlink.webbrowser.cdp.connection.connect_websocket_url", mock_connect_websocket_url)

    try:
        yield fake_websocket_connection
    finally:
        assert fake_websocket_connection.closed
        assert mock_connect_websocket_url.call_args_list == [call(ANY, "ws://localhost:1234/fake", max_message_size=2 ** 24)]
