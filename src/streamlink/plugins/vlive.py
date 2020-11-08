import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class Vlive(Plugin):
    _url_re = re.compile(r"https://www\.vlive\.tv/(?P<format>video|post)/(?P<id>[0-9\-]+)")
    _page_info = re.compile(r'window\.__PRELOADED_STATE__\s*=\s*({.*})\s*<', re.DOTALL)
    _playinfo_url = "https://www.vlive.tv/globalv-web/vam-web/old/v3/live/{0}/playInfo"

    _schema_video = validate.Schema(
        validate.transform(_page_info.search),
        validate.any(None, validate.all(
            validate.get(1),
            validate.transform(parse_json),
            validate.any(validate.all(
                {"postDetail": {"post": {"officialVideo": {
                    "type": str,
                    "videoSeq": int,
                    validate.optional("status"): str,
                }}}},
                validate.get("postDetail"),
                validate.get("post"),
                validate.get("officialVideo")),
                validate.all(
                    {"postDetail": {"error": {
                        "errorCode": str,
                    }}},
                    validate.get("postDetail"),
                    validate.get("error")))
        ))
    )

    _schema_stream = validate.Schema(
        validate.transform(parse_json),
        validate.all(
            {"result": {"streamList": [{
                "streamName": str,
                "serviceUrl": str,
            }]}},
            validate.get("result"),
            validate.get("streamList")
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        video_json = self.session.http.get(self.url, headers={"Referer": self.url},
                                           schema=self._schema_video)
        if video_json is None:
            log.error('Could not parse video page')
            return

        err = video_json.get('errorCode')
        if err == 'common_700':
            log.error('Available only to members of the channel')
            return
        elif err == 'common_702':
            log.error('Vlive+ VODs are not supported')
            return
        elif err == 'common_404':
            log.error('Could not find video page')
            return
        elif err is not None:
            log.error('Unknown error code: {0}'.format(err))
            return

        if video_json['type'] == 'VOD':
            log.error('VODs are not supported')
            return

        url_format, video_id = self._url_re.match(self.url).groups()
        if url_format == 'post':
            video_id = str(video_json['videoSeq'])

        video_status = video_json.get('status')
        if video_status == 'ENDED':
            log.error('Stream has ended')
            return
        elif video_status != 'ON_AIR':
            log.error('Unknown video status: {0}'.format(video_status))
            return

        stream_info = self.session.http.get(self._playinfo_url.format(video_id),
                                            headers={"Referer": self.url},
                                            schema=self._schema_stream)

        # All "resolutions" have a variant playlist with only one entry, so just combine them
        for i in stream_info:
            res_streams = HLSStream.parse_variant_playlist(self.session, i['serviceUrl'])
            if len(res_streams.values()) > 1:
                log.warning('More than one stream in variant playlist, using first entry!')

            yield i['streamName'], res_streams.popitem()[1]


__plugin__ = Vlive
