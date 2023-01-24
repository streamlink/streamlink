"""
$description The biggest stream local of streams of Brazil
$url globoplay.com
$type live, vod
$region Brazil

"""

import re
import json
import os
import sys
import requests
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream

class Globoplay(Plugin):
    api_url = "https://api.globoplay.com.br/v2"
    url_re = re.compile(r"https?://(?:www\.)?globoplay\.com\.br/vod/([^/]+)")
    _username = None
    _password = None
    _quality = None
    _language = None

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    @classmethod
    def stream_weight(cls, stream):
        if "auto" in stream:
            return 0
        return 1

    @classmethod
    def argparser(cls):
        parser = super().argparser()
        parser.add_argument("--globoplay-username", dest="globoplay_username",
                            help="The username to use when logging in")
        parser.add_argument("--globoplay-password", dest="globoplay_password",
                            help="The password to use when logging in")
        parser.add_argument("--globoplay-quality", dest="globoplay_quality",
                            help="The video quality to use")
        parser.add_argument("--globoplay-language", dest="globoplay_language",
                            help="The video language to use")
        return parser


    def _get_streams(self):
        match = self.url_re.match(self.url)
        video_id = match.group(1)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0;Win64) AppleWebkit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
        }
        if not self.options.globoplay_username or not self.options.globoplay_password:
            self.logger.error("Username or password not set.")
            return None
        try:
            auth = requests.auth.HTTPBasicAuth(self.options.globoplay_username, self.options.globoplay_password)
            res = http.get(f"{self.api_url}/videos/{video_id}", auth=auth, headers=headers)
            json_data = http.json(res)
            if json_data.get("error") or not json_data.get("playback"):
                return None
            if self.options.globoplay_quality and self.options.globoplay_language:
                json_data = json_data["playback"]
                url = json_data["media"][self.options.globoplay_language][self.options.globoplay_quality]

            if url:
                return HLSStream.parse_variant_playlist(self.session, url)
            else:
                self.logger.error("Could not find a stream for this video")
            return None


    except (requests.HTTPError, requests.ConnectionError) as err:
            self.logger.error("Failed to get stream: {0}".format(err))
            return None



__plugin__ = Globoplay
