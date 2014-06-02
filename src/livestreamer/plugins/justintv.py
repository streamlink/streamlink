import re

from collections import defaultdict

from livestreamer.exceptions import PluginError
from livestreamer.plugin.api import validate

# Import base classes from a support plugin that must exist in the
# same directory as this plugin.
from livestreamer.plugin.api.support_plugin import justintv_common

JustinTVPluginBase = justintv_common.PluginBase
JustinTVAPIBase = justintv_common.APIBase

_url_re = re.compile(r"http(s)?://([\w\.]+)?justin.tv/[^/]+(/[bc]/\d+)?")

_video_schema = validate.Schema(validate.union({
    "archives": validate.all(
        validate.xml_findall("archive"),
        [
            validate.union({
                "length": validate.all(
                    validate.xml_findtext("length"),
                    validate.transform(int),
                ),
                "transcodes": validate.all(
                    validate.xml_find("transcode_file_urls"),
                    validate.xml_findall("*"),
                    validate.map(
                        lambda e: (e.tag.replace("transcode_", ""), e.text)
                    ),
                    validate.transform(dict),
                ),
                "url": validate.xml_findtext("video_file_url")
            }),
        ]
    ),
    validate.optional("restrictions"): validate.xml_findtext(
        "archive_restrictions/restriction"
    ),
    validate.optional("bracket_start"): validate.all(
        validate.xml_findtext("bracket_start"),
        validate.transform(int)
    ),
    validate.optional("bracket_end"): validate.all(
        validate.xml_findtext("bracket_end"),
        validate.transform(int)
    )
}))


def convert_jtv_to_twitch_video(video):
    data = dict(start_offset=video.get("bracket_start", 0),
                end_offset=video.get("bracket_end", 0),
                chunks=defaultdict(list),
                restrictions={})

    total_duration = 0
    for archive in video["archives"]:
        total_duration += archive["length"]
        data["chunks"]["source"].append(archive)

        for name, url in archive["transcodes"].items():
            chunk = dict(url=url, length=archive["length"])
            data["chunks"][name].append(chunk)

    if not data["end_offset"]:
        data["end_offset"] = total_duration

    if video.get("restrictions") == "archives":
        data["restrictions"] = dict((n, "chansub") for n in data["chunks"])

    return data


class JustinTVAPI(JustinTVAPIBase):
    def __init__(self):
        JustinTVAPIBase.__init__(self, host="justin.tv")

    def video_broadcast(self, broadcast_id, **params):
        res = self.call("/api/broadcast/by_archive/{0}".format(broadcast_id),
                        format="xml", **params)
        return res

    def video_clip(self, clip_id, **params):
        res = self.call("/api/broadcast/by_chapter/{0}".format(clip_id),
                        format="xml", **params)
        return res


class JustinTV(JustinTVPluginBase):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def __init__(self, url):
        JustinTVPluginBase.__init__(self, url)

        self.api = JustinTVAPI()

    def _get_video_streams(self):
        try:
            if self.video_type == "b":
                res = self.api.video_broadcast(self.video_id,
                                               schema=_video_schema)
            elif self.video_type == "c":
                res = self.api.video_clip(self.video_id,
                                          schema=_video_schema)
            else:
                return
        except PluginError as err:
            if "404 Client Error" in str(err):
                return
            else:
                raise

        video = convert_jtv_to_twitch_video(res)
        return self._create_playlist_streams(video)

__plugin__ = JustinTV
