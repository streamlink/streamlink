"""
$description Israeli live TV channel and video on-demand service owned by Network 13.
$url 13tv.co.il
$type live, vod
$region Israel
"""

import logging
import re
from urllib.parse import urljoin, urlunparse

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?13tv\.co\.il/(live|.*?/)"
))
class N13TV(Plugin):
    api_url = "https://13tv-api.oplayer.io/api/getlink/"
    main_js_url_re = re.compile(r'type="text/javascript" src="(.*?main\..+\.js)"')
    user_id_re = re.compile(r'"data-ccid":"(.*?)"')
    video_name_re = re.compile(r'"videoRef":"(.*?)"')
    server_addr_re = re.compile(r'(.*[^/])(/.*)')
    media_file_re = re.compile(r'(.*)(\.[^\.].*)')

    live_schema = validate.Schema(validate.all(
        [{'Link': validate.url()}],
        validate.get(0),
        validate.get('Link')
    ))

    vod_schema = validate.Schema(validate.all([{
        'ShowTitle': validate.text,
        'ProtocolType': validate.all(
            validate.text,
            validate.transform(lambda x: x.replace("://", ""))
        ),
        'ServerAddress': validate.text,
        'MediaRoot': validate.text,
        'MediaFile': validate.text,
        'Bitrates': validate.text,
        'StreamingType': validate.text,
        'Token': validate.all(
            validate.text,
            validate.transform(lambda x: x.lstrip("?"))
        )
    }], validate.get(0)))

    def _get_live(self, user_id):
        res = self.session.http.get(
            self.api_url,
            params=dict(
                userId=user_id,
                serverType="web",
                ch=1,
                cdnName="casttime"
            )
        )

        url = self.session.http.json(res, schema=self.live_schema)
        log.debug("URL={0}".format(url))

        return HLSStream.parse_variant_playlist(self.session, url)

    def _get_vod(self, user_id, video_name):
        res = self.session.http.get(
            urljoin(self.api_url, "getVideoByFileName"),
            params=dict(
                userId=user_id,
                videoName=video_name,
                serverType="web",
                callback="x"
            )
        )

        vod_data = self.session.http.json(res, schema=self.vod_schema)

        if video_name == vod_data['ShowTitle']:
            host, base_path = self.server_addr_re.search(
                vod_data['ServerAddress']
            ).groups()
            if not host or not base_path:
                raise PluginError("Could not split 'ServerAddress' components")

            base_file, file_ext = self.media_file_re.search(
                vod_data['MediaFile']
            ).groups()
            if not base_file or not file_ext:
                raise PluginError("Could not split 'MediaFile' components")

            media_path = "{0}{1}{2}{3}{4}{5}".format(
                base_path,
                vod_data['MediaRoot'],
                base_file,
                vod_data['Bitrates'],
                file_ext,
                vod_data['StreamingType']
            )
            log.debug("Media path={0}".format(media_path))

            vod_url = urlunparse((
                vod_data['ProtocolType'],
                host,
                media_path,
                '',
                vod_data['Token'],
                ''
            ))
            log.debug("URL={0}".format(vod_url))

            return HLSStream.parse_variant_playlist(self.session, vod_url)

    def _get_streams(self):
        url_type = self.match.group(1)
        log.debug("URL type={0}".format(url_type))

        res = self.session.http.get(self.url)

        if url_type != "live":
            m = self.video_name_re.search(res.text)
            video_name = m and m.group(1)
            if not video_name:
                raise PluginError('Could not determine video_name')
            log.debug("Video name={0}".format(video_name))

        m = self.main_js_url_re.search(res.text)
        main_js_path = m and m.group(1)
        if not main_js_path:
            raise PluginError('Could not determine main_js_path')
        log.debug("Main JS path={0}".format(main_js_path))

        res = self.session.http.get(urljoin(self.url, main_js_path))

        m = self.user_id_re.search(res.text)
        user_id = m and m.group(1)
        if not user_id:
            raise PluginError('Could not determine user_id')
        log.debug("User ID={0}".format(user_id))

        if url_type == "live":
            return self._get_live(user_id)
        else:
            return self._get_vod(user_id, video_name)


__plugin__ = N13TV
