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
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.stream import HDSStream, HTTPStream
from livestreamer.utils import (urlget, urlopen, parse_json, parse_xml,
                                parse_qsd, get_node_text)
from livestreamer.options import Options

import hashlib
import json
import re
import requests
import socket
import time
import xml.dom.minidom


class GomTV(Plugin):
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

        self.res = urlget(self.url, session=self.rsession)

        hds = GomTVHDS(self.url, self)
        legacy = GomTVLegacy(self.url, self)
        streams = {}

        if "/vod/" in self.url:
            try:
                streams.update(hds.get_vod_streams())
            except NoStreamsError:
                pass

            if len(streams) == 0:
                streams.update(legacy.get_vod_streams())
        else:
            try:
                streams.update(hds.get_live_streams())
            except NoStreamsError:
                pass

            try:
                streams.update(hds.get_alt_live_streams())
            except NoStreamsError:
                pass

            if len(streams) == 0:
                streams.update(legacy.get_live_streams())

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
            for v in ("SES_USERNO", "SES_STATE", "SES_MEMBERNICK", "SES_USERNICK"):
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
            url = self._parse_event_url(url, res.text)
            res = urlget(url, session=self.rsession)

        return res


class GomTVHDS(GomTV):
    BaseURL = "http://gox.gomtv.net/cgi-bin"
    GOXLiveURL = BaseURL + "/gox_live.cgi"
    GOXVODURL = BaseURL + "/gox_vod.cgi"
    GetUserIPURL = "http://www.gomtv.net/webPlayer/getIP.gom"
    GetStreamURL = "http://www.gomtv.net/live/ajaxGetUrl.gom"

    VODQualityLevels = [65, 60, 6]
    GOXHashKey = "qoaEl"

    Lang = ["ENG", "KOR"]

    def __init__(self, url, parent):
        self.res = parent.res
        self.rsession = parent.rsession

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

        for level in self.VODQualityLevels:
            params = self._create_gox_params(flashvars, level)

            res = urlget(self.GOXVODURL, params=params,
                         session=self.rsession)

            gox = GOXFile(res.text)
            entries = gox.filter_entries("vod")

            for entry in entries:
                try:
                    s = HDSStream.parse_manifest(self.session, entry.ref[0])
                    streams.update(s)
                except IOError:
                    self.logger.warning("Unable to parse manifest")

        if len(streams) == 0:
            self.logger.warning(("Unable to access any streams, "
                                 "make sure you have access to this VOD"))

        return streams

    def get_live_streams(self):
        res = self._get_live_page(self.res)

        match = re.search("flashvars\s+=\s+({.+?});", res.text)

        if not match:
            raise NoStreamsError(self.url)

        flashvars = parse_json(match.group(1), "flashvars JSON")
        flashvars["uip"] = self._get_user_ip()

        levels = re.findall("setFlashLevel\((\d+)\);", res.text)
        streams = {}

        for level in levels:
            params = self._create_gox_params(flashvars, level)

            res = urlget(self.GOXLiveURL, params=params,
                         session=self.rsession)
            gox = GOXFile(res.text)

            for entry in gox.filter_entries("live"):
                try:
                    s = HDSStream.parse_manifest(self.session, entry.ref[0])
                    streams.update(s)
                except IOError:
                    self.logger.warning("Unable to parse manifest")

                break

        return streams

    def get_alt_live_streams(self):
        res = self._get_live_page(self.res)

        match = re.search('jQuery.post\("/live/ajaxGetUrl.gom", ({.+?}),',
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

            res = urlopen(self.GetStreamURL, data=params, session=self.rsession)
            url = unquote(res.text)

            if not urlparse(url).path.endswith(".f4m"):
                continue

            try:
                s = HDSStream.parse_manifest(self.session, url)
                streams.update(s)
            except IOError:
                self.logger.warning("Unable to parse manifest")

        # Hack to rename incorrect bitrate specified by GOM to something
        # more sane.
        for name, stream in streams.items():
            if name == "1k":
                streams["1000k"] = stream
                del streams[name]

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


class GomTVLegacy(GomTV):
    BaseURL = "http://www.gomtv.net"
    GOXURL = BaseURL + "/gox/ggox.gom"

    VODQualityLevels = ["SQ", "HQ"]
    LiveQualityLevels = ["HQ", "HQTest", "SQ", "SQTest"]

    StreamHeaders = {
        "User-Agent": "KPeerClient"
    }

    KeyCheckPort = 63800

    def __init__(self, url, parent):
        self.res = parent.res
        self.rsession = parent.rsession

        GomTV.__init__(self, url)

    def get_vod_streams(self):
        flashvars = re.search("FlashVars=\"(.+?)\"", self.res.text)

        if not flashvars:
            raise NoStreamsError(self.url)

        flashvars = parse_qsd(flashvars.group(1))
        streams = {}

        for strlevel in self.VODQualityLevels:
            params = self._create_gox_params(flashvars, strlevel, "vod")
            res = urlget(self.GOXURL, params=params, session=self.rsession)

            gox = GOXFile(res.text)

            for entry in gox.entries:
                nokey = False

                for attr in ("nodeip", "nodeip", "uno", "userip"):
                    if not hasattr(entry, attr):
                        nokey = True

                if nokey:
                    continue

                try:
                    key = self._check_vod_key(entry.nodeip, entry.nodeid,
                                              entry.uno, entry.userip)
                except PluginError as err:
                    self.logger.warning(err)
                    continue

                streams[strlevel.lower()] = HTTPStream(self.session, entry.ref[0],
                                                       params=dict(key=key),
                                                       headers=self.StreamHeaders)

                break

        if len(streams) == 0:
            self.logger.warning(("Unable to access any streams, "
                                 "make sure you have access to this VOD"))

        return streams

    def get_live_streams(self):
        res = self._get_live_page(self.res)

        match = re.search("this\.playObj = ({.+?})", res.text, re.DOTALL)
        if not match:
            raise NoStreamsError(self.url)

        flashvars = parse_json(match.group(1), "playObj JSON")

        match = re.search("goxkey=([A-z0-9]+)", res.text)
        if not match:
            raise NoStreamsError(self.url)

        flashvars["goxkey"] = match.group(1)
        flashvars["target"] = "live"

        streams = {}

        for strlevel in self.LiveQualityLevels:
            params = self._create_gox_params(flashvars, strlevel, "live")
            res = urlget(self.GOXURL, params=params, session=self.rsession)

            gox = GOXFile(res.text)

            for entry in gox.entries:
                streams[strlevel.lower()] = HTTPStream(self.session, entry.ref[0],
                                                       headers=self.StreamHeaders)

                break

        return streams

    def _create_gox_params(self, flashvars, level, videotype="live"):
        params = dict(strLevel=level, title="", ref="",
                      tmpstamp=int(time.time()))
        keys = ["conid", "leagueid"]

        if videotype == "vod":
            keys += ["vjoinid"]
        elif videotype == "live":
            keys += ["goxkey", "target"]

        for key in keys:
            if not key in flashvars:
                raise PluginError(("Missing key '{0}' in flashvars").format(key))

            params[key] = flashvars[key]

        return params

    def _check_vod_key(self, nodeip, nodeid, userno, userip):
        try:
            conn = socket.create_connection((nodeip, self.KeyCheckPort),
                                            timeout=30)
        except socket.error as err:
            raise PluginError(("Failed to connect to key check server: {0}").format(str(err)))

        msg = "Login,0,{userno},{nodeid},{userip}\n".format(nodeid=nodeid,
                                                            userno=userno,
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

            for entry in dom.getElementsByTagName("ENTRY"):
                entry = GOXFileEntry(entry)
                entries.append(entry)

        return entries


class GOXFileEntry(object):
    def __init__(self, dom):
        self._parse(dom)

    def _parse(self, dom):
        for child in dom.childNodes:
            if isinstance(child, xml.dom.minidom.Element):
                if child.tagName == "REF":
                    href = child.getAttribute("href")

                    if child.hasAttribute("reftype"):
                        reftype = child.getAttribute("reftype")
                    else:
                        reftype = None

                    # Streams can be gomp2p links, with actual stream
                    # URL passed as a parameter
                    if href.startswith("gomp2p://"):
                        href, n = re.subn("^.*LiveAddr=", "", href)
                        href = unquote(href)

                    href = href.replace("&amp;", "&")
                    val = (href, reftype)
                else:
                    val = get_node_text(child)

                attr = child.tagName.lower()
                setattr(self, attr, val)

__plugin__ = GomTV
