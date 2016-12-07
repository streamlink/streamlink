import re
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HTTPStream


class NineAnime(Plugin):
    _episode_info_url = "http://9anime.to/ajax/episode/info"

    _info_schema = validate.Schema({
        "grabber": validate.url(),
        "params": {
            "id": validate.text,
            "token": validate.text,
            "options": validate.text,
        }
    })

    _streams_schema = validate.Schema({
        "token": validate.text,
        "error": None,
        "data": [{
            "label": validate.text,
            "file": validate.url(),
            "type": "mp4"
        }]
    })

    _user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "\
                  "Chrome/36.0.1944.9 Safari/537.36"
    _url_re = re.compile(r"https?://9anime.to/watch/(?:[^.]+?\.)(\w+)/(\w+)")

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        match = self._url_re.match(self.url)
        film_id, episode_id = match.groups()

        headers = {
            "Referer": self.url,
            "User-Agent": self._user_agent
        }

        # Get the info about the Episode, including the Grabber API URL
        info_res = http.get(self._episode_info_url,
                            params=dict(update=0, film=film_id, id=episode_id),
                            headers=headers)
        info = http.json(info_res, schema=self._info_schema)

        # Get the data about the streams from the Grabber API
        stream_list_res = http.get(info["grabber"], params=info["params"], headers=headers)
        stream_data = http.json(stream_list_res, schema=self._streams_schema)

        for stream in stream_data["data"]:
            yield stream["label"], HTTPStream(self.session, stream["file"])


__plugin__ = NineAnime
