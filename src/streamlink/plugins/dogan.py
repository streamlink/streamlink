"""
$description Turkish live TV channels and video on-demand service from Dogan Group, including CNN Turk and Kanal D.
$url cnnturk.com
$url dreamturk.com.tr
$url dreamtv.com.tr
$url kanald.com.tr
$url teve2.com.tr
$type live, vod
"""

import logging
import re
from urllib.parse import urljoin

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"https?://(?:www\.)?cnnturk\.com/"))
@pluginmatcher(re.compile(r"https?://(?:www\.)?(dreamturk|dreamtv)\.com\.tr/"))
@pluginmatcher(re.compile(r"https?://(?:www\.)?teve2\.com\.tr/"))
@pluginmatcher(re.compile(r"https?://(?:www\.)?kanald\.com\.tr/"))
class Dogan(Plugin):
    # based on the order of matchers
    API_URLS = [
        "/api/media?id={id}",
        "/actions/content/media/{id}",
        "/action/media/{id}",
    ]
    API_URL_OLD = "/actions/media?id={id}"

    def _get_content_id(self):
        return self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
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
            ),
        )

    def _api_query_new(self, content_id, api_url):
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
                                    "ContentId": str,
                                    validate.optional("DefaultServiceUrl"): validate.any(validate.url(), ""),
                                    validate.optional("ServiceUrl"): validate.any(validate.url(), ""),
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
        if type(data) is str:
            log.error(data)
            return

        service_url, default_service_url, secure_path, content_id = data

        if default_service_url == "https://www.kanald.com.tr":
            self.url = default_service_url
            return self._api_query_old(content_id)

        if re.match(r"^https?://", secure_path):
            return secure_path

        return urljoin(service_url or default_service_url, secure_path)

    def _api_query_old(self, content_id):
        url = urljoin(self.url, self.API_URL_OLD.format(id=content_id))
        service_url, default_service_url, secure_path = self.session.http.get(
            url,
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "data": {
                        "id": str,
                        "media": {
                            "link": {
                                validate.optional("defaultServiceUrl"): validate.any(validate.url(), ""),
                                validate.optional("serviceUrl"): validate.any(validate.url(), ""),
                                "securePath": str,
                            },
                        },
                    },
                },
                validate.get(("data", "media", "link")),
                validate.union_get("serviceUrl", "defaultServiceUrl", "securePath"),
            ),
        )

        return urljoin(service_url or default_service_url, secure_path)

    def _get_hls_url(self, content_id):
        for idx, match in enumerate(self.matches[:len(self.API_URLS)]):
            if match:
                return self._api_query_new(content_id, self.API_URLS[idx])

        return self._api_query_old(content_id)

    def _get_streams(self):
        try:
            content_id = self._get_content_id()
        except PluginError:
            log.error("Could not find the content ID for this stream")
            return

        log.debug(f"Loading content: {content_id}")
        hls_url = self._get_hls_url(content_id)
        if not hls_url:
            return

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = Dogan
