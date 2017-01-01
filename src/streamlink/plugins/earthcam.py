from __future__ import print_function
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.compat import urlparse
from streamlink.stream import RTMPStream
from streamlink.utils import parse_json


class EarthCam(Plugin):
    url_re = re.compile(r"https?://(?:www.)?earthcam.com/.*")
    swf_url = "http://static.earthcam.com/swf/streaming/stream_viewer_v3.swf"
    json_base_re = re.compile(r"""var[ ]+json_base[^=]+=.*?(\{.*?});""", re.DOTALL)
    cam_name_re = re.compile(r"""var[ ]+currentName[^=]+=[ \t]+(?P<quote>["'])(?P<name>\w+)(?P=quote);""", re.DOTALL)
    cam_data_schema = validate.Schema(
        validate.transform(json_base_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.transform(lambda d: d.replace("\\/", "/")),
                validate.transform(parse_json),
            )
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = http.get(self.url)
        m = self.cam_name_re.search(res.text)
        cam_name = m and m.group("name")
        json_base = self.cam_data_schema.validate(res.text)

        cam_data = json_base["cam"][cam_name]

        self.logger.debug("Found cam for {} - {}", cam_data["group"], cam_data["title"])

        is_live = cam_data["liveon"] == "true"
        rtmp_domain = cam_data["streamingdomain" if is_live else "archivedomain"]
        if rtmp_domain:
            if is_live:
                playpath = cam_data.get("livestreamingpath")
            else:
                playpath = cam_data.get("archivepath")

            if not playpath:
                self.logger.error("This cam stream appears to be in offline or "
                                  "snapshot mode and not live stream can be played.")
                return

            rtmp_url = rtmp_domain + playpath

            self.logger.debug("RTMP URL: {0}", rtmp_url)

            params = {"rtmp": rtmp_url,
                      "playpath": playpath,
                      "pageUrl": self.url,
                      "swfUrl": self.swf_url}
            if is_live:
                params["live"] = True
            yield "live", RTMPStream(self.session, params)


__plugin__ = EarthCam
