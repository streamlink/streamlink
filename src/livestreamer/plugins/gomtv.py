'''
This is derived from https://github.com/sjp/GOMstreamer

and carries the following licence

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

'''
from livestreamer.compat import str, bytes, urlencode
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.stream import HTTPStream
from livestreamer.utils import urlget, urllib
from livestreamer.options import Options

import xml.dom.minidom, re
import cookielib
import Cookie

class GomTV(Plugin):
    options = Options({
        "cookie": None,
        "username": None,
        "password": None,
    })

    @classmethod
    def can_handle_url(self, url):
        return "gomtv.net" in url


    def _get_streams(self):
        options = self.options
        # Setting urllib up so that we can store cookies
        self.cookiejar = cookielib.LWPCookieJar()
        self.opener = urllib.build_opener(urllib.HTTPCookieProcessor(self.cookiejar))

        if options.get("cookie"):
            self.authenticate(cookie=options.get("cookie"))
        else:
            self.authenticate(options.get("username"), options.get("password"))

        streams = {}
        qualities = ["HQ", "SQ", "HQTest", "SQTest"]
        streamChoice = "both"

        response = self.grabLivePage(self.url)

        goxUrls = []
        validGoxFound = False
        failedGoxAll = False
        for quality in qualities:
            urls = self.parseHTML(response, quality)

            for url in urls:
                # Grab the response of the URL listed on the Live page for a stream
                goxFile = urlget(url, opener=self.opener)

                # The response for the GOX XML if an incorrect stream quality is chosen is 1002.
                if (goxFile != '1002' and goxFile != ''):
                    streamUrl = self.parseStreamURL(goxFile)
                    req = urllib.Request(streamUrl, headers={"User-Agent": "KPeerClient"})
                    streams[quality] = HTTPStream(self.session, req)
                    validGoxFound = True

        return streams

    def authenticate(self, username=None, password=None, cookie=None):
        if (username is None or password is None) and cookie is None:
            raise PluginError("GOMTV.net Requires a username and password or cookie")
        
        
        if cookie is not None:
            name,value = cookie.split("=")
    
            c = cookielib.Cookie(version=0, name=name, value=value, 
                                 port=None, port_specified=False, domain='gomtv.net', 
                                 domain_specified=False, domain_initial_dot=False, path='/', 
                                 path_specified=True, secure=False, expires=None, discard=True, 
                                 comment=None, comment_url=None, rest={'HttpOnly': None}, 
                                 rfc2109=False)
            self.cookiejar.set_cookie(c)
        else:
            values = {
                     'cmd': 'login',
                     'rememberme': '1',
                     'mb_username': username,
                     'mb_password': password
                     }
            data = urlencode(values)
            # Now expects to log in only via the website. Thanks chrippa.
            headers = {'Referer': 'http://www.gomtv.net/'}
            request = urllib.Request('https://ssl.gomtv.net/userinfo/loginProcess.gom', data, headers)
            urlget(request, opener=self.opener)
            
        req = urllib.Request('http://www.gomtv.net/forum/list.gom?m=my')
        if 'Please need login' in urlget(req, opener=self.opener):
            raise PluginError("Authentication failed")

        # The real response that we want are the cookies, so returning None is fine.
        return

    def getEventLivePageURL(self, gomtvLiveURL, response):
        match = re.search(' \"(.*)\";', response)
        assert match, 'Event Live Page URL not found'
        return urljoin(gomtvLiveURL, match.group(1))

    def getSeasonURL(self, gomtvURL):
        # Getting season url from the 'Go Live!' button on the main page.
        match = re.search('.*liveicon"><a href="([^"]*)"', urlget(gomtvURL, opener=self.opener))
        assert match, 'golive_btn href not found'
        return match.group(1)

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
            patternHTML = r'[^/]+var.+(http://www.gomtv.net/gox[^;]+;)'
            urlFromHTML = re.search(patternHTML, response).group(1)
            urlFromHTML = re.sub(r'\" \+ playType \+ \"', quality, urlFromHTML)
        except AttributeError:
            pass

        # Finding the title of the stream, probably not necessary but
        # done for completeness
        try:
            patternTitle = r'this\.title[^;]+;'
            titleFromHTML = re.search(patternTitle, response).group(0)
            titleFromHTML = re.search(r'\"(.*)\"', titleFromHTML).group(0)
            titleFromHTML = re.sub(r'"', '', titleFromHTML)
            urlFromHTML = re.sub(r'"\+ tmpThis.title[^;]+;', titleFromHTML, urlFromHTML)
        except AttributeError:
            pass

        # Check for multiple streams going at the same time, and extract the conid and the title
        # Those streams have the class "live_now"
        patternLive = r'<a\shref=\"/live/index.gom\?conid=(?P<conid>\d+)\"\sclass=\"live_now\"\stitle=\"(?P<title>[^\"]+)'
        live_streams = re.findall(patternLive, response)

        if len(live_streams) > 1:
            liveUrls = []
            options = range(len(live_streams))
            for i in options:
                # Modify the urlFromHTML according to the user
                singleUrlFromHTML = re.sub(r'conid=\d+', 'conid=' + live_streams[i][0], urlFromHTML)
                singleTitleHTML = '+'.join(live_streams[i][1].split(' '))
                singleUrlFromHTML = re.sub(r'title=[\w|.|+]*', 'title=' + singleTitleHTML, singleUrlFromHTML)
                liveUrls.append(singleUrlFromHTML)
            return liveUrls
        else:
            if urlFromHTML is None:
                return []
            else:
                return [urlFromHTML]

    def parseStreamURL(self, response):
        # Grabbing the gomcmd URL
        try:
            streamPattern = r'<REF href="([^"]*)"\s*/>'
            regexResult = re.search(streamPattern, response).group(1)
        except AttributeError:
            return None

        regexResult = urllib.unquote(regexResult)
        regexResult = re.sub(r'&amp;', '&', regexResult)
        # SQ and SQTest streams can be gomp2p links, with actual stream address passed as a parameter.
        if regexResult.startswith('gomp2p://'):
            regexResult, n = re.subn(r'^.*LiveAddr=', '', regexResult)
        # Cosmetics, getting rid of the HTML entity, we don't
        # need either of the " character or &quot;
        regexResult = regexResult.replace('&quot;', '')
        return regexResult

__plugin__ = GomTV
