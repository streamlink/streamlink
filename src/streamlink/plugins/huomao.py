"""
NOTE: Since a documented API is nowhere to be found for Huomao; this plugin
simply extracts the videos stream_id, stream_url and stream_quality by
scraping the HTML and JS of one of Huomaos mobile webpages.

When viewing a stream on huomao.com, the base URL references a room_id. This
room_id is mapped one-to-one to a stream_id which references the actual .flv
video. Both stream_id, stream_url and stream_quality can be found in the
HTML and JS source of the mobile_page. Since one stream can occur in many
different qualities, we scrape all stream_url and stream_quality occurrences
and return each option to the user.
"""

import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.stream import HTTPStream

# URL pattern for recognizing inputed Huomao.tv / Huomao.com URL.
url_re = re.compile(r"""
    (http(s)?://)?
    (www\.)?
    huomao
    (\.tv|\.com)
    /(?P<room_id>\d+)
""", re.VERBOSE)

# URL used to retrive the stream_id, stream_url and stream_quality based of
# a room_id.
mobile_url = "http://www.huomao.com/mobile/mob_live/{0}"

# Pattern for extracting the stream_id from the mobile_url HTML.
#
# Example from HTML:
#   <input id="html_stream" value="efmrCH" type="hidden">
stream_id_pattern = re.compile(r'id=\"html_stream\" value=\"(?P<stream_id>\w+)\"')

# Pattern for extracting each stream_url, stream_quality_url and a prettified
# stream_quality_name used for quality naming.
#
# Example from HTML:
#   "2: 'http://live-ws.huomaotv.cn/live/'+stream+'_720/playlist.m3u8'"
stream_info_pattern = re.compile(r"""
    [1-9]:
    \s+
    '(?P<stream_url>(?:\w|\.|:|-|/)+)
    '\+stream\+'
    (?P<stream_quality_url>_?(?P<stream_quality_name>\d*))
    /playlist.m3u8'
""", re.VERBOSE)


class Huomao(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return url_re.match(url)

    def get_stream_id(self, html):
        """Returns the stream_id contained in the HTML."""
        stream_id = stream_id_pattern.search(html)

        if not stream_id:
            self.logger.error("Failed to extract stream_id.")

        return stream_id.group("stream_id")

    def get_stream_info(self, html):
        """Returns a nested list of different stream options.

        Each entry in the list will contain a stream_url, stream_quality_url
        and stream_quality_name for each stream occurrence that was found in
        the JS.
        """
        stream_info = stream_info_pattern.findall(html)

        if not stream_info:
            self.logger.error("Failed to extract stream_info.")

        # Rename the "" quality to "source" by transforming the tuples to a
        # list and reassigning.
        stream_info_list = []
        for info in stream_info:
            if not info[2]:
                stream_info_list.append([info[0], info[1], "source"])
            else:
                stream_info_list.append(list(info))

        return stream_info_list

    def _get_streams(self):
        room_id = url_re.search(self.url).group("room_id")
        html = http.get(mobile_url.format(room_id))
        stream_id = self.get_stream_id(html.text)
        stream_info = self.get_stream_info(html.text)

        streams = {}
        for info in stream_info:
            streams[info[2]] = HTTPStream(self.session,
                                          info[0] + stream_id + info[1] + ".flv")

        return streams


__plugin__ = Huomao
