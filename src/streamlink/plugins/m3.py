import re
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream import HLSStream
from streamlink.plugin.api import useragents
import requests
from urllib3.exceptions import InsecureRequestWarning
 
@pluginmatcher(re.compile(r'https?://archivum.mtva.hu/m3'))
@pluginmatcher(re.compile(r'https://nemzetiarchivum.hu/m3'))
 
class M3(Plugin):
    def _get_streams(self):
        self.session.http.verify = False
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
        headers = {"User-Agent": useragents.CHROME,
                   "Referer": "https://nemzetiarchivum.hu/m3",
                  }
        body = self.session.http.get('https://nemzetiarchivum.hu/api/m3/v3/stream?target=live', headers=headers, verify=False).text
        mrl = None
        match = re.search(r'type":"hls","url":"(.*?)\"', body)
        if match:
            mrl = match.group(1).replace('\/','/').replace("HLS.smil","nodrm.smil")
        if mrl:
            return HLSStream.parse_variant_playlist(self.session, mrl, headers=headers)
 
__plugin__ = M3
