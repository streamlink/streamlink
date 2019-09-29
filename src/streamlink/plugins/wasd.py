import logging
import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)

class WASD(Plugin):
	_url_re = re.compile(r"https?://(?:www\.)?wasd\.tv/")
	_url_channel = re.compile(r"https?://(?:www\.)?wasd\.tv/channel/(\d+)")
	_url_video = re.compile(r"https?://(?:www\.)?wasd\.tv/channel/\d+/videos/(\d+)")
	
	@classmethod
	def can_handle_url(cls, url):
		return WASD._url_re.match(url)
		
	def _get_streams(self):
		re_video_id = self._url_video.match(self.url)
		re_channel_id = self._url_channel.match(self.url)
		
		if not re_video_id and not re_channel_id:
			return log.error("Expected to see url like https://wasd.tv/channel/12345 or https://wasd.tv/channel/12345/videos/67890")
		
		# Check if we have AUTH token stored in session cache and request it
		cookies = self.session.http.cookies
		if not cookies or not cookies['cronos-auth-token'] or not cookies['cronos-auth-token-signature']:
			log.debug("There is no AUTH token in cache. Attempting to request one")
			self.getAuthToken()
		if not cookies or not cookies['cronos-auth-token'] or not cookies['cronos-auth-token-signature']:
			return log.error("Failed to get AUTH token")
		
		if re_video_id:
			streams = self.getStreamsFromURL("https://wasd.tv/api/media-containers/" + re_video_id[1], 'video')
		else:
			streams = self.getStreamsFromURL("https://wasd.tv/api/media-containers?media_container_status=RUNNING&limit=1&offset=0&channel_id=" + re_channel_id[1] + "&media_container_type=SINGLE,COOP", 'channel')
		
		if streams:
			for video in streams:
				# TODO: This is how I planned it initially. video[0] is quality and video[1] is URL for .m3u8 file. 
				# But it doesn't work and I can't find channels with more than 1 quality to debug it. So for now it will be copy-pasted code from other plugins
				# yield video[0], HLSStream(self.session, video[1])
				
				# This one is working. But I feel its not how it should be
				return HLSStream.parse_variant_playlist(self.session, video[1])
	
	# WASD.TV requires token to make API requests. We will get it here
	def getAuthToken(self):
		log.debug("Requesting AUTH token for future API requests")
		res = self.session.http.post('https://wasd.tv/api/auth/anon-token')
		
		if not res:
			return None
		if not res.cookies:
			return None
		if not res.cookies['cronos-auth-token']:
			return None
		if not res.cookies['cronos-auth-token-signature']:
			return None
			
		self.save_cookies()
		log.debug("Succesfully got AUTH token")
	
	# type = video / channel. Type of API link 
	def getStreamsFromURL(self, URL, type):
		log.debug("Requesting stream URL: " + URL)
		
		res = self.session.http.get(URL)
		json_res = self.session.http.json(res)
		
		if not json_res:
			return log.error("Server sent empty response for URL: " + URL)
		if not json_res["result"]:
			log.debug("There is no results so we assume no streams available")
			return None
			
		if type == "video":
			return self.getStreamsFromJSON(URL, json_res["result"], type)
		else:
			if not json_res["result"][0]:
				return log.error("Missing result[0] in response from server for URL: " + URL)
			return self.getStreamsFromJSON(URL, json_res["result"][0], type)
		
	def getStreamsFromJSON(self, URL, json, type):
		if not json["user_id"]:
			return log.error("Missing user_id in response from server for URL: " + URL)
		if not json["media_container_streams"]:
			return log.error("Missing media_container_streams in response from server for URL: " + URL)
		if not json["media_container_streams"][0]:
			return log.error("Missing media_container_streams[0] in response from server for URL: " + URL)
		
		user_id = json["user_id"]
		user_container = self.getUserContainerFromArray(user_id, json["media_container_streams"])
		
		if type == "channel" and user_container["stream_status"] != "RUNNING":
			return log.debug("Stream on channel page is not live (recording of last stream?)")
			
		if not user_container["stream_media"]:
			return log.error("stream_media is missing inside container. WASD.TV changed JSON format?")
			
		if not user_container["stream_media"][0]:
			return log.debug("stream_media is empty. No streams available in container?")
			
		return self.getStreamInstancesArray(user_container["stream_media"])
		
	def getUserContainerFromArray(self, user_id, arr):
		for stream in arr:
			if not stream["user_id"]:
				return log.error("Failed to check user_id. WASD.TV changed JSON format?")
			if stream["user_id"] == user_id:
				return stream
		
		return log.error("Failed to find media_container for user_id " + stream["user_id"])
		
	def getStreamInstancesArray(self, media):
		instances = []
		
		for stream in media:
			if stream["media_type"] != "HLS":
				log.error("stream dump: " + stream)
				log.error("Expected to see HLS media_type but got '" + stream["media_type"] + "'. Not supported by plugin, please check updates or report issue")
				continue
			
			if stream["media_status"] == "STOPPED":
				if not stream["media_meta"]["media_archive_url"]:
					log.error("stream dump: " + stream)
					log.error("Expected to see media_archive_url for STOPPED stream but did not found it")
					continue
				else:
					# TODO: convert quality to streamlink format like "1080p"/"1080p60"
					instances.append([ stream["media_meta"]["media_current_resolution"] + "x" + str(stream["media_meta"]["media_current_fps"]) + "fps", stream["media_meta"]["media_archive_url"] ])
			elif stream["media_status"] == "RUNNING":
				if not stream["media_meta"]["media_url"]:
					log.error("stream dump: " + stream)
					log.error("Expected to see media_url for RUNNING stream but did not found it")
					continue
				else:
					# TODO: convert quality to streamlink format like "1080p"/"1080p60"
					instances.append([ stream["media_meta"]["media_current_resolution"] + "x" + str(stream["media_meta"]["media_current_fps"]) + "fps", stream["media_meta"]["media_url"] ])
			else:
				log.error("stream dump: " + stream)
				log.error("Expected media_status to be STOPPED/RUNNING but it was: " + stream["media_status"])
				continue

		return instances
			
__plugin__ = WASD
