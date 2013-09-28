import re

from collections import defaultdict

from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.utils import res_xml, urlget

# Import base class from a support plugin that must exist in the
# same directory as this plugin.
from livestreamer.plugin.api.support_plugin import justintv_common


BROADCAST_URL = "http://api.justin.tv/api/broadcast/by_archive/{0}.xml"
CLIP_URL = "http://api.justin.tv/api/broadcast/by_chapter/{0}.xml"
METADATA_URL = "http://www.justin.tv/meta/{0}.xml?on_site=true"
SWF_URL = "http://www.justin.tv/widgets/live_embed_player.swf"


def convert_video_xml(res):
    dom = res_xml(res)
    data = dict(play_offset=0, start_offset=0, end_offset=0,
                chunks=defaultdict(list), restrictions={})
    total_duration = 0

    for archive in dom.findall("archive"):
        duration = int(archive.findtext("length", 0))
        total_duration += duration

        # Add 'source' chunk
        chunk = dict(url=archive.findtext("video_file_url"),
                     length=duration)
        data["chunks"]["source"].append(chunk)

        # Find transcode chunks
        for transcode in archive.find("transcode_file_urls"):
            match = re.match("transcode_(\w+)", transcode.tag)
            if match:
                name = match.group(1)
                chunk = dict(url=transcode.text,
                             length=duration)
                data["chunks"][name].append(chunk)

    data["play_offset"] = dom.findtext("bracket_start") or 0
    data["start_offset"] = dom.findtext("bracket_start") or 0
    data["end_offset"] = dom.findtext("bracket_end") or total_duration

    restrictions = dom.findtext("archive_restrictions/restriction")
    if restrictions == "archives":
        data["restrictions"] = dict((n, "chansub") for n in data["chunks"])

    return data


class JustinTV(justintv_common.JustinTVBase):
    @classmethod
    def can_handle_url(self, url):
        return "justin.tv" in url

    def _get_metadata(self):
        url = METADATA_URL.format(self.channel)
        cookies = {}

        for cookie in self.options.get("cookie").split(";"):
            try:
                name, value = cookie.split("=")
            except ValueError:
                continue

            cookies[name.strip()] = value.strip()

        res = urlget(url, cookies=cookies)
        meta = res_xml(res, "metadata XML")

        metadata = {}
        metadata["access_guid"] = meta.findtext("access_guid")
        metadata["login"] = meta.findtext("login")
        metadata["title"] = meta.findtext("title")

        return metadata

    def _authenticate(self):
        if self.options.get("cookie"):
            self.logger.info("Attempting to authenticate using cookies")

            try:
                metadata = self._get_metadata()
            except PluginError as err:
                if "404 Client Error" in str(err):
                    raise NoStreamsError(self.url)
                else:
                    raise

            chansub = metadata.get("access_guid")
            login = metadata.get("login")

            if login:
                self.logger.info("Successfully logged in as {0}", login)
            else:
                self.logger.error("Failed to authenticate, your cookies may "
                                  "have expired")

            return chansub

    def _get_desktop_streams(self):
        chansub = self._authenticate()

        self.logger.debug("Fetching desktop streams")
        res = self.usher.find(self.channel,
                              password=self.options.get("password"),
                              channel_subscription=chansub)

        return self._parse_find_result(res, SWF_URL)

    def _get_video_streams(self):
        if self.video_type == "b":
            url = BROADCAST_URL.format(self.video_id)
        elif self.video_type == "c":
            url = CLIP_URL.format(self.video_id)
        else:
            raise NoStreamsError(self.url)

        try:
            res = urlget(url)
        except PluginError as err:
            if "404 Client Error" in str(err):
                raise NoStreamsError(self.url)
            else:
                raise

        videos = convert_video_xml(res)

        return self._create_playlist_streams(videos)

__plugin__ = JustinTV
