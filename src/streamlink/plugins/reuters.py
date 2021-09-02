import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r'https?://([\w-]+\.)*reuters\.(com|tv)'
))
class Reuters(Plugin):
    _re_fusion_global_content = re.compile(r"Fusion\s*\.\s*globalContent\s*=\s*(?P<json>{.+?})\s*;\s*Fusion\s*\.", re.DOTALL)
    _re_fusion_content_cache = re.compile(r"Fusion\s*\.\s*contentCache\s*=\s*(?P<json>{.+?})\s*;\s*Fusion\s*\.", re.DOTALL)

    def _get_data(self):
        root = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html()
        ))

        try:
            log.debug("Trying to find source via meta tag")
            schema = validate.Schema(
                validate.xml_xpath_string(".//meta[@property='og:video'][1]/@content"),
                validate.url()
            )
            return schema.validate(root)
        except PluginError:
            pass

        try:
            log.debug("Trying to find source via next-head")
            schema = validate.Schema(
                validate.xml_findtext(".//script[@type='application/ld+json'][@class='next-head']"),
                validate.transform(parse_json),
                {"contentUrl": validate.url()},
                validate.get("contentUrl")
            )
            return schema.validate(root)
        except PluginError:
            pass

        schema_fusion = validate.xml_findtext(".//script[@type='application/javascript'][@id='fusion-metadata']")
        schema_video = validate.all(
            {"source": {"hls": validate.url()}},
            validate.get(("source", "hls"))
        )
        try:
            log.debug("Trying to find source via fusion-metadata globalContent")
            schema = validate.Schema(
                schema_fusion,
                validate.transform(self._re_fusion_global_content.search),
                validate.get("json"),
                validate.transform(parse_json),
                {"result": {"related_content": {"videos": list}}},
                validate.get(("result", "related_content", "videos", 0)),
                schema_video
            )
            return schema.validate(root)
        except PluginError:
            pass

        try:
            log.debug("Trying to find source via fusion-metadata contentCache")
            schema = validate.Schema(
                schema_fusion,
                validate.transform(self._re_fusion_content_cache.search),
                validate.get("json"),
                validate.transform(parse_json),
                {"videohub-by-guid-v1": {str: {"data": {"result": {"videos": list}}}}},
                validate.get("videohub-by-guid-v1"),
                validate.transform(lambda obj: obj[list(obj.keys())[0]]),
                validate.get(("data", "result", "videos", 0)),
                schema_video
            )
            return schema.validate(root)
        except PluginError:
            pass

    def _get_streams(self):
        hls_url = self._get_data()
        if hls_url:
            return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = Reuters
