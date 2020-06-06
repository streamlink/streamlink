import logging
import re

from streamlink.compat import urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class N13TV(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?13tv\.co\.il/(live|.*?/)")
    api_url = "https://13tv-api.oplayer.io/api/getlink/"
    api_vod_path = "getVideoByFileName"
    main_js_url_re = re.compile(r'type="text/javascript" src="(.*?main\..+\.js)"')
    user_id_re = re.compile(r'"data-ccid":"(.*?)"')
    video_name_re = re.compile(r'"videoRef":"(.*?)"')

    live_schema = validate.Schema([{
        'Link': validate.url()
    }])

    vod_schema = validate.Schema([{
        'ShowTitle': validate.text,
        'ProtocolType': validate.text,
        'ServerAddress': validate.text,
        'MediaRoot': validate.text,
        'MediaFile': validate.text,
        'Bitrates': validate.text,
        'StreamingType': validate.text,
        'Token': validate.text
    }])

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        m = self.url_re.match(self.url)
        base_path = m and m.group(1)
        log.debug("Base path = {0}", base_path)

        res = self.session.http.get(self.url)

        if base_path != "live":
            m = self.video_name_re.search(res.text)
            video_name = m and m.group(1)
            log.debug("Video name = {0}", video_name)

        m = self.main_js_url_re.search(res.text)
        main_js_path = m and m.group(1)
        log.debug("Main JS path = {0}", main_js_path)

        parsed_url = urlparse(self.url)
        res = self.session.http.get(
            parsed_url.scheme + '://'
            + parsed_url.netloc + main_js_path
        )

        m = self.user_id_re.search(res.text)
        user_id = m and m.group(1)
        log.debug("User ID = {0}", user_id)

        if base_path == "live":
            res = self.session.http.get(
                self.api_url,
                params=dict(
                    userId=user_id,
                    serverType="web",
                    ch=1,
                    cdnName="casttime"
                )
            )

            live = self.session.http.json(res, schema=self.live_schema)
            log.debug("Live URL = {0}", live[0]['Link'])

            return HLSStream.parse_variant_playlist(self.session, live[0]['Link'])
        else:
            res = self.session.http.get(
                self.api_url + self.api_vod_path,
                params=dict(
                    userId=user_id,
                    videoName=video_name,
                    serverType="web",
                    callback="x"
                )
            )

            vod = self.session.http.json(res, schema=self.vod_schema)

            if video_name == vod[0]['ShowTitle']:
                media_file_parts = vod[0]['MediaFile'].split('.')
                media_file = (
                    media_file_parts[0]
                    + vod[0]['Bitrates']
                    + '.'
                    + media_file_parts[1]
                )
                log.debug("Media file = {0}", media_file)

                vod_url = (
                    vod[0]['ProtocolType']
                    + vod[0]['ServerAddress']
                    + vod[0]['MediaRoot']
                    + media_file + vod[0]['StreamingType']
                    + vod[0]['Token']
                )
                log.debug("VOD URL = {0}", vod_url)

                return HLSStream.parse_variant_playlist(self.session, vod_url)
            else:
                return


__plugin__ = N13TV
