import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, RTMPStream
from streamlink.utils import parse_json, update_scheme

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?earthcam\.com/"
))
class EarthCam(Plugin):
    playpath_re = re.compile(r"(?P<folder>/.*/)(?P<file>.*?\.flv)")
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

    def _get_streams(self):
        res = self.session.http.get(self.url)
        m = self.cam_name_re.search(res.text)
        cam_name = m and m.group("name")
        json_base = self.cam_data_schema.validate(res.text)

        cam_data = json_base["cam"][cam_name]

        log.debug("Found cam for {0} - {1}".format(cam_data["group"], cam_data["title"]))

        is_live = (cam_data["liveon"] == "true" and cam_data["defaulttab"] == "live")

        # HLS data
        hls_domain = cam_data["html5_streamingdomain"]
        hls_playpath = cam_data["html5_streampath"]

        # RTMP data
        rtmp_playpath = ""
        if is_live:
            n = "live"
            rtmp_domain = cam_data["streamingdomain"]
            rtmp_path = cam_data["livestreamingpath"]
            rtmp_live = cam_data["liveon"]

            if rtmp_path:
                match = self.playpath_re.search(rtmp_path)
                rtmp_playpath = match.group("file")
                rtmp_url = rtmp_domain + match.group("folder")
        else:
            n = "vod"
            rtmp_domain = cam_data["archivedomain"]
            rtmp_path = cam_data["archivepath"]
            rtmp_live = cam_data["archiveon"]

            if rtmp_path:
                rtmp_playpath = rtmp_path
                rtmp_url = rtmp_domain

        # RTMP stream
        if rtmp_playpath:
            log.debug("RTMP URL: {0}{1}".format(rtmp_url, rtmp_playpath))

            params = {
                "rtmp": rtmp_url,
                "playpath": rtmp_playpath,
                "pageUrl": self.url,
                "swfUrl": self.swf_url,
                "live": rtmp_live
            }

            yield n, RTMPStream(self.session, params)

        # HLS stream
        if hls_playpath and is_live:
            hls_url = hls_domain + hls_playpath
            hls_url = update_scheme(self.url, hls_url)

            log.debug("HLS URL: {0}".format(hls_url))

            yield from HLSStream.parse_variant_playlist(self.session, hls_url).items()

        if not (rtmp_playpath or hls_playpath):
            log.error("This cam stream appears to be in offline or "
                      "snapshot mode and not live stream can be played.")
            return


__plugin__ = EarthCam
