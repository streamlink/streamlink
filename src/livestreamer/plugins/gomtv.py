"""
This plugin is derived from https://github.com/sjp/GOMstreamer
and carries the following license.

Copyright 2010 Simon Potter, Tomas Herman
Copyright 2011 Simon Potter
Copyright 2011 Fj (fj.mail@gmail.com)
Copyright 2012 Niall McAndrew (niallm90@gmail.com)
Copyright 2012-2013 Christopher Rosell (chrippa@tanuki.se)

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
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.options import Options
from livestreamer.plugin import Plugin
from livestreamer.stream import HDSStream, HTTPStream, RTMPStream
from livestreamer.utils import (urlget, urlopen, parse_json, parse_xml,
                                res_xml, parse_qsd)

import hashlib
import re
import requests
import socket


class GomTV(Plugin):
    """Implements authentication to the GomTV website."""

    BaseURL = "http://www.gomtv.net"
    LiveURL = BaseURL + "/main/goLive.gom"
    LoginURL = "https://ssl.gomtv.net/userinfo/loginProcess.gom"
    LoginCheckURL = BaseURL + "/forum/list.gom?m=my"

    LoginHeaders = {
        "Referer": BaseURL
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
        self.rsession = requests.session()
        options = self.options

        if options.get("cookie"):
            self._authenticate(cookies=options.get("cookie"))
        else:
            self._authenticate(options.get("username"),
                               options.get("password"))

        res = urlget(self.url, session=self.rsession)
        player = GomTV3(self.url, res, self.rsession)
        streams = {}

        if "/vod/" in self.url:
            return player.get_vod_streams()
        else:
            try:
                streams.update(player.get_hds_live_streams())
            except NoStreamsError:
                pass

            try:
                streams.update(player.get_limelight_live_streams())
            except NoStreamsError:
                pass

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

        if username and password:
            cookie = ""
            for v in ("SES_MEMBERNO", "SES_STATE", "SES_MEMBERNICK", "SES_USERNICK"):
                if v in self.rsession.cookies:
                    cookie += "{0}={1}; ".format(v, self.rsession.cookies[v])

            self.logger.info("Cookie for reusing this session: {0}", cookie)

    def _parse_event_url(self, prefix, data):
        match = re.search(' \"(.*)\";', data)

        if not match:
            raise PluginError("Event live page URL not found")

        return urljoin(prefix, match.group(1))

    def _get_live_page(self, res):
        # If a special event occurs, we know that the live page response
        # will just be some JavaScript that redirects the browser to the
        # real live page. We assume that the entireity of this JavaScript
        # is less than 200 characters long, and that real live pages are
        # more than that.

        if len(res.text) < 200:
            # Grabbing the real live page URL
            url = self._parse_event_url(self.url, res.text)
            res = urlget(url, session=self.rsession)

        return res


class GomTV3(GomTV):
    """Implements concepts and APIs used in the version 0.3.x
       flash player by GomTV."""

    BaseURL = "http://gox.gomtv.net/cgi-bin"
    GOXLiveURL = BaseURL + "/gox_live.cgi"
    GOXVODURL = BaseURL + "/gox_vod_sfile.cgi"
    GetUserIPURL = "http://www.gomtv.net/webPlayer/getIP.gom"
    GetStreamURL = "http://www.gomtv.net/live/ajaxGetUrl.gom"
    GetLimelightStreamURL = "http://www.gomtv.net/live/ajaxGetLimelight.gom"
    LimelightSOAPURL = "http://production.ps.delve.cust.lldns.net/PlaylistService"

    VODQualityLevels = {
        65: "ehq",
        60: "hq",
         6: "sq",
         5: "sq"
    }

    GOXHashKey = "qoaEl"
    VODStreamKeyCheckPort = 63800

    Lang = ["ENG", "KOR"]

    def __init__(self, url, res, rsession):
        self.res = res
        self.rsession = rsession

        GomTV.__init__(self, url)

    def get_vod_streams(self):
        match = re.search("flashvars\s+=\s+({.+?});", self.res.text)

        if not match:
            raise NoStreamsError(self.url)

        flashvars = parse_json(match.group(1), "flashvars JSON")

        match = re.search("var jsonData\s+= eval \((.+?)\);",
                             self.res.text, re.DOTALL)

        if not match:
            raise NoStreamsError(self.url)

        playlists = parse_json(match.group(1), "playlist JSON")

        self.logger.info("Playlist items found:")
        for i, playlist in enumerate(playlists):
            for fvars in playlist:
                if self.url[-1] != "/":
                    url = self.url + "/"
                else:
                    url = self.url

                url = urljoin(url, "?set={1}&lang={0}".format(i,
                              fvars["set"]))

                self.logger.info("[Set {1} ({0})] {2}", self.Lang[i],
                                                        fvars["set"],
                                                        url)

        params = parse_qsd(urlparse(self.url).query)
        currentset = int(params.get("set", "1"))
        lang = int(params.get("lang", "0"))

        flashvars.update(playlists[lang][currentset - 1])
        flashvars["uip"] = self._get_user_ip()

        streams = {}

        for level, levelname in self.VODQualityLevels.items():
            params = self._create_gox_params(flashvars, level)

            res = urlget(self.GOXVODURL, params=params,
                         session=self.rsession)

            gox = GOXFile(res.text)
            entries = gox.filter_entries("vod")

            for entry in entries:
                streamurl = entry.ref[0]
                params = {}

                try:
                    params["key"] = self._create_stream_key(streamurl)
                except PluginError as err:
                    self.logger.warning("{0}", str(err))
                    continue

                streams[levelname] = HTTPStream(self.session, streamurl,
                                                params=params)

        if len(streams) == 0:
            self.logger.warning(("Unable to access any streams, "
                                 "make sure you have access to this VOD"))

        return streams

    def get_hds_live_streams(self):
        res = self._get_live_page(self.res)

        match = re.search('\s+jQuery.post\("/live/ajaxGetUrl.gom", ({.+?}),',
                          res.text)
        if not match:
            raise NoStreamsError(self.url)

        ajaxparams = match.group(1)
        ajaxparams = dict(re.findall("(\w+):(\d+)", ajaxparams))

        levels = re.findall("setFlashLevel\((\d+)\);.+?<span class=\"qtype\">(\w+)</span>", res.text)
        streams = {}

        for level, quality in levels:
            params = ajaxparams.copy()
            params["level"] = level
            quality = quality.lower()

            res = urlopen(self.GetStreamURL, data=params, session=self.rsession)
            url = unquote(res.text)

            if not urlparse(url).path.endswith(".f4m"):
                continue

            try:
                s = HDSStream.parse_manifest(self.session, url)
                if len(s) > 0:
                    bitrate, stream = list(s.items())[0]
                    streams[quality] = stream
            except IOError:
                self.logger.warning("Unable to parse manifest")

        return streams

    def get_limelight_live_streams(self):
        res = self._get_live_page(self.res)

        match = re.search('\s+jQuery.post\("/live/ajaxGetLimelight.gom", ({.+?}),',
                          res.text)

        if not match:
            raise NoStreamsError(self.url)

        ajaxparams = match.group(1)
        ajaxparams = dict(re.findall("(\w+):(\d+)", ajaxparams))

        levels = re.findall("setFlashLevel\((\d+)\);", res.text)
        streams = {}

        for level in levels:
            params = ajaxparams.copy()
            params["level"] = level

            res = urlopen(self.GetLimelightStreamURL, data=params, session=self.rsession)
            url = unquote(res.text)

            if url.startswith("http"):
                continue

            try:
                playlist_entries = self._limelight_soap_playlist_items(url)
                streams.update(playlist_entries)
            except PluginError as err:
                self.logger.warning("Unable to access Limelight playlist: {0}", err)
                continue

        return streams


    def _get_user_ip(self):
        res = urlget(self.GetUserIPURL)

        return res.text

    def _create_gox_params(self, flashvars, level):
        flashvars["adstate"] = "0"
        flashvars["goxkey"] = self.GOXHashKey
        flashvars["level"] = str(level)

        keys = ["leagueid", "conid", "goxkey", "level", "uno", "uip", "adstate"]

        if "playmode" in flashvars and flashvars["playmode"] == "vod":
            keys += ["vjoinid", "nid"]

        goxkey = hashlib.md5()
        params = {}

        for key in keys:
            if not key in flashvars:
                raise PluginError(("Missing key '{0}' in flashvars").format(key))

            goxkey.update(bytes(flashvars[key], "ascii"))
            params[key] = flashvars[key]

        params["goxkey"] = goxkey.hexdigest()

        return params

    def _create_stream_key(self, url):
        parsed = urlparse(url)
        params = parse_qsd(parsed.query)
        keys = ["uno", "nodeid"]

        for key in keys:
            if not key in params:
                raise PluginError(("Missing key '{0}' in key check params").format(key))

        userip = self._get_user_ip()
        nodeip = parsed.netloc

        try:
            conn = socket.create_connection((nodeip, self.VODStreamKeyCheckPort),
                                            timeout=30)
        except socket.error as err:
            raise PluginError(("Failed to connect to key check server: {0}").format(str(err)))

        msg = "Login,0,{userno},{nodeid},{userip}\n".format(nodeid=params["nodeid"],
                                                            userno=params["uno"],
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

    def _limelight_soap_playlist_items(self, channelid):
        payload = """<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
                                         xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                                         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                       <SOAP-ENV:Body>
                         <tns:getPlaylistWithNItemsByChannelId xmlns:tns="http://service.data.media.pluggd.com">
                           <tns:in0>{0}</tns:in0>
                           <tns:in1>0</tns:in1>
                           <tns:in2>7</tns:in2>
                         </tns:getPlaylistWithNItemsByChannelId>
                       </SOAP-ENV:Body>
                     </SOAP-ENV:Envelope>""".format(channelid)

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "Referer": "http://assets.delvenetworks.com/player/loader.swf",
            "x-page-url": self.url
        }

        res = urlopen(self.LimelightSOAPURL, data=payload, headers=headers)
        playlist = res_xml(res)

        streams = {}
        items = playlist.findall(".//*{http://service.data.media.pluggd.com}playlistItems/")

        for item in items:
            streams_ = item.findall("./{http://service.data.media.pluggd.com}streams/")

            for stream in streams_:
                url = stream.findtext("{http://service.data.media.pluggd.com}url")
                height = stream.findtext("{http://service.data.media.pluggd.com}videoHeightInPixels")

                streamname = "{0}p".format(height)
                parsed = urlparse(url)

                if parsed.scheme.startswith("rtmp"):
                    params = dict(rtmp=url, live=True)
                    streams[streamname] = RTMPStream(self.session, params)

        return streams


class GOXFile(object):
    def __init__(self, data):
        self.entries = self._parse(data)

    def filter_entries(self, wanted_reftype):
        entries = []
        for entry in self.entries:
            if not hasattr(entry, "ref"):
                continue

            href, reftype = entry.ref

            if len(href) == 0 or reftype != wanted_reftype:
                continue

            entries.append(entry)

        return entries

    def _parse(self, data):
        entries = []
        errcode = re.search("^(\d+)$", data)
        haserror = errcode or "error.mp4" in data

        if not haserror and len(data) > 0:
            # Fix invalid XML
            data = data.replace("&", "&amp;")
            dom = parse_xml(data, "GOX XML")

            for entry in dom.findall("ENTRY"):
                entry = GOXFileEntry(entry)
                entries.append(entry)

        return entries


class GOXFileEntry(object):
    def __init__(self, dom):
        self._parse(dom)

    def _parse(self, entry):
        for child in entry:
            if child.tag == "REF":
                href = child.attrib.get("href")
                reftype = child.attrib.get("reftype")

                # Streams can be gomp2p links, with actual stream
                # URL passed as a parameter
                if href.startswith("gomp2p://"):
                    href, n = re.subn("^.*LiveAddr=", "", href)
                    href = unquote(href)

                href = href.replace("&amp;", "&")
                val = (href, reftype)
            else:
                val = child.text

            attr = child.tag.lower()
            setattr(self, attr, val)

__plugin__ = GomTV
