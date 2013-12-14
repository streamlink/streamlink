import re

from collections import defaultdict

from livestreamer.exceptions import PluginError

# Import base classes from a support plugin that must exist in the
# same directory as this plugin.
from livestreamer.plugin.api.support_plugin import justintv_common

JustinTVPluginBase = justintv_common.PluginBase
JustinTVAPIBase = justintv_common.APIBase


def convert_video_xml(dom):
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


class JustinTVAPI(JustinTVAPIBase):
    def __init__(self):
        JustinTVAPIBase.__init__(self, host="justin.tv")

    def video_broadcast(self, broadcast_id):
        res = self.call("/api/broadcast/by_archive/{0}".format(broadcast_id),
                        format="xml")
        return res

    def video_clip(self, clip_id):
        res = self.call("/api/broadcast/by_chapter/{0}".format(clip_id),
                        format="xml")
        return res


class JustinTV(JustinTVPluginBase):
    @classmethod
    def can_handle_url(self, url):
        return "justin.tv" in url

    def __init__(self, url):
        JustinTVPluginBase.__init__(self, url)

        self.api = JustinTVAPI()

    def _get_video_streams(self):
        try:
            if self.video_type == "b":
                res = self.api.video_broadcast(self.video_id)
            elif self.video_type == "c":
                res = self.api.video_clip(self.video_id)
            else:
                return
        except PluginError as err:
            if "404 Client Error" in str(err):
                return
            else:
                raise

        videos = convert_video_xml(res)

        return self._create_playlist_streams(videos)

__plugin__ = JustinTV
