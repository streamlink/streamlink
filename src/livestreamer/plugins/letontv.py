from livestreamer import NoStreamsError
import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import RTMPStream

SWF_URL = "http://files.leton.tv/jwplayer.flash.swf"

URL_REGEX = re.compile("""
    http?://(\w+.)?
    (leton.tv/player\.php\?)
    (streampage=)
    (?P<streampage>[^/?&]+)
""", re.VERBOSE)

JS_VAR_A_REGEX = r"var a = ([\d]+);"
JS_VAR_B_REGEX = r"var b = ([\d]+);"
JS_VAR_C_REGEX = r"var c = ([\d]+);"
JS_VAR_D_REGEX = r"var d = ([\d]+);"
JS_VAR_F_REGEX = r"var f = ([\d]+);"
JS_VAR_V_PART_REGEX = r"var v_part = \'/(spull|pull)/([^;]+)\';"


class LetOnTV(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return re.match(URL_REGEX, url)

    def _find_server_ip(self, text):
        """ Decode the server ip stored as JavaScript variables in the stream's page """
        match = re.search(JS_VAR_A_REGEX, text)
        if match:
            var_a = int(match.group(1))
        match = re.search(JS_VAR_B_REGEX, text)
        if match:
            var_b = int(match.group(1))
        match = re.search(JS_VAR_C_REGEX, text)
        if match:
            var_c = int(match.group(1))
        match = re.search(JS_VAR_D_REGEX, text)
        if match:
            var_d = int(match.group(1))
        match = re.search(JS_VAR_F_REGEX, text)
        if match:
            var_f = int(match.group(1))

        if not var_a or not var_b or not var_c or not var_d or not var_f:
            raise NoStreamsError(self.url)

        ip_octets = [str(int(var_a / var_f)), str(int(var_b / var_f)), str(int(var_c / var_f)), str(int(var_d / var_f))]
        ip_delimiter = "."
        server_ip = ip_delimiter.join(ip_octets)

        return server_ip

    def _get_streams(self):
        res = http.get(self.url)

        server_ip = self._find_server_ip(res.text)
        match = re.search(JS_VAR_V_PART_REGEX, res.text)

        if match:
            rtmp_url_postfix = match.group(1)
            playpath = match.group(2)

        if not rtmp_url_postfix or not playpath:
            raise NoStreamsError(self.url)

        streams = {}
        params = {
            "rtmp": "rtmp://{0}/{1}".format(server_ip, rtmp_url_postfix),
            "playpath": playpath,
            "pageUrl": self.url,
            "swfUrl": SWF_URL,
            "live": True
        }

        streams["live"] = RTMPStream(self.session, params)
        return streams


__plugin__ = LetOnTV