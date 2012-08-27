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

from livestreamer.compat import str, bytes, urlencode, urllib, urlparse, cookies, cookiejar
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.stream import HTTPStream
from livestreamer.utils import urlget
from livestreamer.options import Options

import xml.dom.minidom, re

class GomTV(Plugin):
    BaseURL = "http://www.gomtv.net"
    LiveURL = BaseURL + "/main/goLive.gom"
    LoginURL = "https://ssl.gomtv.net/userinfo/loginProcess.gom"
    LoginCheckURL = BaseURL + "/forum/list.gom?m=my"

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
        options = self.options
        # Setting urllib up so that we can store cookies
        self.cookiejar = cookiejar.LWPCookieJar()
        self.opener = urllib.build_opener(urllib.HTTPCookieProcessor(self.cookiejar))

        if options.get("cookie"):
            self.authenticate(cookies=options.get("cookie"))
        else:
            self.authenticate(options.get("username"), options.get("password"))

        streams = {}
        qualities = ["HQ", "SQ", "HQTest", "SQTest"]

        response = self.grabLivePage(self.url)

        for quality in qualities:
            urls = self.parseHTML(response, quality)

            for url in urls:
                # Grab the response of the URL listed on the Live page for a stream
                goxFile = urlget(url, opener=self.opener)

                # The response for the GOX XML if an incorrect stream quality is chosen is 1002.
                if goxFile != b"1002" and len(goxFile) > 0:
                    streamUrl = self.parseStreamURL(goxFile)
                    req = urllib.Request(streamUrl, headers={"User-Agent": "KPeerClient"})
                    streams[quality] = HTTPStream(self.session, req)

        return streams

    def authenticate(self, username=None, password=None, cookies=None):
        if (username is None or password is None) and cookies is None:
            raise PluginError("GOMTV.net Requires a username and password or cookie")


        if cookies is not None:
            for cookie in cookies.split(";"):
                try:
                    name, value = cookie.split("=")
                except ValueError:
                    continue

                c = cookiejar.Cookie(version=0, name=name, value=value,
                                     port=None, port_specified=False, domain="gomtv.net",
                                     domain_specified=False, domain_initial_dot=False, path="/",
                                     path_specified=True, secure=False, expires=None, discard=True,
                                     comment=None, comment_url=None, rest={"HttpOnly": None},
                                     rfc2109=False)
                self.cookiejar.set_cookie(c)
        else:
            values = {
                "cmd": "login",
                "rememberme": "1",
                "mb_username": username,
                "mb_password": password
            }
            data = bytes(urlencode(values), "ascii")
            headers = {"Referer": self.BaseURL}
            request = urllib.Request(self.LoginURL, data, headers)
            urlget(request, opener=self.opener)

        req = urllib.Request(self.LoginCheckURL)
        if b"Please need login" in urlget(req, opener=self.opener):
            raise PluginError("Authentication failed")

    def getEventLivePageURL(self, gomtvLiveURL, response):
        match = re.search(' \"(.*)\";', response)

        if not match:
            raise PluginError("Event Live Page URL not found")

        return urljoin(gomtvLiveURL, match.group(1))

    def grabLivePage(self, gomtvLiveURL):
        response = urlget(gomtvLiveURL, opener=self.opener)

        # If a special event occurs, we know that the live page response
        # will just be some JavaScript that redirects the browser to the
        # real live page. We assume that the entireity of this JavaScript
        # is less than 200 characters long, and that real live pages are
        # more than that.

        if len(response) < 200:
            # Grabbing the real live page URL
            gomtvLiveURL = self.getEventLivePageURL(gomtvLiveURL, response)
            response = urlget(gomtvLiveURL, opener=self.opener)

        return response

    def parseHTML(self, response, quality):
        urlFromHTML = None

        # Parsing through the live page for a link to the gox XML file.
        # Quality is simply passed as a URL parameter e.g. HQ, SQ, SQTest
        try:
            patternHTML = b"[^/]+var.+(http://www.gomtv.net/gox[^;]+;)"
            urlFromHTML = re.search(patternHTML, response).group(1)
            urlFromHTML = re.sub(b'\" \+ playType \+ \"', bytes(quality, "utf8"), urlFromHTML)
        except AttributeError:
            raise PluginError("Unable to find the majority of the GOMtv XML URL on the Live page.")

        # Finding the title of the stream, probably not necessary but
        # done for completeness
        try:
            patternTitle = b"this\.title[^;]+;"
            titleFromHTML = re.search(patternTitle, response).group(0)
            titleFromHTML = re.search(b'\"(.*)\"', titleFromHTML).group(0)
            titleFromHTML = re.sub(b'"', b"", titleFromHTML)
            urlFromHTML = re.sub(b'"\+ tmpThis.title[^;]+;', titleFromHTML, urlFromHTML)
        except AttributeError:
            raise PluginError("Unable to find the stream title on the Live page.")

        # Check for multiple streams going at the same time, and extract the conid and the title
        # Those streams have the class "live_now"
        patternLive = b'<a\shref=\"/live/index.gom\?conid=(?P<conid>\d+)\"\sclass=\"live_now\"\stitle=\"(?P<title>[^\"]+)'
        live_streams = re.findall(patternLive, response)

        if len(live_streams) > 1:
            liveUrls = []
            for stream in live_streams:
                # Modify the urlFromHTML according to the user
                singleUrlFromHTML = re.sub(b"conid=\d+", b"conid=" + stream[0], urlFromHTML)
                singleTitleHTML = b"+".join(stream[0].split(b" "))
                singleUrlFromHTML = re.sub(b"title=[\w|.|+]*", b"title=" + singleTitleHTML, singleUrlFromHTML)
                liveUrls.append(str(singleUrlFromHTML, "utf8"))

            return liveUrls
        else:
            if urlFromHTML is None:
                return []
            else:
                return [str(urlFromHTML, "utf8")]

    def parseStreamURL(self, response):
        # Grabbing the gomcmd URL
        try:
            streamPattern = b'<REF href="([^"]*)"\s*/>'
            regexResult = re.search(streamPattern, response).group(1)
        except AttributeError:
            raise PluginError("Unable to find the gomcmd URL in the GOX XML file.")

        regexResult = str(regexResult, "utf8")
        regexResult = regexResult.replace("&amp;", "&")
        regexResult = urllib.unquote(regexResult)

        # SQ and SQTest streams can be gomp2p links, with actual stream address passed as a parameter.
        if regexResult.startswith("gomp2p://"):
            regexResult, n = re.subn("^.*LiveAddr=", "", regexResult)

        # Cosmetics, getting rid of the HTML entity, we don't
        # need either of the " character or &quot;
        regexResult = regexResult.replace("&quot;", "")

        return regexResult

__plugin__ = GomTV
