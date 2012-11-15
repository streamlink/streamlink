from livestreamer.compat import str, bytes
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget, verifyjson

import re
import json
import requests

class DailyMotion(Plugin):

    QualityMap = {
            'ld'    : '240p',
            'sd'    : '360p',
            'hq'    : '480p',
            'hd720' : '720p',
            'hd1080': '1080p'
    }

    StreamInfoURL = "http://www.dailymotion.com/sequence/full/{0}"
    MetadataURL = "https://api.dailymotion.com/video/{0}"

    @classmethod
    def can_handle_url(self, url):
        # valid urls are of the form dailymotion.com/video/[a-z]{5}.*
        # but we make 'video/' optionnal and allow for dai.ly as shortcut
        return ("dailymotion.com" in url) or ("dai.ly" in url)

    def _check_channel_live(self, id):
        url = self.MetadataURL.format(self.channelname)
        res = urlget(url, params=dict(fields="mode"))
        if len(res.json) == 0:
            raise PluginError("Error retrieving stream live status")
        return res.json['mode'] == 'live'

    def _get_channel_name(self, url):
        rpart = url.rstrip("/").rpartition("/")[2].lower()
        name = re.sub('_.*', '', rpart)
        return name

    def _get_node_by_name(self, parent, name):
        res = None
        for node in parent:
            if node['name'] == name:
                res = node
                break
        return res


    def _get_rtmp_streams(self):

        url = self.MetadataURL.format(self.channelname)

        self.logger.debug("Fetching stream info")
        res = urlget(url)

        if not isinstance(res.json, dict):
            raise PluginError("Stream info response is not JSON")

        chan_id = verifyjson(res.json, 'id')

        streams = {}

        if not self._check_channel_live(chan_id):
            return streams

        url = self.StreamInfoURL.format(self.channelname)

        self.logger.debug("JSON data url: {0}", url)

        res = urlget(url)

        if not isinstance(res.json, dict):
            raise PluginError("Stream info response is not JSON")

        if len(res.json) == 0:
            raise PluginError("JSON is empty")

        chan_info_json = res.json

        # This is ugly, not sure how to fix it.
        back_json_node = chan_info_json['sequence'][0]['layerList'][0]
        if back_json_node['name'] != 'background':
            raise PluginError("JSON data has unexpected structure")

        rep_node = self._get_node_by_name(back_json_node['sequenceList'], 'reporting')['layerList']
        main_node = self._get_node_by_name(back_json_node['sequenceList'], 'main')['layerList']

        if not(rep_node and main_node):
            raise PluginError("Error parsing stream RTMP url")

        swfurl = self._get_node_by_name(rep_node, 'reporting')['param']['extraParams']['videoSwfURL']
        feeds_params = self._get_node_by_name(main_node, 'video')['param']

        if not(swfurl and feeds_params):
            raise PluginError("Error parsing stream RTMP url")


        # Different feed qualities are available are a dict under 'live'
        # In some cases where there's only 1 quality available,
        # it seems the 'live' is absent. We use the single stream available
        # under the 'customURL' key.

        if feeds_params.has_key('live') and len(feeds_params['live']) > 0:
            quals = feeds_params['live']
        else:
            res = urlget(feeds_params['customURL'])
            rtmpurl = res.text

            stream = RTMPStream(self.session, {
                "rtmp": rtmpurl,
                "swfVfy": swfurl,
                "live": True
            })
            self.logger.debug('Adding URL: '+feeds_params['customURL'])
            streams['live'] = stream
            return streams

        for (k,q) in quals.iteritems():
            info = {}

            try:
                res = urlget(q, exception=IOError)
            except IOError:
                continue
            rtmpurl = res.text

            stream = RTMPStream(self.session, {
                "rtmp": rtmpurl,
                "swfVfy": swfurl,
                "live": True
            })
            self.logger.debug('Adding URL: '+rtmpurl)

            if k in self.QualityMap:
                sname = self.QualityMap[k]
            else:
                sname = k

            streams[sname] = stream

        return streams

    def _get_streams(self):
        self.channelname = self._get_channel_name(self.url)

        if not self.channelname:
            raise NoStreamsError(self.url)

        streams = {}

        try:
            rtmpstreams = self._get_rtmp_streams()
            streams.update(rtmpstreams)
        except PluginError as err:
            self.logger.error("Error when fetching RTMP stream info: {0}", str(err))

        return streams


__plugin__ = DailyMotion


# vim: expandtab tabstop=4 shiftwidth=4
