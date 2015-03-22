import re
from uuid import uuid4

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import RTMPStream
from livestreamer.compat import urlparse

ITV_PLAYER_USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.107 Safari/537.36'
LIVE_SWF_URL = "http://www.itv.com/mediaplayer/ITVMediaPlayer.swf"
ONDEMAND_SWF_URL = "http://www.itv.com/mercury/Mercury_VideoPlayer.swf"
CHANNEL_MAP = {'itv': 1, 'itv2': 2, 'itv3': 3, 'itv4': 4, 'itvbe': 8, 'citv': 7}
_url_re = re.compile(r"https://(?:www.)?itv.com/itvplayer/(?P<stream>.+)")


class ITVPlayer(Plugin):
    def __init__(self, url):
        Plugin.__init__(self, url)
        match = _url_re.match(url)
        self._stream = match and match.groupdict()["stream"]

    @classmethod
    def can_handle_url(self, url):
        match = _url_re.match(url)
        return match

    @property
    def channel_id(self):
        if self._stream in CHANNEL_MAP:
            return CHANNEL_MAP[self._stream]

    @property
    def production_id(self):
        if self._stream not in CHANNEL_MAP:
            res = http.get(self.url, verify=False)
            production_id_match = re.findall(r'"productionId":"(.*?)",', res.text, flags=re.DOTALL)
            if production_id_match:
                return production_id_match[0]

    def _get_streams(self):
        """
            Find all the streams for the ITV url
            :return: Mapping of quality to stream
        """
        soap_message = self._soap_request()

        headers = {'Content-Length': '{0:d}'.format(len(soap_message)),
                   'Content-Type': 'text/xml; charset=utf-8',
                   'Host': 'mercury.itv.com',
                   'Origin': 'http://www.itv.com',
                   'Referer': 'http://www.itv.com/Mercury/Mercury_VideoPlayer.swf?v=null',
                   'SOAPAction': "http://tempuri.org/PlaylistService/GetPlaylist",
                   'User-Agent': ITV_PLAYER_USER_AGENT,
                   "X-Requested-With": "ShockwaveFlash/16.0.0.305"}

        res = http.post("http://mercury.itv.com/PlaylistService.svc?wsdl",
                        headers=headers,
                        data=soap_message)

        # looking for the <MediaFiles> tag
        xmldoc = http.xml(res)

        mediafiles = xmldoc.find(".//VideoEntries//MediaFiles")
        # No mediafiles, no streams
        if not mediafiles:
            return None

        rtmp = mediafiles.attrib['base']
        streams = {}

        for mediafile in mediafiles.findall("MediaFile"):
            playpath = mediafile.find("URL").text

            rtmp_url = urlparse(rtmp)
            app = (rtmp_url.path[1:] + '?' + rtmp_url.query).rstrip('?')
            live = app == "live"

            params = dict(rtmp="{u.scheme}://{u.netloc}{u.path}".format(u=rtmp_url),
                          app=app.rstrip('?'),
                          playpath=playpath,
                          swfVfy=LIVE_SWF_URL if live else ONDEMAND_SWF_URL,
                          timeout=10)
            if live:
                params['live'] = True

            bitrate = int(mediafile.attrib['bitrate']) / 1000
            quality = "{0}k".format(bitrate)
            streams[quality] = RTMPStream(self.session, params)

        return streams


    def _soap_request(self):

        def sub_ns(parent, tag, ns):
            return ET.SubElement(parent, "{%s}%s" % (ns, tag))

        def sub_common(parent, tag):
            return sub_ns(parent, tag, "http://schemas.itv.com/2009/05/Common")

        def sub_soap(parent, tag):
            return sub_ns(parent, tag, "http://schemas.xmlsoap.org/soap/envelope/")

        def sub_item(parent, tag):
            return sub_ns(parent, tag, "http://tempuri.org/")

        def sub_itv(parent, tag):
            return sub_ns(parent, tag, "http://schemas.datacontract.org/2004/07/Itv.BB.Mercury.Common.Types")

        production_id = self.production_id
        channel_id = self.channel_id

        ET.register_namespace("com", "http://schemas.itv.com/2009/05/Common")
        ET.register_namespace("soapenv", "http://schemas.xmlsoap.org/soap/envelope/")
        ET.register_namespace("tem", "http://tempuri.org/")
        ET.register_namespace("itv", "http://schemas.datacontract.org/2004/07/Itv.BB.Mercury.Common.Types")

        # Start of XML
        root = ET.Element("{http://schemas.xmlsoap.org/soap/envelope/}Envelope")

        sub_soap(root, "Header")
        body = sub_soap(root, "Body")

        # build request
        get_playlist = sub_item(body, "GetPlaylist")
        request = sub_item(get_playlist, "request")
        prode = sub_itv(request, "ProductionId")

        if production_id:
            # request -> ProductionId
            prode.text = production_id

        # request -> RequestGuid
        sub_itv(request, "RequestGuid").text = str(uuid4()).upper()

        vodcrid = sub_itv(request, "Vodcrid")
        # request -> Vodcrid -> Id
        vod_id = sub_common(vodcrid, "Id")
        # request -> Vodcrid -> Partition
        sub_common(vodcrid, "Partition").text = "itv.com"

        if channel_id:
            vod_id.text = "sim{0}".format(channel_id)

        # build userinfo
        userinfo = sub_item(get_playlist, "userInfo")
        sub_itv(userinfo, "Broadcaster").text = "Itv"
        sub_itv(userinfo, "RevenueScienceValue").text = "ITVPLAYER.2.14.1.+build.4a9166f0ba"
        sub_itv(userinfo, "SessionId")
        sub_itv(userinfo, "SsoToken")
        sub_itv(userinfo, "UserToken")
        # GeoLocationToken -> Token
        # sub_itv(sub_itv(userinfo, "GeoLocationToken"), "Token")


        # build siteinfo
        siteinfo = sub_item(get_playlist, "siteInfo")
        sub_itv(siteinfo, "AdvertisingRestriction").text = "None"
        sub_itv(siteinfo, "AdvertisingSite").text = "ITV"
        sub_itv(siteinfo, "AdvertisingType").text = "Any"
        sub_itv(siteinfo,
                "Area").text = "ITVPLAYER.VIDEO"  # "channels.itv{0}".format(channel_id) if channel_id else "ITVPLAYER.VIDEO"
        sub_itv(siteinfo, "Category")
        sub_itv(siteinfo, "Platform").text = "DotCom"
        sub_itv(siteinfo, "Site").text = "ItvCom"

        # build deviceInfo
        deviceinfo = sub_item(get_playlist, "deviceInfo")
        sub_itv(deviceinfo, "ScreenSize").text = "Big"

        # build playerinfo
        playerinfo = sub_item(get_playlist, "playerInfo")
        sub_itv(playerinfo, "Version").text = "2"

        return ET.tostring(root)


__plugin__ = ITVPlayer
