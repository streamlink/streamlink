import base64
import datetime
import hashlib
import logging
import random
import re
import xml.etree.ElementTree as ET

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_xml

log = logging.getLogger(__name__)


class Radiko(Plugin):
    _url_re = re.compile(r'https?://radiko\.jp/(#!/)?(?P<state>live|ts)/(?P<station_id>[a-zA-Z0-9-]+)/?(?P<start_at>\d+)?')
    _api_auth_1 = 'https://radiko.jp/v2/api/auth1'
    _api_auth_2 = 'https://radiko.jp/v2/api/auth2'
    _auth_key = 'bcd151073c03b352e1ef2fd66c32209da9ca0afa'

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        match = self._url_re.match(self.url)
        state = match.group('state')
        station_id = match.group('station_id').upper()
        is_timefree = '0' if state == 'live' else '1'

        url = self.session.http.get(
            f'https://radiko.jp/v3/station/stream/pc_html5/{station_id}.xml',
            schema=validate.Schema(
                validate.transform(parse_xml),
                validate.xml_findall('.//url[@areafree="1"]'),
                [validate.union({
                    'timefree': validate.all(
                        validate.getattr('attrib'),
                        validate.get('timefree'),
                    ),
                    'url': validate.all(
                        validate.xml_find('./playlist_create_url'),
                        validate.getattr('text'),
                    ),
                })],
                validate.filter(lambda x: x['timefree'] == is_timefree),
                validate.get(0),
                validate.get('url'),
            )
        )
        log.debug(f'url={url}')
        params = {
            'station_id': station_id,
            'l': 15,
            'lsid': hashlib.md5(str(random.random()).encode('utf-8')).hexdigest(),
            'type': 'b',
        }
        token, area_id = self._authorize()
        log.debug(f'area_id={area_id}')
        if is_timefree == '1':
            start_at = match.group('start_at')
            end_at = self._get_xml(start_at, station_id)
            params.update({
                'start_at': start_at,
                'ft': start_at,
                'end_at': end_at,
                'to': end_at,
            })
        log.debug(f'params={params!r}')
        self.session.http.headers = {'X-Radiko-AuthToken': token}
        yield from HLSStream.parse_variant_playlist(self.session, url, params=params).items()

    def _authorize(self):
        headers = {
            'x-radiko-app': 'pc_html5',
            'x-radiko-app-version': '0.0.1',
            'x-radiko-device': 'pc',
            'x-radiko-user': 'dummy_user'
        }
        self.session.http.headers.update(headers)
        r = self.session.http.get(self._api_auth_1)
        token = r.headers.get('x-radiko-authtoken')
        offset = int(r.headers.get('x-radiko-keyoffset'))
        length = int(r.headers.get('x-radiko-keylength'))
        partial_key = base64.b64encode(self._auth_key[offset:offset + length].encode('ascii')).decode('utf-8')
        headers = {
            'x-radiko-authtoken': token,
            'x-radiko-device': 'pc',
            'x-radiko-partialkey': partial_key,
            'x-radiko-user': 'dummy_user'
        }
        self.session.http.headers.update(headers)
        r = self.session.http.get(self._api_auth_2)
        if r.status_code == 200:
            return token, r.text.split(',')[0]

    def _get_xml(self, start_at, station_id):
        today = datetime.date(int(start_at[:4]), int(start_at[4:6]), int(start_at[6:8]))
        yesterday = today - datetime.timedelta(days=1)
        if int(start_at[8:10]) < 5:
            date = yesterday.strftime('%Y%m%d')
        else:
            date = today.strftime('%Y%m%d')
        r = self.session.http.get(f'http://radiko.jp/v3/program/station/date/{date}/{station_id}.xml')
        tree = ET.XML(r.content)
        for x in tree[2][0][1].findall('prog'):
            if x.attrib['ft'] == start_at:
                return x.attrib['to']


__plugin__ = Radiko
