import re, json, requests
# import m3u8
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream import HLSStream

@pluginmatcher(re.compile(r'https://chzzk\.naver\.com/live/(?P<channel_id>\w+)'))
class ChzzkPlugin(Plugin):
    API_URL = "https://api.chzzk.naver.com/service/v1/channels/{channel_id}/live-detail"

    def _get_streams(self):
        channel_id = self.match.group("channel_id")
        api_url = self.API_URL.format(channel_id=channel_id)

        try:
            response = requests.get(api_url)
            response.raise_for_status()
        except requests.RequestException as e:
            self.logger.error("Failed to fetch channel information: {0}".format(str(e)))
            return

        if response.status_code == 404:
            self.logger.error("Channel not found")
            return

        try:
            content = response.json().get('content', {})
            status = content.get('status')
            if status != 'OPEN':
                self.logger.error("Channel is not live (status: {0})".format(status))
                return

            live_title = content.get('liveTitle')
            channel_name = content.get('channel', {}).get('channelName')
            category = content.get('liveCategory')
            stream_info = content.get('livePlaybackJson')
            hls_url = json.loads(stream_info).get('media', [{}])[0].get('path')
            # hls = m3u8.loads(hls_url)
            
            # self.logger.info("Stream Title: {0}".format(live_title))
            # self.logger.info("Channel Name: {0}".format(channel_name))
            # self.logger.info("Category: {0}".format(category))
            # self.logger.info("HLS URL: {0}".format(hls_url))
            self.author = channel_name
            self.category = category
            self.title = live_title

            yield from HLSStream.parse_variant_playlist(self.session, hls_url).items()
        except json.JSONDecodeError as e:
            self.logger.error("Failed to decode JSON response: {0}".format(str(e)))
            return
        
__plugin__ = ChzzkPlugin
