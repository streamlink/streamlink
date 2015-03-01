import hashlib
import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HDSStream

# Got the secret from the swf with rev number location
# (tv/wat/player/media/Media.as)
TOKEN_SECRET = '9b673b13fa4682ed14c3cfa5af5310274b514c4133e9b3a81e6e3aba009l2564'

_url_re = re.compile("http(s)?://(\w+\.)?wat.tv/")
_video_id_re = re.compile("href=\"http://m.wat.tv/video/([^\"]+)", re.IGNORECASE)


class WAT(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)
        match = video_id = _video_id_re.search(res.text)
        if not match:
            return

        video_id = match.group(1)

        # TODO: Replace with "yield from" when dropping Python 2.
        for __ in self._create_streams('web', video_id).items():
            yield __

        for __ in self._create_streams('webhd', video_id).items():
            yield __

    def _create_streams(self, type_, video_id):
        url = self._generate_security_url(type_, video_id)
        res = http.get(url)

        return HDSStream.parse_manifest(self.session, res.text, cookies=res.cookies)

    def _generate_security_url(self, type_, video_id):
        token = self._generate_security_token(type_, video_id)

        return ("http://www.wat.tv/get/{type_}/{video_id}?token={token}"
                "&domain=www.wat.tv&refererURL=wat.tv&revision=04.00.719%0A&"
                "synd=0&helios=1&context=playerWat&pub=1&country=FR"
                "&sitepage=WAT%2Ftv%2Ft%2Finedit%2Ftf1%2Fparamount_pictures_"
                "france&lieu=wat&playerContext=CONTEXT_WAT&getURL=1"
                "&version=LNX%2014,0,0,125").format(**locals())

    def _generate_security_token(self, type_, video_id):
        # Get timestamp
        res = http.get('http://www.wat.tv/servertime')
        timestamp = int(res.text.split('|')[0])
        timestamp_hex = format(timestamp, 'x').rjust(8, '0')

        # Player id
        player_prefix = "/{0}/{1}".format(type_, video_id)

        # Create the token
        data = (TOKEN_SECRET + player_prefix + timestamp_hex).encode('utf8')
        token = hashlib.md5(data)
        token = "{0}/{1}".format(token.hexdigest(), timestamp_hex)

        return token

__plugin__ = WAT
