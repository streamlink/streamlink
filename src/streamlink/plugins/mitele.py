from __future__ import print_function

import re
from base64 import b64decode

from datetime import datetime
from uuid import uuid4

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json


class Mitele(Plugin):
    url_re = re.compile(r"https?://(?:www.)?mitele.es/directo/(\w+)")
    supported_channels = ("telecinco", "bemad", "boing", "cuatro")
    app_key = "56c3464fe4b0b8a18ac02511"
    session_url = "https://appgrid-api.cloud.accedo.tv/session"
    config_url = "https://appgrid-api.cloud.accedo.tv/metadata/general_configuration, web_configuration?" \
                 "sessionKey={key}"
    channel_id_url = "http://indalo.mediaset.es/mmc-player/api/mmc/v1/{channel}/live/flash.json"
    stream_info_url = "http://player.ooyala.com/sas/player_api/v2/authorization/embed_code/{key}/{yoo}?" \
                      "device=html5&domain=www.mitele.es"
    session_schema = validate.Schema({
        "sessionKey": validate.text,
        "expiration": validate.transform(lambda d: datetime.strptime(d, "%Y%m%dT%H:%M:%S+0000"))
    })
    config_schema = validate.Schema({
        "general_configuration": {
            "api_configuration": {
                "ooyala_discovery": {
                    "api_key": validate.text
                }
            }
        }
    })
    channel_id_schema = validate.Schema(
        validate.all(
            {"locations": [{"yoo": validate.text}]},
            validate.get("locations"),
            validate.get(0),
            validate.get("yoo")
        )
    )
    stream_info_schema = validate.Schema({
        "authorization_data": {
            validate.text: {
                "authorized": bool,
                "message": validate.text,
                validate.optional("streams"): [{
                    "delivery_type": validate.text,
                    "url": {
                        "format": "encoded",
                        "data": validate.all(validate.text,
                                             validate.transform(b64decode),
                                             validate.transform(lambda d: d.decode("utf8")),
                                             validate.url())
                    }
                }]
            }
        }
    })

    @classmethod
    def can_handle_url(cls, url):
        m = cls.url_re.match(url)
        return m and m.group(1) in cls.supported_channels

    @property
    def session_key(self):
        """
        Get a cached or new session key, uuid is a random uuid (type 4)
        :return:
        """
        session_key = self.cache.get("sessionKey")
        if session_key:
            self.logger.debug("Using cached sessionKey")
            return session_key
        else:
            self.logger.debug("Requesting new sessionKey")
            uuid = uuid4()
            res = http.get(self.session_url, params=dict(appKey=self.app_key, uuid=uuid))
            data = parse_json(res.text, schema=self.session_schema)
            # when to expire the sessionKey, -1 hour for good measure
            expires_in = (data["expiration"] - datetime.now()).total_seconds() - 3600
            self.cache.set("sessionKey", data["sessionKey"], expires=expires_in)
            return data["sessionKey"]

    @property
    def config(self):
        """
        Get the API config data
        """
        config_res = http.get(self.config_url.format(key=self.session_key))
        return parse_json(config_res.text, schema=self.config_schema)

    def get_channel_id(self, channel):
        """
        Get the ID of the channel form the name
        :param channel: channel name
        :return: channel id
        """
        channel_id_res = http.get(self.channel_id_url.format(channel=channel))
        return parse_json(channel_id_res.text, schema=self.channel_id_schema)

    def get_stream_info(self, key, channel_id):
        """
        Get details about the streams
        :param key: API key
        :param channel_id: channel id
        :return: stream info
        """
        stream_info_res = http.get(self.stream_info_url.format(key=key, yoo=channel_id))
        return parse_json(stream_info_res.text, schema=self.stream_info_schema)

    def _get_streams(self):
        channel = self.url_re.match(self.url).group(1)

        key, sig = self.config["general_configuration"]["api_configuration"]["ooyala_discovery"]["api_key"].split(".")
        self.logger.debug("Got api key: {}.{}", key, sig)

        channel_id = self.get_channel_id(channel)
        self.logger.debug("Got channel ID {} for channel {}", channel_id, channel)

        data = self.get_stream_info(key, channel_id)

        stream_info = data["authorization_data"][channel_id]

        if stream_info["authorized"]:
            for stream in stream_info["streams"]:
                if stream["delivery_type"] == "hls":
                    for s in HLSStream.parse_variant_playlist(self.session, stream["url"]["data"]).items():
                        yield s

        else:
            self.logger.error("Cannot load streams: {}", stream_info["message"])


__plugin__ = Mitele
