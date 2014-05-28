import re

from functools import reduce

from livestreamer.compat import urlparse, unquote, range
from livestreamer.exceptions import PluginError
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HDSStream, HTTPStream, RTMPStream
from livestreamer.stream.playlist import FLVPlaylist
from livestreamer.utils import verifyjson

METADATA_URL = "https://api.dailymotion.com/video/{0}"
QUALITY_MAP = {
    "ld": "240p",
    "sd": "360p",
    "hq": "480p",
    "hd720": "720p",
    "hd1080": "1080p",
    "custom": "live",
    "auto": "hds"
}
RTMP_SPLIT_REGEX = r"(?P<host>rtmp://[^/]+)/(?P<app>[^/]+)/(?P<playpath>.+)"
STREAM_INFO_URL = "http://www.dailymotion.com/sequence/full/{0}"


class DailyMotion(Plugin):
    @classmethod
    def can_handle_url(self, url):
        # valid urls are of the form dailymotion.com/video/[a-z]{5}.*
        # but we make "video/" optional and allow for dai.ly as shortcut
        # Gamecreds uses Dailymotion as backend so we support it through this plugin.
        return ("dailymotion.com" in url) or ("dai.ly" in url) or ("video.gamecreds.com" in url)

    def _check_channel_live(self, channelname):
        url = METADATA_URL.format(channelname)
        res = http.get(url, params=dict(fields="mode"))
        json = http.json(res)

        if not isinstance(json, dict):
            raise PluginError("Invalid JSON response")

        mode = verifyjson(json, "mode")

        return mode == "live"

    def _get_channel_name(self, url):
        name = None
        if ("dailymotion.com" in url) or ("dai.ly" in url):
            rpart = urlparse(url).path.rstrip("/").rpartition("/")[-1].lower()
            name = re.sub("_.*", "", rpart)
        elif ("video.gamecreds.com" in url):
            res = http.get(url)
            # The HTML is broken (unclosed meta tags) and minidom fails to parse.
            # Since we are not manipulating the DOM, we get away with a simple grep instead of fixing it.
            match = re.search("<meta property=\"og:video\" content=\"http://www.dailymotion.com/swf/video/([a-z0-9]{6})", res.text)
            if match: name = match.group(1)

        return name

    def _get_node_by_name(self, parent, name):
        res = None
        for node in parent:
            if node["name"] == name:
                res = node
                break

        return res

    def _get_rtmp_streams(self, channelname):
        self.logger.debug("Fetching stream info")
        res = http.get(STREAM_INFO_URL.format(channelname))
        json = http.json(res)

        if not isinstance(json, dict):
            raise PluginError("Invalid JSON response")

        if not json:
            raise PluginError("JSON is empty")

        # This is ugly, not sure how to fix it.
        back_json_node = json["sequence"][0]["layerList"][0]
        if back_json_node["name"] != "background":
            raise PluginError("JSON data has unexpected structure")

        rep_node = self._get_node_by_name(back_json_node["sequenceList"], "reporting")["layerList"]
        main_node = self._get_node_by_name(back_json_node["sequenceList"], "main")["layerList"]

        if not (rep_node and main_node):
            raise PluginError("Error parsing stream RTMP url")

        swfurl = self._get_node_by_name(rep_node, "reporting")["param"]["extraParams"]["videoSwfURL"]
        feeds_params = self._get_node_by_name(main_node, "video")["param"]

        if not (swfurl and feeds_params):
            raise PluginError("Error parsing stream RTMP url")


        # Different feed qualities are available are a dict under "live"
        # In some cases where there's only 1 quality available,
        # it seems the "live" is absent. We use the single stream available
        # under the "customURL" key.
        streams = {}
        if "mode" in feeds_params and feeds_params["mode"] == "live":
            for key, quality in QUALITY_MAP.items():
                url = feeds_params.get("{0}URL".format(key))
                if not url:
                    continue

                try:
                    res = http.get(url, exception=IOError)
                except IOError:
                    continue

                if quality == "hds":
                    hds_streams = HDSStream.parse_manifest(self.session,
                                                           res.url)
                    streams.update(hds_streams)
                else:
                    match = re.match(RTMP_SPLIT_REGEX, res.text)
                    if not match:
                        self.logger.warning("Failed to split RTMP URL: {0}",
                                            res.text)
                        continue

                    stream = RTMPStream(self.session, {
                        "rtmp": match.group("host"),
                        "app": match.group("app"),
                        "playpath": match.group("playpath"),
                        "swfVfy": swfurl,
                        "live": True
                    })

                    self.logger.debug("Adding URL: {0}", res.text)
                    streams[quality] = stream

        return streams

    def _create_flv_playlist(self, template):
        res = http.get(template)
        json = http.json(res)

        if not isinstance(json, dict):
            raise PluginError("Invalid JSON response")

        parsed = urlparse(template)
        try:
            url_template = '{0}://{1}{2}'.format(
                parsed.scheme, parsed.netloc, json['template']
            )
            segment_max = reduce(lambda i,j: i+j[0], json['fragments'], 0)
            duration = json['duration']
        except KeyError:
            raise PluginError('Unexpected JSON response')

        substreams = [HTTPStream(self.session,
                                 url_template.replace('$fragment$', str(i)))
                      for i in range(1, segment_max + 1)]

        return FLVPlaylist(self.session, streams=substreams,
                           duration=duration, skip_header=True,
                           flatten_timestamps=True)

    def _get_vod_streams(self, channelname):
        res = http.get(self.url)
        match = re.search('autoURL%22%3A%22(.*?)%22', res.text)
        if not match:
            raise PluginError('Error retrieving manifest url')
        manifest_url = unquote(match.group(1)).replace('\\', '')

        try:
            res = http.get(manifest_url)
            manifest = http.json(res)
        except:
            raise PluginError('Error retrieving manifest')

        # A fallback host (http://proxy-xx...) is sometimes provided
        # that we could make us of.
        streams = {}
        for params in manifest.get('alternates', []):
            name = params.get('name')
            template = params.get('template')
            if not (name and template):
                continue

            name = '{0}p'.format(name)
            streams[name] = self._create_flv_playlist(template)

        return streams

    def _get_streams(self):
        channelname = self._get_channel_name(self.url)

        if not channelname:
            return

        if self._check_channel_live(channelname):
            return self._get_rtmp_streams(channelname)
        else:
            return self._get_vod_streams(channelname)


__plugin__ = DailyMotion


# vim: expandtab tabstop=4 shiftwidth=4
