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

from livestreamer.compat import str, bytes, urlparse, urljoin, unquote
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.stream import HTTPStream
from livestreamer.utils import urlget, urlopen
from livestreamer.options import Options

import re
import requests
import xml.dom.minidom

class GomTV(Plugin):
    BaseURL = "http://www.gomtv.net"
    LiveURL = BaseURL + "/main/goLive.gom"
    LoginURL = "https://ssl.gomtv.net/userinfo/loginProcess.gom"
    LoginCheckURL = BaseURL + "/forum/list.gom?m=my"

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

        streams = {}
        qualities = ["HQ", "SQ", "HQTest", "SQTest"]

        res = self._get_live_page(self.url)
        urls = self._find_stream_urls(res.text)

        for quality in qualities:
            for url in urls:
                # Grab the response of the URL listed on the Live page for a stream
                url = url.format(quality=quality)
                res = urlget(url, session=self.rsession)

                # The response for the GOX XML if an incorrect stream quality is chosen is 1002.
                if res.text != "1002" and len(res.text) > 0:
                    streamurl = self._parse_gox_file(res.text)
                    streams[quality.lower()] = HTTPStream(self.session, streamurl,
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

    def _find_stream_urls(self, data):
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

        # Check for multiple streams going at the same time, and extract the conid and the title
        # Those streams have the class "live_now"
        patternlive = '<a\shref=\"/live/index.gom\?conid=(?P<conid>\d+)\"\sclass=\"live_now\"\stitle=\"(?P<title>[^\"]+)'
        streams = re.findall(patternlive, data)

        if len(streams) > 1:
            urls = []
            for stream in streams:
                # Modify the urlFromHTML according to the user
                singleurl = re.sub("conid=\d+", "conid=" + stream[0], url)
                singletitlehtml = "+".join(stream[0].split(" "))
                singleurl = re.sub("title=[\w|.|+]*", "title=" + singletitlehtml, singleurl)
                urls.append(singleurl)

            return urls
        else:
            if url is None:
                return []
            else:
                return [url]

    def _parse_gox_file(self, data):
        # Grabbing the gomcmd URL
        try:
            patternstream = '<REF href="([^"]*)"\s*/>'
            match = re.search(patternstream, data).group(1)
        except AttributeError:
            raise PluginError("Unable to find the gomcmd URL in the GOX XML file")

        match = match.replace("&amp;", "&")
        match = unquote(match)

        # SQ and SQTest streams can be gomp2p links, with actual stream address passed as a parameter.
        if match.startswith("gomp2p://"):
            match, n = re.subn("^.*LiveAddr=", "", match)

        # Cosmetics, getting rid of the HTML entity, we don't
        # need either of the " character or &quot;
        match = match.replace("&quot;", "")

        return match

__plugin__ = GomTV
