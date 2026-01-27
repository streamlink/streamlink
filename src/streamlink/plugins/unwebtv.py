import logging
import re
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream.hls import HLSStream

log=logging.getLogger(__name__)

@pluginmatcher(re.compile(r"https?://webtv\.un\.org/"))
class UNWebTV(Plugin):
    """
    $description Global video streaming network of the United Nations.
    $url webtv.un.org
    $type live, vod
    $notes Content is free and not geo-restricted.
    """
    
    def _get_ks(self,partner_id):
        """
        Generates a Kaltura Session (KS) key.
        This is required to unlock the stream URL.
        """
        log.debug(f"Generating Widget Session for Partner ID: {partner_id}")
        try:
            # widgetId is typically "_{partner_id}" for public sessions
            url = "https://cdnapisec.kaltura.com/api_v3/service/session/action/startWidgetSession"
            params = {
                "widgetId": f"_{partner_id}",
                "format": "1"  # JSON response
            }
            # calling the Kaltura API
            res = self.session.http.get(url, params=params).json()
            ks = res.get("ks")
            if ks:
                log.debug(f"Generated KS: {ks[:10]}...")
                return ks
            else:
                log.warning("Kaltura API did not return a session key (KS).")
        except Exception as e:
            log.warning(f"Failed to generate session key: {e}")
        return None

    def _get_streams(self):
        log.debug(f"Fetching page: {self.url}")
        res = self.session.http.get(self.url)

        # 1. extract partner ID (default: 2503451)
        partner_id="2503451"
        p_id_match=re.search(r'partnerId["\']?\s*[:=]\s*["\']?(\d+)', res.text)
        if p_id_match:
            partner_id=p_id_match.group(1)

        # 2. get the Session Key (KS)
        # without this, even valid IDs will return 404 Not Found
        ks=self._get_ks(partner_id)

        # 3. find ALL video (entry) IDs
        # we look for standard Kaltura IDs (1_xxxx or 0_xxxx)
        # we use a set to avoid duplicates
        entry_ids=[]
        seen_ids=set()

        # find all 1_xxxx or 0_xxxx IDs in the source
        matches=re.findall(r'["\']([0-1]_[a-zA-Z0-9]{8,})["\']', res.text)
        for mid in matches:
            if mid not in seen_ids:
                entry_ids.append(mid)
                seen_ids.add(mid)

        # if no IDs found in source (unlikely), try URL slug as fallback
        if not entry_ids:
            url_match=re.search(r'/asset/[^/]+/(?P<slug>[a-zA-Z0-9]+)', self.url)
            if url_match:
                # for now, let's just log.
                log.warning("No standard Entry IDs found. URL slug might be a Reference ID (not fully supported yet).")

        if not entry_ids:
            log.error("No Entry IDs found to play.")
            return

        log.info(f"Found {len(entry_ids)} potential video IDs. Trying them...")

        # 4. try to play the found IDs using brute force
        # on the homepage, there are many IDs. The main player (for the 24/7 livestream) is usually the first valid one.
        # on an asset page, the specific video ID is usually in this list too.
        
        for entry_id in entry_ids:
            # construct the API URL
            #we append /ks/{ks} if we have one
            kaltura_url = (
                f"https://cdnapisec.kaltura.com/p/{partner_id}/sp/{partner_id}00/"
                f"playManifest/entryId/{entry_id}/format/applehttp/protocol/https/a.m3u8"
            )
            
            if ks:
                kaltura_url+=f"?ks={ks}"

            log.debug(f"Testing Entry ID: {entry_id}")
            
            try:
                # we attempt to fetch the playlist. 
                # if it fails (404/403), we catch it and try the next ID.
                streams=HLSStream.parse_variant_playlist(self.session, kaltura_url)
                
                # yield streams and stop looking.
                if streams:
                    log.info(f"Successfully loaded stream for ID: {entry_id}")
                    yield from streams.items()
                    return 
            except IOError as e:
                # 404 or 403 means this ID is invalid or not the main video. Continue.
                continue

        log.error("Tested all found IDs, but none were playable.")

__plugin__ = UNWebTV      
