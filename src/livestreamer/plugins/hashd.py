from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget, res_json

import math

class Hashd(Plugin):
    SWFURL = "http://cdn.hashd.tv/player/player.swf"
    GEOIPURL = "http://freegeoip.net/json/"
    GEOURL = "http://maps.googleapis.com/maps/api/geocode/json?address="

    @classmethod
    def can_handle_url(self, url):
        return "hashd.tv" in url

    def _distance(self, origin, destination):
        lat1, lon1 = origin
        lat2, lon2 = destination
        radius = 6371 # km

        dlat = math.radians(lat2-lat1)
        dlon = math.radians(lon2-lon1)
        a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
            * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        d = radius * c

        return d
        
    def _choose_server(self, json):
        res = urlget(self.GEOIPURL)
        loc = res_json(res)
        loc = [loc["latitude"], loc["longitude"]]
        sel_dist = float("inf")
        i = 0
        primary = -1
        secondary = -1

        for server in json["server"]:
            res = urlget(self.GEOURL+server["server"]["name"]+"&sensor=false")
            cord = res_json(res)
            cord = [cord["results"][0]["geometry"]["location"]["lat"], cord["results"][0]["geometry"]["location"]["lng"]]
            cur_dist = self._distance(loc, cord)

            if cur_dist < sel_dist:
                sel_dist = cur_dist

                if server["server"]["used"] < 90:
                    # nearest server with load < 90%
                    primary = i
                else:
                    # nearest server with load > 90%
                    secondary = i

            i += 1

        if primary == -1:
            # if all servers have load over 90% use nearest one
            return secondary

        return primary

    def _parse_vod(self, json):
        streams = {}
        
        if json["stream_protocol"] != "rtmp":
            # Just in case. I coudn't find any non-rtmp streams. 
            raise NoStreamsError(self.url)
            
        streams["vod"] = RTMPStream(self.session, {
            "rtmp": json["stream_url"]+"/"+json["file"],
            "pageUrl": self.url,
            "swfUrl": self.SWFURL,
            "live": True
        })

        return streams

    def _parse_live(self, json):
        streams = {}
        app = json["ingest"]["name"]
        playpath = json["name_seo"]
        i = 0
        id = self._choose_server(json)

        for server in json["server"]:
            name = server["server"]["name"]
            height = str(json["current_video_height"])+"p"

            if id != i:
                height+="_alt_"+name

            streams[height] = RTMPStream(self.session, {
                "rtmp": "rtmp://"+server["server"]["hostname"],
                "app": app,
                "playpath": playpath,
                "pageUrl": self.url,
                "swfUrl": self.SWFURL,
                "live": True
            })
            i += 1


        return streams

    def _get_streams(self):
        if not RTMPStream.is_usable(self.session):
            raise PluginError("rtmpdump is not usable and required by Hashd plugin")
        
        self.logger.debug("Fetching stream info")
        res = urlget(self.url.rstrip("/").lower()+".json?first=true")
        json = res_json(res)

        if not isinstance(json, dict):
            raise PluginError("Invalid JSON response")
        elif not ("live" in json or "file" in json):
            raise PluginError("Invalid JSON response")
     
        if "file" in json:
            streams = self._parse_vod(json)
        elif json["live"]:
            streams = self._parse_live(json)
        else:
            raise NoStreamsError(self.url)
           
        return streams


__plugin__ = Hashd
