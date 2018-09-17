import re
import json
from streamlink.plugin import Plugin
from streamlink.stream import HTTPStream, HLSStream

_url_re = re.compile(r"https://egame\.qq\.com/(?P<channel>[^/&?]+)")
_room_json = re.compile(r'EgamePlayer\.Player\(({.*})\);')

STREAM_WEIGHTS = {
	"source": 1080,
	"medium": 720,
	"low": 480
}

class Egame(Plugin):
	@classmethod
	def can_handle_url(cls, url):
		return _url_re.match(url)

	@classmethod
	def stream_weight(cls, stream):
		if stream in STREAM_WEIGHTS:
			return STREAM_WEIGHTS[stream], "egame"
		return Plugin.stream_weight(stream)

	def _get_streams(self):
		match = _url_re.match(self.url)
		channel = match.group("channel")

		res = self.session.http.get(self.url)
		roominfo_text = _room_json.search(res.text).group(1)
		roominfo_json = json.loads(roominfo_text)
		_quality = ['source', 'medium', 'low']

		num_streams = len(roominfo_json['urlArray'])
		for i in range(num_streams):
			if roominfo_json['urlArray'][i]:
				yield _quality[i], HTTPStream(self.session, roominfo_json['urlArray'][i]['playUrl'])
		return

__plugin__ = Egame