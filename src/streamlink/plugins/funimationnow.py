import logging
import random
import re

from streamlink.plugin import Plugin, PluginArgument, PluginArguments
from streamlink.plugin.api import useragents, validate
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream, HTTPStream
from streamlink.stream.ffmpegmux import MuxedStream

log = logging.getLogger(__name__)


class Experience:
    CSRF_NAME = "csrfmiddlewaretoken"
    login_url = "https://www.funimation.com/log-in/"
    api_base = "https://www.funimation.com/api"
    login_api_url = "https://prod-api-funimationnow.dadcdigital.com/api/auth/login/"
    show_api_url = api_base + "/experience/{experience_id}/"
    sources_api_url = api_base + "/showexperience/{experience_id}/"
    languages = ["english", "japanese"]
    alphas = ["uncut", "simulcast"]

    login_schema = validate.Schema(validate.any(
        {"success": False,
         "error": validate.text},
        {"token": validate.text,
         "user": {"id": int}}
    ))

    def __init__(self, session, experience_id):
        """
        :param session: streamlink session
        :param experience_id: starting experience_id, may be changed later
        """
        self.session = session
        self.experience_id = experience_id
        self._language = None
        self.cache = {}
        self.token = None

    def request(self, method, url, *args, **kwargs):
        headers = kwargs.pop("headers", {})
        if self.token:
            headers.update({"Authorization": "Token {0}".format(self.token)})
            self.session.http.cookies.update({"src_token": self.token})

        log.debug("Making {0}request to {1}".format("authorized " if self.token else "", url))

        res = self.session.http.request(method, url, *args, headers=headers, **kwargs)
        if "_Incapsula_Resource" in res.text:
            log.error(
                "This page is protected by Incapsula, please see "
                "https://github.com/streamlink/streamlink/issues/2088"
                " for a workaround."
            )
            return
        return res

    def get(self, *args, **kwargs):
        return self.request("GET", *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.request("POST", *args, **kwargs)

    @property
    def pinst_id(self):
        return ''.join([
            random.choice("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(8)
        ])

    def _update(self):
        api_url = self.show_api_url.format(experience_id=self.experience_id)
        log.debug("Requesting experience data: {0}".format(api_url))
        res = self.get(api_url)
        if res:
            data = self.session.http.json(res)
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
        if self.show_info:
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
        res = self.get(api_url, params={"pinst_id": self.pinst_id})
        return self.session.http.json(res)

    def login_csrf(self):
        r = self.session.http.get(self.login_url)
        for input in itertags(r.text, "input"):
            if input.attributes.get("name") == self.CSRF_NAME:
                return input.attributes.get("value")

    def login(self, email, password):
        log.debug("Attempting to login as {0}".format(email))
        r = self.post(self.login_api_url,
                      data={'username': email, 'password': password, self.CSRF_NAME: self.login_csrf()},
                      raise_for_status=False,
                      headers={"Referer": "https://www.funimation.com/log-in/"})
        d = self.session.http.json(r, schema=self.login_schema)
        self.token = d.get("token", None)
        return self.token is not None


class FunimationNow(Plugin):
    arguments = PluginArguments(
        PluginArgument(
            "email",
            argument_name="funimation-email",
            requires=["password"],
            help="Email address for your Funimation account."
        ),
        PluginArgument(
            "password",
            argument_name="funimation-password",
            sensitive=True,
            help="Password for your Funimation account."
        ),
        PluginArgument(
            "language",
            argument_name="funimation-language",
            choices=["en", "ja", "english", "japanese"],
            default="english",
            help="""
            The audio language to use for the stream; japanese or english.

            Default is "english".
            """
        ),
        PluginArgument("mux-subtitles", is_global=True)
    )

    url_re = re.compile(r"""
        https?://(?:www\.)funimation(.com|now.uk)
    """, re.VERBOSE)
    experience_id_re = re.compile(r"/player/(\d+)")
    mp4_quality = "480p"

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        self.session.http.headers = {"User-Agent": useragents.CHROME}
        res = self.session.http.get(self.url)

        # remap en to english, and ja to japanese
        rlanguage = {"en": "english", "ja": "japanese"}.get(self.get_option("language").lower(),
                                                            self.get_option("language").lower())
        if "_Incapsula_Resource" in res.text:
            log.error(
                "This page is protected by Incapsula, please see "
                "https://github.com/streamlink/streamlink/issues/2088"
                " for a workaround."
            )
            return

        if "Out of Territory" in res.text:
            log.error("The content requested is not available in your territory.")
            return

        id_m = self.experience_id_re.search(res.text)
        experience_id = id_m and int(id_m.group(1))
        if experience_id:
            log.debug(f"Found experience ID: {experience_id}")
            exp = Experience(self.session, experience_id)
            if self.get_option("email") and self.get_option("password"):
                if exp.login(self.get_option("email"), self.get_option("password")):
                    log.info(f"Logged in to Funimation as {self.get_option('email')}")
                else:
                    log.warning("Failed to login")

            if exp.episode_info:
                log.debug(f"Found episode: {exp.episode_info['episodeTitle']}")
                log.debug(f"  has languages: {', '.join(exp.episode_info['languages'].keys())}")
                log.debug(f"  requested language: {rlanguage}")
                log.debug(f"  current language:   {exp.language}")
                if rlanguage != exp.language:
                    log.debug(f"switching language to: {rlanguage}")
                    exp.set_language(rlanguage)
                    if exp.language != rlanguage:
                        log.warning(f"Requested language {rlanguage} is not available, continuing with {exp.language}")
                    else:
                        log.debug(f"New experience ID: {exp.experience_id}")

                subtitles = None
                stream_metadata = {}
                disposition = {}
                for subtitle in exp.subtitles():
                    log.debug(f"Subtitles: {subtitle['src']}")
                    if subtitle["src"].endswith(".vtt") or subtitle["src"].endswith(".srt"):
                        sub_lang = {"en": "eng", "ja": "jpn"}[subtitle["language"]]
                        # pick the first suitable subtitle stream
                        subtitles = subtitles or HTTPStream(self.session, subtitle["src"])
                        stream_metadata["s:s:0"] = ["language={0}".format(sub_lang)]
                    stream_metadata["s:a:0"] = ["language={0}".format(exp.language_code)]

                sources = exp.sources()
                if 'errors' in sources:
                    for error in sources['errors']:
                        log.error("{0} : {1}".format(error['title'], error['detail']))
                    return

                for item in sources["items"]:
                    url = item["src"]
                    if ".m3u8" in url:
                        for q, s in HLSStream.parse_variant_playlist(self.session, url).items():
                            if self.get_option("mux_subtitles") and subtitles:
                                yield q, MuxedStream(self.session, s, subtitles, metadata=stream_metadata,
                                                     disposition=disposition)
                            else:
                                yield q, s
                    elif ".mp4" in url:
                        # TODO: fix quality
                        s = HTTPStream(self.session, url)
                        if self.get_option("mux_subtitles") and subtitles:
                            yield self.mp4_quality, MuxedStream(self.session, s, subtitles, metadata=stream_metadata,
                                                                disposition=disposition)
                        else:
                            yield self.mp4_quality, s

        else:
            log.error("Could not find experience ID?!")


__plugin__ = FunimationNow
