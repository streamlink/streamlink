import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.compat import urlparse, parse_qsl
from streamlink.stream import HLSStream, HTTPStream, RTMPStream


class DeutscheWelle(Plugin):
    default_channel = "1"
    url_re = re.compile(r"https?://(?:www\.)?dw\.com/")

    channel_re = re.compile(r'''<a.*?data-id="(\d+)".*?class="ici"''')
    live_stream_div = re.compile(r'''
        <div\s+class="mediaItem"\s+data-channel-id="(\d+)".*?>.*?
        <input\s+type="hidden"\s+name="file_name"\s+value="(.*?)"\s*>.*?<div
    ''', re.DOTALL | re.VERBOSE)

    smil_api_url = "http://www.dw.com/smil/{}"
    html5_api_url = "http://www.dw.com/html5Resource/{}"
    vod_player_type_re = re.compile(r'<input type="hidden" name="player_type" value="(?P<stream_type>.+?)">')
    stream_vod_data_re = re.compile(r'<input\s+type="hidden"\s+name="file_name"\s+value="(?P<stream_url>.+?)">.*?'
                                    r'<input\s+type="hidden"\s+name="media_id"\s+value="(?P<stream_id>\d+)">',
                                    re.DOTALL)

    smil_schema = validate.Schema(
        validate.union({
            "base": validate.all(
                validate.xml_find(".//meta"),
                validate.xml_element(attrib={"base": validate.text}),
                validate.get("base")
            ),
            "streams": validate.all(
                validate.xml_findall(".//switch/*"),
                [
                    validate.all(
                        validate.getattr("attrib"),
                        {
                            "src": validate.text,
                            "system-bitrate": validate.all(
                                validate.text,
                                validate.transform(int),
                            ),
                            validate.optional("width"): validate.all(
                                validate.text,
                                validate.transform(int)
                            )
                        }
                    )
                ]
            )
        })
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _create_stream(self, url, quality=None):
        if url.startswith('rtmp://'):
            return (quality, RTMPStream(self.session, {'rtmp': url}))
        if url.endswith('.m3u8'):
            return HLSStream.parse_variant_playlist(self.session, url).items()

        return (quality, HTTPStream(self.session, url))

    def _get_live_streams(self, page):
        # check if a different language has been selected
        qs = dict(parse_qsl(urlparse(self.url).query))
        channel = qs.get("channel")

        if not channel:
            m = self.channel_re.search(page.text)
            channel = m and m.group(1)

        self.logger.debug("Using sub-channel ID: {0}", channel)

        # extract the streams from the page, mapping between channel-id and stream url
        media_items = self.live_stream_div.finditer(page.text)
        stream_map = dict([m.groups((1, 2)) for m in media_items])

        stream_url = stream_map.get(str(channel) or self.default_channel)
        if stream_url:
            return self._create_stream(stream_url)

    def _get_vod_streams(self, stream_type, page):
        m = self.stream_vod_data_re.search(page.text)
        if m is None:
            return
        stream_url, stream_id = m.groups()

        if stream_type == "video":
            stream_api_id = "v-{}".format(stream_id)
            default_quality = "vod"
        elif stream_type == "audio":
            stream_api_id = "a-{}".format(stream_id)
            default_quality = "audio"
        else:
            return

        # Retrieve stream embedded in web page
        yield self._create_stream(stream_url, default_quality)

        # Retrieve streams using API
        res = self.session.http.get(self.smil_api_url.format(stream_api_id))
        videos = self.session.http.xml(res, schema=self.smil_schema)

        for video in videos['streams']:
            url = videos["base"] + video["src"]
            if url == stream_url or url.replace("_dwdownload.", ".") == stream_url:
                continue

            if video["system-bitrate"] > 0:
                # If width is available, use it to select the best stream
                # amongst those with same bitrate
                quality = "{}k".format((video["system-bitrate"] + video.get("width", 0)) // 1000)
            else:
                quality = default_quality

            yield self._create_stream(url, quality)

    def _get_streams(self):
        res = self.session.http.get(self.url)
        m = self.vod_player_type_re.search(res.text)
        if m is None:
            return

        stream_type = m.group("stream_type")
        if stream_type == "dwlivestream":
            return self._get_live_streams(res)

        return self._get_vod_streams(stream_type, res)


__plugin__ = DeutscheWelle
