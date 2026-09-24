"""
$description Turkish live TV channels and video on-demand service from Dogan Group, including CNN Turk and Kanal D.
$url cnnturk.com
$url dreamturk.com.tr
$url dreamtv.com.tr
$url kanald.com.tr
$type live, vod
"""

import re
from urllib.parse import urljoin

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = getLogger(__name__)


@pluginmatcher(
    name="cnnturk",
    pattern=re.compile(r"https?://(?:www\.)?cnnturk\.com/"),
)
@pluginmatcher(
    name="dreamturk",
    pattern=re.compile(r"https?://(?:www\.)?(dreamturk|dreamtv)\.com\.tr/"),
)
@pluginmatcher(
    name="kanald",
    pattern=re.compile(r"https?://(?:www\.)?kanald\.com\.tr/"),
)
class Dogan(Plugin):
    API_URLS = {
        "cnnturk": "/api/cnnvideo/media?id={id}&isMobile=false",
        "dreamturk": "/actions/content/media/{id}",
    }
    DAILYMOTION_URL = "https://www.dailymotion.com/embed/video/{id}"

    @staticmethod
    def _get_content_url(root):
        schema = validate.Schema(
            validate.xml_xpath_string(
                ".//script[@type='application/ld+json'][contains(text(),'\"contentUrl\"')][1]/text()",
            ),
            validate.none_or_all(
                validate.parse_json(),
                {
                    # the same JSON schema is used on CNNTurk, so check for .m3u8 ending and fail silently otherwise
                    "contentUrl": validate.url(path=validate.endswith(".m3u8")),
                },
                validate.get("contentUrl"),
            ),
        )

        try:
            return schema.validate(root, exception=ValueError)
        except ValueError:
            return None

    @staticmethod
    def _get_content_id(root):
        schema = validate.Schema(
            validate.any(
                validate.all(
                    validate.xml_xpath_string("""
                        .//div[@data-id][
                            @data-live
                            or @id='video-element'
                            or @id='player-container'
                            or contains(@class, 'player-container')
                        ][1]/@data-id
                    """),
                    str,
                ),
                # xpath query needs to have a lower priority
                validate.all(
                    validate.xml_xpath_string(
                        ".//body[@data-content-id][1]/@data-content-id",
                    ),
                    str,
                ),
            ),
        )

        return schema.validate(root)

    def _api_query(self, content_id, api_url):
        url = urljoin(self.url, api_url.format(id=content_id))
        data = self.session.http.get(
            url,
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        str,
                        validate.parse_json(),
                        {"Error": str},
                        validate.get("Error"),
                    ),
                    validate.all(
                        {
                            "Media": {
                                "Link": {
                                    "ContentId": validate.any(str, None),
                                    validate.optional("DefaultServiceUrl"): validate.any(validate.url(), "", None),
                                    validate.optional("ServiceUrl"): validate.any(validate.url(), "", None),
                                    "SecurePath": str,
                                },
                            },
                        },
                        validate.get(("Media", "Link")),
                        validate.union_get("ServiceUrl", "DefaultServiceUrl", "SecurePath", "ContentId"),
                    ),
                ),
            ),
        )
        if isinstance(data, str):
            log.error(data)
            return

        service_url, default_service_url, secure_path, content_id = data

        if re.match(r"^https?://(?:www\.)?dailymotion\.com/", service_url or ""):
            return self.DAILYMOTION_URL.format(id=secure_path)

        if re.match(r"^https?://", secure_path):
            return secure_path

        return urljoin(service_url or default_service_url, secure_path)

    def _query_hls_url(self, content_id):
        for matcher in self.matchers:
            if matcher.pattern is self.matcher and matcher.name:
                return self._api_query(content_id, self.API_URLS[matcher.name])

    def _get_streams(self):
        root = self.session.http.get(self.url, schema=validate.Schema(validate.parse_html()))

        hls_url = self._get_content_url(root)
        if not hls_url:
            try:
                content_id = self._get_content_id(root)
            except PluginError:
                log.error("Could not find the content ID for this stream")
                return

            log.debug(f"Loading content: {content_id}")
            hls_url = self._query_hls_url(content_id)

        if not hls_url:
            return

        if hls_url.startswith(self.DAILYMOTION_URL.format(id="")):
            log.debug(f"Loading Dailymotion video: {hls_url}")
            return self.session.streams(hls_url)

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = Dogan
