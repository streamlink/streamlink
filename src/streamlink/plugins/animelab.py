import logging
import re

from streamlink.plugin import Plugin, PluginArgument, PluginArguments
from streamlink.plugin.api import validate
from streamlink.stream import HTTPStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class AnimeLab(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?animelab\.com/player/")
    login_url = "https://www.animelab.com/login"
    video_collection_re = re.compile(r"VideoCollection\((\[.*?\])\);")
    playlist_position_re = re.compile(r"playlistPosition\s*=\s*(\d+);")
    video_collection_schema = validate.Schema(
        validate.union({
            "position": validate.all(
                validate.transform(playlist_position_re.search),
                validate.any(
                    None,
                    validate.all(validate.get(1), validate.transform(int))
                )
            ),
            "playlist": validate.all(
                validate.transform(video_collection_re.search),
                validate.any(
                    None,
                    validate.all(
                        validate.get(1),
                        validate.transform(parse_json)
                    )
                )
            )
        })
    )
    arguments = PluginArguments(
        PluginArgument(
            "email",
            requires=["password"],
            metavar="EMAIL",
            help="The email address used to register with animelab.com."
        ),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="A animelab.com account password to use with --animelab-email."
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def login(self, email, password):
        log.debug("Attempting to log in as {0}".format(email))
        res = self.session.http.post(
            self.login_url,
            data=dict(email=email, password=password),
            allow_redirects=False,
            raise_for_status=False
        )
        loc = res.headers.get("Location", "")
        if "geoblocked" in loc.lower():
            log.error("AnimeLab is not available in your territory")
        elif res.status_code >= 400:
            log.error("Failed to login to AnimeLab, check your email/password combination")
        else:
            return True

        return False

    def _get_streams(self):
        email, password = self.get_option("email"), self.get_option("password")
        if not email or not password:
            log.error("AnimeLab requires authentication, use --animelab-email "
                      "and --animelab-password to set your email/password combination")
            return

        if self.login(email, password):
            log.info(f"Successfully logged in as {email}")
            video_collection = self.session.http.get(self.url, schema=self.video_collection_schema)
            if video_collection["playlist"] is None or video_collection["position"] is None:
                return

            data = video_collection["playlist"][video_collection["position"]]

            log.debug("Found {0} version {1} hard-subs".format(
                data["language"]["name"],
                "with" if data["hardSubbed"] else "without"
            ))

            for video in data["videoInstances"]:
                if video["httpUrl"]:
                    q = video["videoQuality"]["description"]
                    s = HTTPStream(self.session, video["httpUrl"])
                    yield q, s


__plugin__ = AnimeLab
