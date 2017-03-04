#!/usr/bin/env python
import re

from streamlink.plugin import Plugin, PluginOptions
from streamlink.plugin.api import http, validate
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream


class TVPlayer(Plugin):
    api_url = "http://api.tvplayer.com/api/v2/stream/live"
    login_url = "https://tvplayer.com/account/login"
    update_url = "https://tvplayer.com/account/update-detail"
    dummy_postcode = "SE1 9LT"  # location of ITV HQ in London

    url_re = re.compile(r"https?://(?:www.)?tvplayer.com/(:?watch/?|watch/(.+)?)")
    stream_attrs_re = re.compile(r'var\s+(validate|platform|resourceId|token)\s+=\s*(.*?);', re.S)
    login_token_re = re.compile(r'input.*?name="token".*?value="(\w+)"')
    stream_schema = validate.Schema({
        "tvplayer": validate.Schema({
            "status": u'200 OK',
            "response": validate.Schema({
                    "stream": validate.url(scheme=validate.any("http")),
                    validate.optional("drmToken"): validate.any(None, validate.text)
                })
            })
        },
        validate.get("tvplayer"),
        validate.get("response"))
    options = PluginOptions({
        "email": None,
        "password": None
    })

    @classmethod
    def can_handle_url(cls, url):
        match = TVPlayer.url_re.match(url)
        return match is not None

    def __init__(self, url):
        super(TVPlayer, self).__init__(url)
        http.headers.update({"User-Agent": useragents.CHROME})

    def authenticate(self, username, password):
        res = http.get(self.login_url)
        match = self.login_token_re.search(res.text)
        token = match and match.group(1)
        res2 = http.post(self.login_url, data=dict(email=username, password=password, token=token),
                         allow_redirects=False)
        # there is a 302 redirect on a successful login
        return res2.status_code == 302

    def _get_streams(self):
        if self.get_option("email") and self.get_option("password"):
            self.authenticate(self.get_option("email"), self.get_option("password"))

        # find the list of channels from the html in the page
        self.url = self.url.replace("https", "http")  # https redirects to http
        res = http.get(self.url)

        if "enter your postcode" in res.text:
            self.logger.info("Setting your postcode to: {0}. "
                             "This can be changed in the settings on tvplayer.com", self.dummy_postcode)
            res = http.post(self.update_url,
                            data=dict(postcode=self.dummy_postcode),
                            params=dict(return_url=self.url))

        stream_attrs = dict((k, v.strip('"')) for k, v in self.stream_attrs_re.findall(res.text))

        if "resourceId" in stream_attrs and "validate" in stream_attrs and "platform" in stream_attrs:
            # get the stream urls
            res = http.post(self.api_url, data=dict(
                service=1,
                id=stream_attrs["resourceId"],
                validate=stream_attrs["validate"],
                platform=stream_attrs["platform"],
                token=stream_attrs.get("token")))

            stream_data = http.json(res, schema=self.stream_schema)

            if stream_data.get("drmToken"):
                self.logger.error("This stream is protected by DRM can cannot be played")
                return
            else:
                return HLSStream.parse_variant_playlist(self.session, stream_data["stream"])
        else:
            if "need to login" in res.text:
                self.logger.error("You need to login using --tvplayer-email/--tvplayer-password to view this stream")


__plugin__ = TVPlayer
