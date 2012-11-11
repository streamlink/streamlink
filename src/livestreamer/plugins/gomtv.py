"""
This plugin is derived from https://github.com/sjp/GOMstreamer
and carries the following license.

Copyright 2010 Simon Potter, Tomas Herman
Copyright 2011 Simon Potter
Copyright 2011 Fj (fj.mail@gmail.com)
Copyright 2012 Niall McAndrew (niallm90@gmail.com)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

from livestreamer.compat import str, bytes, urlparse, urljoin, unquote, parse_qs
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.stream import HTTPStream
from livestreamer.utils import urlget, urlopen
from livestreamer.options import Options

import socket
import re
import requests
import time
import xml.dom.minidom

class GomTV(Plugin):
    BaseURL = "http://www.gomtv.net"
    LiveURL = BaseURL + "/main/goLive.gom"
    LoginURL = "https://ssl.gomtv.net/userinfo/loginProcess.gom"
    LoginCheckURL = BaseURL + "/forum/list.gom?m=my"
    GOXVODURL = BaseURL + "/gox/ggox.gom"
    KeyCheckPort = 63800

    LoginHeaders = {
        "Referer": BaseURL
    }

    StreamHeaders = {
        "User-Agent": "KPeerClient"
    }

    options = Options({
        "cookie": None,
        "username": None,
        "password": None,
    })

    @classmethod
    def can_handle_url(self, url):
        return "gomtv.net" in url

    def __init__(self, url):
        parsed = urlparse(url)

        # Attempt to resolve current live URL if main page is passed
        if len(parsed.path) <= 1:
            url = self.LiveURL

        Plugin.__init__(self, url)

    def _get_streams(self):
        self.rsession = requests.session(prefetch=True)

        options = self.options
        if options.get("cookie"):
            self._authenticate(cookies=options.get("cookie"))
        else:
            self._authenticate(options.get("username"), options.get("password"))

        if "/vod/" in self.url:
            return self._get_vod_streams()
        else:
            return self._get_live_streams()

    def _get_vod_streams(self):
        res = urlget(self.url)
        flashvars = re.search("FlashVars=\"(.+?)\"", res.text)

        if not flashvars:
            raise PluginError("Unable to find flashvars on page")

        flashvars = parse_qs(flashvars.group(1))
        for var in ("vjoinid", "conid", "leagueid"):
            if not var in flashvars:
                raise PluginError(("Missing key '{0}' in flashvars").format(var))

        streams = {}
        qualities = ["SQ", "HQ"]

        for quality in qualities:
            params = dict(leagueid=flashvars["leagueid"][0], vjoinid=flashvars["vjoinid"][0],
                          conid=flashvars["conid"][0], title="", ref="",
                          tmpstamp=int(time.time()), strLevel=quality)
            res = urlget(self.GOXVODURL, params=params, session=self.rsession)

            if res.text != "1002" and len(res.text) > 0:
                gox = self._parse_gox_file(res.text)
                entry = gox[0]

                nokey = False
                for var in ("NODEIP", "NODEID", "UNO", "USERIP"):
                    if not var in entry:
                        nokey = True

                if nokey:
                    self.logger.warning("Unable to fetch key, make sure that you have access to this VOD")
                    continue

                key = self._check_vod_key(entry["NODEIP"], entry["NODEID"], entry["UNO"],
                                          entry["USERIP"])

                streams[quality.lower()] = HTTPStream(self.session, gox[0]["REF"],
                                                      params=dict(key=key),
                                                      headers=self.StreamHeaders)


        return streams


    def _get_live_streams(self):
        streams = {}
        qualities = ["HQ", "SQ", "HQTest", "SQTest"]

        res = self._get_live_page(self.url)
        goxurl = self._find_gox_url(res.text)

        if not goxurl:
            raise PluginError("Unable to find GOX URL")

        for quality in qualities:
            # Grab the response of the URL listed on the Live page for a stream
            url = goxurl.format(quality=quality)
            res = urlget(url, session=self.rsession)

            # The response for the GOX XML if an incorrect stream quality is chosen is 1002.
            if res.text != "1002" and len(res.text) > 0:
                gox = self._parse_gox_file(res.text)
                streams[quality.lower()] = HTTPStream(self.session, gox[0]["REF"],
                                                      headers=self.StreamHeaders)


        return streams

    def _authenticate(self, username=None, password=None, cookies=None):
        if (username is None or password is None) and cookies is None:
            raise PluginError("GOMTV.net requires a username and password or a cookie")

        if cookies is not None:
            for cookie in cookies.split(";"):
                try:
                    name, value = cookie.split("=")
                except ValueError:
                    continue

                self.rsession.cookies[name.strip()] = value.strip()

            self.logger.info("Attempting to authenticate with cookies")
        else:
            form = dict(cmd="login", rememberme="1",
                        mb_username=username,
                        mb_password=password)

            self.logger.info("Attempting to authenticate with username and password")

            urlopen(self.LoginURL, data=form, headers=self.LoginHeaders,
                    session=self.rsession)

        res = urlget(self.LoginCheckURL, session=self.rsession)

        if "Please need login" in res.text:
            raise PluginError("Authentication failed")

        if "SES_USERNICK" in self.rsession.cookies:
            username = self.rsession.cookies["SES_USERNICK"]
            self.logger.info(("Successfully logged in as {0}").format(username))

    def _check_vod_key(self, nodeip, nodeid, userno, userip):
        try:
            conn = socket.create_connection((nodeip, self.KeyCheckPort), timeout=15)
        except socket.error as err:
            raise PluginError(("Failed to connect to key check server: {0}").format(str(err)))

        msg = "Login,0,{userno},{nodeid},{userip}\n".format(nodeid=nodeid, userno=userno,
                                                          userip=userip)

        try:
            conn.sendall(bytes(msg, "ascii"))
            res = conn.recv(4096)
        except IOError as err:
            raise PluginError(("Failed to communicate with key check server: {0}").format(str(err)))

        if len(res) == 0:
            raise PluginError("Empty response from key check server")

        conn.close()

        res = str(res, "ascii").strip().split(",")

        return res[-1]

    def _get_event_url(self, prefix, data):
        match = re.search(' \"(.*)\";', data)

        if not match:
            raise PluginError("Event live page URL not found")

        return urljoin(prefix, match.group(1))

    def _get_live_page(self, url):
        res = urlget(url, session=self.rsession)

        # If a special event occurs, we know that the live page response
        # will just be some JavaScript that redirects the browser to the
        # real live page. We assume that the entireity of this JavaScript
        # is less than 200 characters long, and that real live pages are
        # more than that.

        if len(res.text) < 200:
            # Grabbing the real live page URL
            url = self._parse_event_url(url, res.text)
            res = urlget(url, session=self.rsession)

        return res

    def _find_gox_url(self, data):
        url = None

        # Parsing through the live page for a link to the gox XML file.
        # Quality is simply passed as a URL parameter e.g. HQ, SQ, SQTest
        try:
            patternhtml = "[^/]+var.+(http://www.gomtv.net/gox[^;]+;)"
            url = re.search(patternhtml, data).group(1)
            url = re.sub('\" \+ playType \+ \"', "{quality}", url)
        except AttributeError:
            raise PluginError("Unable to find the majority of the GOMTV.net XML URL on the Live page")

        # Finding the title of the stream, probably not necessary but
        # done for completeness
        try:
            patterntitle = "this\.title[^;]+;"
            title = re.search(patterntitle, data).group(0)
            title = re.search('\"(.*)\"', title).group(0)
            title = re.sub('"', "", title)
            url = re.sub('"\+ tmpThis.title[^;]+;', title, url)
        except AttributeError:
            raise PluginError("Unable to find the stream title on the Live page")

        return url

    def _get_node_text(self, element):
        res = []
        for node in element.childNodes:
            if node.nodeType == node.TEXT_NODE:
                res.append(node.data)

        if len(res) == 0:
            return None
        else:
            return "".join(res)

    def _parse_gox_file(self, data):
        try:
            dom = xml.dom.minidom.parseString(data)
        except Exception as err:
            raise PluginError(("Unable to parse gox file: {0})").format(err))

        entries = []

        for xentry in dom.getElementsByTagName("ENTRY"):
            entry = {}
            for child in xentry.childNodes:
                if isinstance(child, xml.dom.minidom.Element):
                    if child.tagName == "REF":
                        href = child.getAttribute("href")

                        # SQ and SQTest streams can be gomp2p links, with actual stream address passed as a parameter.
                        if href.startswith("gomp2p://"):
                            href, n = re.subn("^.*LiveAddr=", "", href)
                            href = unquote(href)

                        entry[child.tagName] = href
                    else:
                        entry[child.tagName] = self._get_node_text(child)

            entries.append(entry)

        return entries

__plugin__ = GomTV
