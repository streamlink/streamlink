import re

from urllib.parse import unquote
from json import loads

from streamlink.plugin import Plugin
from streamlink.plugin import PluginError
from streamlink.stream import HLSStream


class Discovery(Plugin):
    url_re = re.compile(r'''
        ^https?://(www\.)?((go|watch)\.)?
        (?P<host>
            discovery|tlc|animalplanet|investigationdiscovery|science|discoverylife|
            motortrend|ahc|destinationamerica|discoveryfamily|discoveryenespanol|
            discovery-familia|own|hgtv|food|travel|cooking-channel|diy
        )
        \.com/watch/
        (?P<slug>
            discovery|tlc|animal-planet|investigation-discovery|science|discovery-life|
            motortrend|ahc|destination-america|discovery-family|discovery-en-espanol|
            discovery-familia|own|hgtv|food|travel|cooking-channel|diy
        )
        \??$
    ''', re.VERBOSE)

    api_url = 'https://api.discovery.com/v1/content/livestreams?slug='

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        slug = self.url_re.match(self.url)['slug'].lower()
        eosAf = None

        if 'eosAf' in self.session.http.cookies:
            eosAf = self.session.http.cookies['eosAf']

        if not eosAf:
            self.logger.error("Login cookie missing. Provide 'eosAf' cookie with --http-cookie.")
            return

        eosAf_parsed = loads(unquote(unquote(eosAf)))
        auth = eosAf_parsed['a']
        header = {'Authorization': 'Bearer ' + auth}

        access_res = self.session.http.get(self.api_url + slug, headers=header)
        access_link = access_res.json()[0]['links'][0]['href']

        link_res = self.session.http.get(access_link, headers=header)
        link_data = link_res.json()

        if 'streamUrl' in link_data:
            stream_url = link_data['streamUrl']
        else:
            stream_url = link_data[0]['links'][0]['href']

        try:
            self.session.http.get(stream_url)  # check for 401 error

        except PluginError as ex:
            if ex.err.response.status_code == 401:  # pylint: disable=no-member
                # some Discovery sites have a separate eosAf cookie that does not work with other sites
                self.logger.error("Error 401: Unauthorized. This is most likely because you used an eosAf cookie from another Discovery site or one that has expired.")
            raise ex

        return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = Discovery
