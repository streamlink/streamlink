from __future__ import print_function

import random
import re

from streamlink.plugin import Plugin, PluginOptions
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream
from streamlink.stream import HTTPStream
from streamlink.stream.ffmpegmux import MuxedStream


class Experience(object):
    api_base = "https://prod-api-funimationnow.dadcdigital.com/api"
    show_api_url = api_base+"/source/catalog/title/experience/{experience_id}/"
    sources_api_url = api_base+"/source/catalog/video/{experience_id}/signed/"
    languages = ["english", "japanese"]
    alphas = ["uncut", "simulcast"]

    def __init__(self, experience_id):
        """
        :param experience_id: starting experience_id, may be changed later
        """
        self.experience_id = experience_id
        self._language = None
        self.cache = {}

    @property
    def pinst_id(self):
        return ''.join([
            random.choice("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(8)
        ])

    def _update(self):
        api_url = self.show_api_url.format(experience_id=self.experience_id)
        res = http.get(api_url)
        data = http.json(res)
        self.cache[self.experience_id] = data

    @property
    def show_info(self):
        if self.experience_id not in self.cache:
            self._update()
        return self.cache.get(self.experience_id)

    @property
    def episode_info(self):
        """
        Search for the episode with the requested experience Id
        :return:
        """
        for season in self.show_info["seasons"]:
            for episode in season["episodes"]:
                for lang in episode["languages"].values():
                    for alpha in lang["alpha"].values():
                        if alpha["experienceId"] == self.experience_id:
                            return episode

    @property
    def language(self):
        for language, lang_data in self.episode_info["languages"].items():
            for alpha in lang_data["alpha"].values():
                if alpha["experienceId"] == self.experience_id:
                    return language

    @property
    def language_code(self):
        return {"english": "eng", "japanese": "jpn"}[self.language]

    def set_language(self, language):
        if language in self.episode_info["languages"]:
            for alpha in self.episode_info["languages"][language]["alpha"].values():
                self.experience_id = alpha["experienceId"]

    def _get_alpha(self):
        for lang_data in self.episode_info["languages"].values():
            for alpha in lang_data["alpha"].values():
                if alpha["experienceId"] == self.experience_id:
                    return alpha

    def subtitles(self):
        alpha = self._get_alpha()
        for src in alpha["sources"]:
            return src["textTracks"]

    def sources(self):
        """
        Get the sources for a given experience_id, which is tied to a specific language
        :param experience_id: int; video content id
        :return: sources dict
        """
        api_url = self.sources_api_url.format(experience_id=self.experience_id)
        res = http.get(api_url, params=dict(pinstId=self.pinst_id))
        return http.json(res)


class FunimationNow(Plugin):
    options = PluginOptions({
        "language": "english",
        "mux_subtitles": False
    })
    url_re = re.compile(r"""
        https?://(?:www\.)funimation(.com|now.uk)
    """, re.VERBOSE)
    experience_id_re = re.compile(r"/player/(\d+)")
    mp4_quality = "480p"

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        http.headers = {"User-Agent": useragents.CHROME}
        res = http.get(self.url)

        rlanguage = self.get_option("language")

        id_m = self.experience_id_re.search(res.text)
        experience_id = id_m and int(id_m.group(1))
        if experience_id:
            self.logger.debug("Found experience ID: {0}", experience_id)
            exp = Experience(experience_id)

            self.logger.debug("Found episode: {0}", exp.episode_info["episodeTitle"])
            self.logger.debug("  has languages: {0}", ", ".join(exp.episode_info["languages"].keys()))
            self.logger.debug("  requested language: {0}", rlanguage)
            self.logger.debug("  current language:   {0}", exp.language)
            if rlanguage != exp.language:
                self.logger.debug("switching language to: {0}", rlanguage)
                exp.set_language(rlanguage)
                if exp.language != rlanguage:
                    self.logger.warning("Requested language {0} is not available, continuing with {1}",
                                        rlanguage, exp.language)
                else:
                    self.logger.debug("New experience ID: {0}", exp.experience_id)

            subtitles = None
            stream_metadata = {}
            disposition = {}
            for subtitle in exp.subtitles():
                self.logger.info("Subtitles: {0}", subtitle["src"])
                if subtitle["src"].endswith(".vtt") or subtitle["src"].endswith(".srt"):
                    sub_lang = {"en": "eng", "ja": "jpn"}[subtitle["language"]]
                    # pick the first suitable subtitle stream
                    subtitles = subtitles or HTTPStream(self.session, subtitle["src"])
                    stream_metadata["s:s:0"] = ["language={0}".format(sub_lang)]
                stream_metadata["s:a:0"] = ["language={0}".format(exp.language_code)]

            for item in exp.sources()["items"]:
                url = item["src"]
                if ".m3u8" in url:
                    for q, s in HLSStream.parse_variant_playlist(self.session, url).items():
                        if self.get_option("mux_subtitles") and subtitles:
                            yield q, MuxedStream(self.session, s, subtitles, metadata=stream_metadata, disposition=disposition)
                        else:
                            yield q, s
                elif ".mp4" in url:
                    # TODO: fix quality
                    s = HTTPStream(self.session, url)
                    if self.get_option("mux_subtitles") and subtitles:
                        yield self.mp4_quality, MuxedStream(self.session, s, subtitles, metadata=stream_metadata, disposition=disposition)
                    else:
                        yield self.mp4_quality, s

        else:
            self.logger.error("Could not find experience ID?!")

__plugin__ = FunimationNow
