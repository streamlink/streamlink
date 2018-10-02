import re
import logging

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class Stadium(Plugin):
    url_re = re.compile(r"""https?://(?:www\.)?watchstadium\.com/live""")
    API_URL = "https://player-api.new.livestream.com/accounts/{account_id}/events/{event_id}/stream_info"
    _stream_data_re = re.compile(r"var StadiumSiteData = (\{.*?});", re.M | re.DOTALL)

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        m = self._stream_data_re.search(res.text)
        if m:
            data = parse_json(m.group(1))
            if data['LivestreamEnabled'] == '1':
                account_id = data['LivestreamArgs']['account_id']
                event_id = data['LivestreamArgs']['event_id']
                log.debug("Found account_id={account_id} and event_id={event_id}".format(account_id=account_id, event_id=event_id))

                url = self.API_URL.format(account_id=account_id, event_id=event_id)
                api_res = self.session.http.get(url)
                api_data = self.session.http.json(api_res)
                stream_url = api_data.get('secure_m3u8_url') or api_data.get('m3u8_url')
                if stream_url:
                    return HLSStream.parse_variant_playlist(self.session, stream_url)
                else:
                    log.error("Could not find m3u8_url")
            else:
                log.error("Stream is offline")


__plugin__ = Stadium
