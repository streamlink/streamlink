"""Plugin for Dplay service."""

import re
import time

from streamlink.compat import quote
from streamlink.exceptions import PluginError, NoStreamsError
from streamlink.plugin import Plugin
from streamlink.plugin.api import StreamMapper, http, validate
from streamlink.stream import HLSStream, HDSStream

# Interface URLs for Dplay
GENERAL_API_URL = 'http://www.{0}/api/v2/ajax/videos?video_id={1}'
STREAM_API_URL = 'https://secure.{0}/secure/api/v2/user/authorization/stream/{1}?stream_type={2}'
GEO_DATA_URL = 'http://geo.{0}/geo.js'
SWF_URL = 'http://player.{0}/4.3.5/swf/AkamaiAdvancedFlowplayerProvider_v3.8.swf'

# User-agent to use for http requests
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.82 Safari/537.36'

# Regular expressions for matching URL and video ID
_url_re = re.compile (r'(?:http(s)?://)?www.(?P<domain>dplay.se|dplay.no|dplay.dk)/')
_videoid_re = re.compile (r'data-video-id="(?P<id>[^"]+)')

# Validation schemas
# ------------------
_api_schema = validate.Schema (
    {
        "data": validate.any (
            None,
            [{
                "video_metadata_drmid_playready": validate.text,
                "video_metadata_drmid_flashaccess": validate.text,
                "content_info": validate.all (
                    {
                        "package_label": validate.all (
                            {
                                "value": validate.text
                            })
                    })
            }])
    }
)
_media_schema = validate.Schema (
    validate.any (
        None,
        { "hls": validate.text },
        { "hds": validate.text },
        {
            "hls": validate.text,
            "hds": validate.text
        }
    )
)
_geo_schema = validate.Schema (
    {
        "countryCode": validate.text
    },
    validate.get ("countryCode")
)
# ------------------

class Dplay (Plugin):
    @classmethod
    def can_handle_url (cls, url):
        return _url_re.match (url)

    # Returns true if stream is playable (i.e. non-premium & not drm-protected)
    def _is_playable (self, data):
        if data['data'][0]['video_metadata_drmid_playready'] != 'none':
            return False
        if data['data'][0]['video_metadata_drmid_playready'] != 'none':
            return False
        if data['data'][0]['content_info']['package_label']['value'] == 'Premium':
            return False
        return True

    # Parses streams
    def _create_streams (self, parser, stream):
        try:
            if stream['format'] == 'hds':
                streams = parser (self.session, stream['url'],
                                  params = {'hdcore': '3.8.0'},
                                  pvswf = SWF_URL.format (self.domain))
            else:
                streams = parser (self.session, stream['url'])
            return streams.items ()
        except IOError as err:
            self.logger.error ('Failed to extract {0} streams: {1}',
                               stream['format'].upper (), err)

    # Assembles available streams
    def _get_streams (self):
        # Get domain name
        self.domain = _url_re.match (self.url).group ('domain')
        
        # Set header data for user-agent
        hdr = {'User-Agent': USER_AGENT.format('sv_SE')}
        
        # Parse video ID from data received from supplied URL
        res = http.get (self.url, headers=hdr).text
        match = _videoid_re.search (res)
        if not match:   # Video ID not found
            self.logger.error ('Failed to parse video ID')
            return {}
        videoId = match.group ('id')
        
        # Get data from general API to validate that stream is playable
        res = http.get (GENERAL_API_URL.format (self.domain, videoId), headers=hdr)
        data = http.json (res, schema=_api_schema)
        if not data['data']:                # No data item found
            self.logger.error ('Unable to find "data" item in general API response')
            return {}
        if not self._is_playable (data):    # Stream not playable
            self.logger.error ('Stream is not playable (Premium or DRM-protected content)')
            return {}
        
        # Get geo data, validate and form cookie consisting of
        # geo data + expiry timestamp (current time + 1 hour)
        res = http.get (GEO_DATA_URL.format (self.domain), headers=hdr)
        geo = http.json (res, schema=_geo_schema)
        timestamp = (int (time.time ()) + 3600) * 1000
        cookie = 'dsc-geo=%s' % quote ('{"countryCode":"%s","expiry":%s}' % (geo, timestamp))
        
        # Append cookie to headers
        hdr['Cookie'] = cookie
        
        # Get available streams using stream API
        try:
            res = http.get (STREAM_API_URL.format (self.domain, videoId, 'hls'),
                            headers=hdr, verify=False)
            data = http.json (res, schema=_media_schema)
            media = data.copy ()
            res = http.get (STREAM_API_URL.format (self.domain, videoId, 'hds'),
                            headers=hdr, verify=False)
            data = http.json (res, schema=_media_schema)
            media.update (data)
        except PluginError as err:      # Likely geo-restricted
            if any (e in str (err) for e in ('401 Client Error',
                                             '403 Client Error')):
                self.logger.error ('Failed to access stream API, '
                                   'may be due to geo-restriction')
                raise NoStreamsError (self.url)
            else:
                raise
        
        # Reformat data into list with stream format and url
        streams = [{'format': k, 'url': media[k]} for k in media]
        
        # Create mapper for supported stream types (HLS/HDS)
        mapper = StreamMapper (cmp=lambda type, video: video['format'] == type)
        mapper.map ('hls', self._create_streams, HLSStream.parse_variant_playlist)
        mapper.map ('hds', self._create_streams, HDSStream.parse_manifest)
        
        # Feed stream data to mapper and return all streams found
        return mapper (streams)

__plugin__ = Dplay
