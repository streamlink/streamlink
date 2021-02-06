import re

from streamlink.plugin import Plugin, PluginError
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json


class Nasa(Plugin):
    # hardcoded API version, extracted from player.min.js
    _api_version = "201510271133"
    # hardcoded "vendor-id/stream-id", extracted from nasa.js (EmberJS component properties)
    _vendorandstreamids = {
        "public": "3117/108566",
        "media": "3117/108567"
    }

    # the API URL also optionally takes an "u" parameter read from the "mrp-v-id" cookie, and "_" with an UNIX timestamp
    _tpl_api_url = "https://mr-a.akamaihd.net/c/data/{id}/{filename}?domain=www.nasa.gov&r={url}"
    # reconstructed from player.min.js
    _tpl_filename = "{streamid}.{ishttps}.1.{apiversion}.json"

    _re_url = re.compile(r"https?://www\.nasa\.gov/multimedia/nasatv/(?:index\.html)?#(?P<channel>public|media)")
    _re_jsonp = re.compile(r"_data_callback_\d+json\(({.+})\);")

    _schema_api_response = validate.Schema(
        validate.transform(_re_jsonp.match),
        validate.any(None, validate.all(
            validate.get(1),
            validate.transform(parse_json),
            {"playlist": {"playlist_items": [validate.all(
                {"media_items": list},
                validate.get("media_items")
            )]}},
            validate.get("playlist"),
            validate.get("playlist_items")
        ))
    )
    _schema_media_items = validate.Schema(
        {
            "list_item_type": "media",
            "stream_names": validate.all({"default": str}, validate.get("default")),
            "video_url": validate.all({"default": validate.url()}, validate.get("default"))
        },
        validate.union((
            validate.get("stream_names"),
            validate.get("video_url")
        ))
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._re_url.match(url) is not None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._title = None

    def get_title(self):
        return self._title

    def _get_api_url(self, channel):
        if channel not in self._vendorandstreamids:
            raise PluginError(f"Missing stream id for channel '{channel}'")
        vendorandstreamid = self._vendorandstreamids[channel]

        return self._tpl_api_url.format(
            id=vendorandstreamid,
            filename=self._tpl_filename.format(
                streamid=vendorandstreamid.split("/")[1],
                ishttps="1",
                apiversion=self._api_version
            ),
            url=self.url
        )

    def _get_streams(self):
        channel = self._re_url.match(self.url).group("channel")
        api_url = self._get_api_url(channel)
        playlist_items = self.session.http.get(api_url, schema=self._schema_api_response)
        if not playlist_items:
            return

        for media_items in playlist_items:
            for item in media_items:
                try:
                    title, url = self._schema_media_items.validate(item)
                    self._title = title
                    return HLSStream.parse_variant_playlist(self.session, url, name_fmt="{pixels}_{bitrate}")
                except PluginError:
                    continue


__plugin__ = Nasa
