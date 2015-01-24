import hashlib
import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HDSStream

_url_re = re.compile("http(s)?://(\w+\.)?wat.tv/")
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1944.9 Safari/537.36"
}

_video_id_re = re.compile("href=\"http://m.wat.tv/video/([^\"]+)", re.IGNORECASE)


class WAT(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        html = http.get(self.url, headers=HTTP_HEADERS).content
        video_id = _video_id_re.search(html).group(1)

        return self.generate_streams('web', video_id) + self.generate_streams('webhd', video_id)

    def generate_streams(self, type, video_id):
        security_url = self.generate_security_url(type, video_id)
        security_response = self.session.http.get(security_url, headers=HTTP_HEADERS)

        url = security_response.content
        cookies = security_response.cookies

        return HDSStream.parse_manifest(self.session, url, headers=HTTP_HEADERS, cookies=cookies).items()

    def generate_security_url(self, type, video_id):
        token = self.generate_security_token(type, video_id)
        return "http://www.wat.tv/get/"+type+"/"+video_id+"?token="+token+"&domain=www.wat.tv&refererURL=wat.tv&revision=04.00.719%0A&synd=0&helios=1&context=playerWat&pub=1&country=FR&sitepage=WAT%2Ftv%2Ft%2Finedit%2Ftf1%2Fparamount_pictures_france&lieu=wat&playerContext=CONTEXT_WAT&getURL=1&version=LNX%2014,0,0,125"

    def generate_security_token(self, type, video_id):
        # Got the secret from the swf with rev number location (tv/wat/player/media/Media.as)
        # use www.showmycode.com or something to decompile the swf
        secret = '9b673b13fa4682ed14c3cfa5af5310274b514c4133e9b3a81e6e3aba009l2564'

        # Get timestamp
        timestamp = int(http.get('http://www.wat.tv/servertime', headers=HTTP_HEADERS).content.split('|')[0])
        timestamp_hex = format(timestamp, 'x').rjust(8, '0')

        # player id
        player_prefix = "/"+type+"/"+video_id

        # Create the token
        token = hashlib.md5((secret + player_prefix) + timestamp_hex).hexdigest() + "/" + timestamp_hex

        return token

__plugin__ = WAT