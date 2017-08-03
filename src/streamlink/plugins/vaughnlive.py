import random
import re
import itertools
import ssl
import websocket

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, http
from streamlink.stream import RTMPStream

_url_re = re.compile(r"""
    http(s)?://(\w+\.)?
    (?P<domain>vaughnlive|breakers|instagib|vapers|pearltime).tv
    (/embed/video)?
    /(?P<channel>[^/&?]+)
""", re.VERBOSE)


class VLWebSocket(websocket.WebSocket):
    def __init__(self, **_):
        self.session = _.pop("session")
        self.logger = self.session.logger.new_module("plugins.vaughnlive.websocket")
        sslopt = _.pop("sslopt", {})
        sslopt["cert_reqs"] = ssl.CERT_NONE
        super(VLWebSocket, self).__init__(sslopt=sslopt, **_)

    def send(self, payload, opcode=websocket.ABNF.OPCODE_TEXT):
        self.logger.debug("Sending message: {0}", payload)
        return super(VLWebSocket, self).send(payload + "\n\x00", opcode)

    def recv(self):
        d = super(VLWebSocket, self).recv().replace("\n", "").replace("\x00", "")
        return d.split(" ", 1)


class VaughnLive(Plugin):
    api_re = re.compile(r'new sApi\("(#(vl|igb|btv|pt|vtv)-[^"]+)",')
    servers = ["wss://sapi-ws-{0}x{1:02}.vaughnlive.tv".format(x, y) for x, y in itertools.product(range(1, 3),
                                                                                                   range(1, 6))]
    origin = "https://vaughnlive.tv"
    rtmp_server_map = {
        "594140c69edad": "198.255.17.18",
        "585c4cab1bef1": "198.255.17.26",
        "5940d648b3929": "198.255.17.34",
        "5941854b39bc4": "198.255.17.66"}
    name_remap = {"#vl": "live", "#btv": "btv", "#pt": "pt", "#igb": "instagib", "#vtv": "vtv"}

    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def api_url(self):
        return random.choice(self.servers)

    def parse_ack(self, action, message):
        if action.endswith("3"):
            channel, _, viewers, token, server, choked, is_live, chls, trns, ingest = message.split(";")
            is_live = is_live == "1"
            viewers = int(viewers)
            self.logger.debug("Viewers: {0}, isLive={1}", viewers, is_live)
            domain, channel = channel.split("-", 1)
            return is_live, server, domain, channel, token, ingest
        else:
            self.logger.error("Unhandled action format: {0}", action)

    def _get_info(self, stream_name):
        server = self.api_url()
        self.logger.debug("Connecting to API: {0}", server)
        ws = websocket.create_connection(server,
                                         header=["User-Agent: {0}".format(useragents.CHROME)],
                                         origin=self.origin,
                                         class_=VLWebSocket,
                                         session=self.session)
        ws.send("MVN LOAD3 {0}".format(stream_name))
        action, message = ws.recv()
        return self.parse_ack(action, message)

    def _get_rtmp_streams(self, server, domain, channel, token):
        rtmp_server = self.rtmp_server_map.get(server, server)

        url = "rtmp://{0}/live?{1}".format(rtmp_server, token)

        yield "live", RTMPStream(self.session, params={
            "rtmp": url,
            "pageUrl": self.url,
            "playpath": "{0}_{1}".format(self.name_remap.get(domain, "live"), channel),
            "live": True
        })

    def _get_streams(self):
        res = http.get(self.url, headers={"User-Agent": useragents.CHROME})

        m = self.api_re.search(res.text)
        stream_name = m and m.group(1)

        if stream_name:
            is_live, server, domain, channel, token, ingest = self._get_info(stream_name)

            if not is_live:
                self.logger.info("Stream is currently off air")
            else:
                for s in self._get_rtmp_streams(server, domain, channel, token):
                    yield s


__plugin__ = VaughnLive
