"""
$url ozolio.com
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?ozolio\.com/explore/?(?P<id>(\w+))?"
))
class Ozolio(Plugin):
    _og_url_re = re.compile(r"""<meta\s*property="og:url"\s*content="https?://(?:www\.)?ozolio\.com/explore/?(?P<id>(\w+)")?""")

    _sesapi_cid_url = "https://relay.ozolio.com/ses.api?cmd=init&oid=CID_{cid}&ver=5&channel=0&control=1"
    _sesapi_sid_url = "https://relay.ozolio.com/ses.api?cmd=open&oid={sid}&output=1&format=M3U8"
    _sesapi_cid_schema = validate.Schema(
        {
            "session": {
                "id": validate.text,
            }
        },
        validate.get("session"),
        validate.get("id"),
    )
    _sesapi_sid_schema = validate.Schema(
        {
            "output": {
                "state": "Active",
                "source": validate.url(),
            }
        },
        validate.get("output"),
        validate.get("source"),
    )

    def _get_streams(self):
        res = self.match.group("id")
        if not res:
            res = self.session.http.get(self.url)
            res = self._og_url_re.search(res.text).group("id")

        if res:
            document = {"document": self.url}
            try:
                res = self.session.http.get(self._sesapi_cid_url.format(cid=res), params=document)
                res = self.session.http.json(res, schema=self._sesapi_cid_schema)
                res = self.session.http.get(self._sesapi_sid_url.format(sid=res))
                res = self.session.http.json(res, schema=self._sesapi_sid_schema)
            except PluginError as err:
                log.debug(err)
            else:
                return HLSStream.parse_variant_playlist(self.session, res)


__plugin__ = Ozolio
