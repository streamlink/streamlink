import json
import unittest
from unittest.mock import MagicMock, Mock

from streamlink import Streamlink
from streamlink.plugin.api import HTTPSession
from streamlink.plugins.garena import Garena
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlGarena(PluginCanHandleUrl):
    __plugin__ = Garena

    should_match = [
        "https://garena.live/LOLTW",
        "https://garena.live/358220",
    ]


class TestPluginGarena(unittest.TestCase):
    def setUp(self):
        self.session = Streamlink()
        self.session.http = MagicMock(HTTPSession)
        self.session.http.headers = {}

    def test_post_api_info(self):
        API_INFO = Garena.API_INFO
        schema = Garena._info_schema

        api_data = {
            "reply": {
                "channel_id": 358220,
            },
            "result": "success"
        }

        api_resp = Mock()
        api_resp.text = json.dumps(api_data)
        self.session.http.post.return_value = api_resp
        self.session.http.json.return_value = api_data

        payload = {"alias": "LOLTW"}

        Garena.bind(self.session, "test.garena")
        plugin = Garena("https://garena.live/LOLTW")

        info_data = plugin._post_api(API_INFO, payload, schema)

        self.assertEqual(info_data["channel_id"], 358220)

        self.session.http.post.assert_called_with(API_INFO, json=dict(alias="LOLTW"))

    def test_post_api_stream(self):
        API_STREAM = Garena.API_STREAM
        schema = Garena._stream_schema

        api_data = {
            "reply": {
                "streams": [
                    {
                        "url": "https://test.se/stream1",
                        "bitrate": 0,
                        "resolution": 1080,
                        "format": 3
                    },
                ]
            },
            "result": "success"
        }

        api_resp = Mock()
        api_resp.text = json.dumps(api_data)
        self.session.http.post.return_value = api_resp
        self.session.http.json.return_value = api_data

        payload = {"channel_id": 358220}

        Garena.bind(self.session, "test.garena")
        plugin = Garena("https://garena.live/358220")

        stream_data = plugin._post_api(API_STREAM, payload, schema)

        self.assertEqual(stream_data["streams"], api_data["reply"]["streams"])

        self.session.http.post.assert_called_with(API_STREAM, json=dict(channel_id=358220))
