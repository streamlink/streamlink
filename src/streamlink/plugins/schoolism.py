from __future__ import print_function

import re
from functools import partial

from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json


class Schoolism(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?schoolism\.com/watchLesson.php")
    login_url = "https://www.schoolism.com/index.php"
    key_time_url = "https://www.schoolism.com/video-html/key-time.php"
    playlist_re = re.compile(r"var allVideos=(\[\{.*\}]);", re.DOTALL)
    js_to_json = partial(re.compile(r'(?!<")(\w+):(?!/)').sub, r'"\1":')
    playlist_schema = validate.Schema(
        validate.transform(playlist_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.transform(js_to_json),
                validate.transform(lambda x: x.replace(",}", "}")),  # remove invalid ,
                validate.transform(parse_json),
                [{
                    "sources": validate.all([{
                        "playlistTitle": validate.text,
                        "title": validate.text,
                        "src": validate.text,
                        "type": validate.text,
                    }],
                        # only include HLS streams
                        validate.filter(lambda s: s["type"] == "application/x-mpegurl")
                    )
                }]
            )
        )
    )

    arguments = PluginArguments(
        PluginArgument(
            "email",
            required=True,
            requires=["password"],
            metavar="EMAIL",
            help="""
        The email associated with your Schoolism account,
        required to access any Schoolism stream.
        """
        ),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="A Schoolism account password to use with --schoolism-email."
        ),
        PluginArgument(
            "part",
            type=int,
            default=1,
            metavar="PART",
            help="""
        Play part number PART of the lesson.

        Defaults is 1.
        """
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def login(self, email, password):
        """
        Login to the schoolism account and return the users account
        :param email: (str) email for account
        :param password: (str) password for account
        :return: (str) users email
        """
        if self.options.get("email") and self.options.get("password"):
            res = http.post(self.login_url, data={"email": email,
                                                  "password": password,
                                                  "redirect": None,
                                                  "submit": "Login"})

            if res.cookies.get("password") and res.cookies.get("email"):
                return res.cookies.get("email")
            else:
                self.logger.error("Failed to login to Schoolism, incorrect email/password combination")
        else:
            self.logger.error("An email and password are required to access Schoolism streams")

    def _get_streams(self):
        user = self.login(self.options.get("email"), self.options.get("password"))
        if user:
            self.logger.debug("Logged in to Schoolism as {0}", user)
            res = http.get(self.url, headers={"User-Agent": useragents.SAFARI_8})
            lesson_playlist = self.playlist_schema.validate(res.text)

            part = self.options.get("part")

            self.logger.info("Attempting to play lesson Part {0}", part)
            found = False

            # make request to key-time api, to get key specific headers
            res = http.get(self.key_time_url, headers={"User-Agent": useragents.SAFARI_8})

            for i, video in enumerate(lesson_playlist, 1):
                if video["sources"] and i == part:
                    found = True
                    for source in video["sources"]:
                        for s in HLSStream.parse_variant_playlist(self.session,
                                                                  source["src"],
                                                                  headers={"User-Agent": useragents.SAFARI_8,
                                                                           "Referer": self.url}).items():
                            yield s

            if not found:
                self.logger.error("Could not find lesson Part {0}", part)


__plugin__ = Schoolism
