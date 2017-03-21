import json
import unittest

from streamlink import Streamlink

try:
    from unittest.mock import patch, Mock
except ImportError:
    from mock import patch, Mock

from streamlink.plugins.garena import Garena


class TestPluginGarena(unittest.TestCase):
    def setUp(self):
        self.session = Streamlink()

    def test_can_handle_url(self):
        # should match
        self.assertTrue(Garena.can_handle_url("https://garena.live/LOLTW"))
        self.assertTrue(Garena.can_handle_url("https://garena.live/358220"))

        # shouldn't match
        self.assertFalse(Garena.can_handle_url("http://local.local/"))
        self.assertFalse(Garena.can_handle_url("http://localhost.localhost/"))

    @patch('streamlink.plugins.garena.http')
    def test_post_api_info(self, mock_http):
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
        mock_http.post.return_value = api_resp
        mock_http.json.return_value = api_data

        payload = {"alias": "LOLTW"}

        plugin = Garena("https://garena.live/LOLTW")

        info_data = plugin._post_api(API_INFO, payload, schema)

        self.assertEqual(info_data["channel_id"], 358220)

        mock_http.post.assert_called_with(API_INFO, json=dict(alias="LOLTW"))

    @patch('streamlink.plugins.garena.http')
    def test_post_api_stream(self, mock_http):
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
        mock_http.post.return_value = api_resp
        mock_http.json.return_value = api_data

        payload = {"channel_id": 358220}

        plugin = Garena("https://garena.live/358220")

        stream_data = plugin._post_api(API_STREAM, payload, schema)

        self.assertEqual(stream_data["streams"], api_data["reply"]["streams"])

        mock_http.post.assert_called_with(API_STREAM, json=dict(channel_id=358220))
