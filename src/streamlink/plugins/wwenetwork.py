from __future__ import print_function
import re
from pprint import pprint

import time

from streamlink import PluginError
from streamlink.cache import Cache
from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.compat import urlparse, parse_qsl
from streamlink.stream import HLSStream


class WWENetwork(Plugin):
    url_re = re.compile(r"https?://network.wwe.com")
    content_id_re = re.compile(r'''"content_id" : "(\d+)"''')
    playback_scenario = "HTTP_CLOUD_WIRED"
    login_url = "https://secure.net.wwe.com/workflow.do"
    login_page_url = "https://secure.net.wwe.com/enterworkflow.do?flowId=account.login&forwardUrl=http%3A%2F%2Fnetwork.wwe.com"
    api_url = "https://ws.media.net.wwe.com/ws/media/mf/op-findUserVerifiedEvent/v-2.3"
    _info_schema = validate.Schema(
        validate.union({
            "status": validate.union({
                "code": validate.all(validate.xml_findtext(".//status-code"), validate.transform(int)),
                "message": validate.xml_findtext(".//status-message"),
            }),
            "urls": validate.all(
                validate.xml_findall(".//url"),
                [validate.getattr("text")]
            ),
            validate.optional("fingerprint"): validate.xml_findtext(".//updated-fingerprint"),
            validate.optional("session_key"): validate.xml_findtext(".//session-key"),
            "session_attributes": validate.all(
                validate.xml_findall(".//session-attribute"),
                [validate.getattr("attrib"),
                 validate.union({
                     "name": validate.get("name"),
                     "value": validate.get("value")
                 })]
            )
        })
    )
    arguments = PluginArguments(
        PluginArgument(
            "email",
            required=True,
            metavar="EMAIL",
            requires=["password"],
            help="""
        The email associated with your WWE Network account,
        required to access any WWE Network stream.
        """
        ),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="""
        A WWE Network account password to use with --wwenetwork-email.
        """
        )
    )

    def __init__(self, url):
        super(WWENetwork, self).__init__(url)
        http.headers.update({"User-Agent": useragents.CHROME})
        self._session_attributes = Cache(filename="plugin-cache.json", key_prefix="wwenetwork:attributes")
        self._session_key = self.cache.get("session_key")
        self._authed = self._session_attributes.get("ipid") and self._session_attributes.get("fprt")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def login(self, email, password):
        self.logger.debug("Attempting login as {0}", email)
        # sets some required cookies to login
        http.get(self.login_page_url)
        # login
        res = http.post(self.login_url, data=dict(registrationAction='identify',
                                                  emailAddress=email,
                                                  password=password,
                                                  submitButton=""),
                        headers={"Referer": self.login_page_url},
                        allow_redirects=False)

        self._authed = "Authentication Error" not in res.text
        if self._authed:
            self._session_attributes.set("ipid", res.cookies.get("ipid"), expires=3600 * 1.5)
            self._session_attributes.set("fprt", res.cookies.get("fprt"), expires=3600 * 1.5)

        return self._authed

    def _update_session_attribute(self, key, value):
        if value:
            self._session_attributes.set(key, value, expires=3600 * 1.5)  # 1h30m expiry
            http.cookies.set(key, value)

    @property
    def session_key(self):
        return self._session_key

    @session_key.setter
    def session_key(self, value):
        self.cache.set("session_key", value)
        self._session_key = value

    def _get_media_info(self, content_id):
        """
        Get the info about the content, based on the ID
        :param content_id:
        :return:
        """
        params = {"identityPointId": self._session_attributes.get("ipid"),
                  "fingerprint": self._session_attributes.get("fprt"),
                  "contentId": content_id,
                  "playbackScenario": self.playback_scenario,
                  "platform": "WEB_MEDIAPLAYER_5",
                  "subject": "LIVE_EVENT_COVERAGE",
                  "frameworkURL": "https://ws.media.net.wwe.com",
                  "_": int(time.time())}
        if self.session_key:
            params["sessionKey"] = self.session_key
        url = self.api_url.format(id=content_id)
        res = http.get(url, params=params)
        return http.xml(res, ignore_ns=True, schema=self._info_schema)

    def _get_content_id(self):
        #  check the page to find the contentId
        res = http.get(self.url)
        m = self.content_id_re.search(res.text)
        if m:
            return m.group(1)

    def _get_streams(self):
        email = self.get_option("email")
        password = self.get_option("password")

        if not self._authed and (not email and not password):
            self.logger.error("A login for WWE Network is required, use --wwenetwork-email/"
                              "--wwenetwork-password to set them")
            return

        if not self._authed:
            if not self.login(email, password):
                self.logger.error("Failed to login, check your username/password")
                return

        content_id = self._get_content_id()
        if content_id:
            self.logger.debug("Found content ID: {0}", content_id)
            info = self._get_media_info(content_id)
            if info["status"]["code"] == 1:
                # update the session attributes
                self._update_session_attribute("fprt", info.get("fingerprint"))
                for attr in info["session_attributes"]:
                    self._update_session_attribute(attr["name"], attr["value"])

                if info.get("session_key"):
                    self.session_key = info.get("session_key")
                for url in info["urls"]:
                    for s in HLSStream.parse_variant_playlist(self.session, url, name_fmt="{pixels}_{bitrate}").items():
                        yield s
            else:
                raise PluginError("Could not load streams: {message} ({code})".format(**info["status"]))


__plugin__ = WWENetwork
