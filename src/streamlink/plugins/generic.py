"""
    generic streamlink plugin

    source: https://github.com/back-to/generic
    issues: https://github.com/back-to/generic/issues
"""
import base64
import codecs
import logging
import os.path
import re

from html import unescape as html_unescape
from pathlib import Path
from typing import Pattern
from urllib.parse import parse_qsl, unquote, urljoin, urlparse

from streamlink.exceptions import (
    FatalPluginError,
    NoPluginError,
    NoStreamsError,
)
from streamlink.plugin import Plugin, PluginArgument, PluginArguments, pluginmatcher
from streamlink.plugin.api import useragents
from streamlink.plugin.plugin import HIGH_PRIORITY
from streamlink.stream import HLSStream, HTTPStream, DASHStream
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.utils.args import comma_list, num
from streamlink.utils.url import update_scheme

try:
    import yt_dlp as youtube_dl
    HAS_YTDL = True
except ImportError:
    try:
        import youtube_dl
        HAS_YTDL = True
    except ImportError:
        HAS_YTDL = False

GENERIC_VERSION = '2021-11-12'

log = logging.getLogger(__name__)

obfuscatorhtml_chunk_re = re.compile(r'''["'](?P<chunk>[A-z0-9+/=]+)["']''')
obfuscatorhtml_re = re.compile(
    r'<script[^<>]*>[^<>]*var\s*(\w+)\s*=\s*\[(?P<chunks>[^\[\]]+)\];\s*\1\.forEach.*-\s*(?P<minus>\d+)[^<>]*</script>',
)
unpack_packer_re = re.compile(
    r'''(?P<data>eval\(function\(p,a,c,k,e,(?:d|r)\).*\))''')
unpack_unescape_re = re.compile(r"""
    <script[^<>]*>[^>]*
    document.write\(unescape\(\s*
    ["']((?=[^<>"']*%\w{2})[^<>"']+)["']
    \)\);?[^<]*</script>""", re.VERBOSE)

unpack_source_url_re_1 = re.compile(r'''(?x)source:\s*(?P<replace>window\.atob\(
    (?P<q>["'])(?P<atob>[A-z0-9+/=]+)(?P=q)\)),\s*
    mimeType:\s*["']application/vnd\.apple\.mpegurl["']
''')
unpack_source_url_re_2 = re.compile(r'''(?x)var\s\w+url=(?P<replace>atob\(
    (?P<q>["'])(?P<atob>[A-z0-9+/=]+)(?P=q)\));''')
unpack_source_url_re_3 = re.compile(r'''(?x)Clappr\.Player\({\s*
    source:\s*(?P<replace>atob\((?P<q>["'])(?P<atob>[A-z0-9+/=]+)(?P=q)\))''')
unpack_u_m3u8_re = re.compile(r'(\\u0022[^\s,]+m3u8[^\s,]*\\u0022)')


class UnpackingError(Exception):
    """Badly packed source or general error."""


class Packer(object):
    """
    Unpacker for Dean Edward's p.a.c.k.e.r

    source: https://github.com/beautify-web/js-beautify/
    version: commit - b0e5f23a2d04db233f428349eb59e63bdefa78bb

    """

    def __init__(self):
        self.beginstr = ''
        self.endstr = ''

    def detect(self, source):
        """Detects whether `source` is P.A.C.K.E.R. coded."""
        mystr = source.replace(' ', '').find('eval(function(p,a,c,k,e,')
        if(mystr > 0):
            self.beginstr = source[:mystr]
        if(mystr != -1):
            """ Find endstr"""
            if(source.split("')))", 1)[0] == source):
                try:
                    self.endstr = source.split("}))", 1)[1]
                except IndexError:
                    self.endstr = ''
            else:
                self.endstr = source.split("')))", 1)[1]
        return (mystr != -1)

    def unpack(self, source):
        """Unpacks P.A.C.K.E.R. packed js code."""
        payload, symtab, radix, count = self._filterargs(source)

        if count != len(symtab):
            raise UnpackingError('Malformed p.a.c.k.e.r. symtab.')

        try:
            if radix == 1:
                unbase = int
            else:
                unbase = Unbaser(radix)
        except TypeError:
            raise UnpackingError('Unknown p.a.c.k.e.r. encoding.')

        def lookup(match):
            """Look up symbols in the synthetic symtab."""
            word = match.group(0)
            return symtab[unbase(word)] or word

        source = re.sub(r'\b\w+\b', lookup, payload)
        return self._replacestrings(source)

    def _filterargs(self, source):
        """Juice from a source file the four args needed by decoder."""
        juicers = [(r"}\('(.*)', *(\d+|\[\]), *(\d+), *'(.*)'\.split\('\|'\), *(\d+), *(.*)\)\)"),
                   (r"}\('(.*)', *(\d+|\[\]), *(\d+), *'(.*)'\.split\('\|'\)"),
                   ]
        for juicer in juicers:
            args = re.search(juicer, source, re.DOTALL)
            if args:
                a = args.groups()
                if a[1] == "[]":
                    a = list(a)
                    a[1] = 62
                    a = tuple(a)
                try:
                    return a[0], a[3].split('|'), int(a[1]), int(a[2])
                except ValueError:
                    raise UnpackingError('Corrupted p.a.c.k.e.r. data.')

        # could not find a satisfying regex
        raise UnpackingError('Could not make sense of p.a.c.k.e.r data (unexpected code structure)')

    def _replacestrings(self, source):
        """Strip string lookup table (list) and replace values in source."""
        match = re.search(r'var *(_\w+)\=\["(.*?)"\];', source, re.DOTALL)

        if match:
            varname, strings = match.groups()
            startpoint = len(match.group(0))
            lookup = strings.split('","')
            variable = '%s[%%d]' % varname
            for index, value in enumerate(lookup):
                source = source.replace(variable % index, '"%s"' % value)
            return source[startpoint:]
        return self.beginstr + source + self.endstr


class Unbaser(object):
    """Functor for a given base. Will efficiently convert
    strings to natural numbers."""
    ALPHABET = {
        62: '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
        95: (' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ'
             '[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~')
    }

    def __init__(self, base):
        self.base = base
        # fill elements 37...61, if necessary
        if 36 < base < 62:
            if not hasattr(self.ALPHABET,
                           self.ALPHABET[62][:base]):
                self.ALPHABET[base] = self.ALPHABET[62][:base]
        # attrs = self.ALPHABET
        # print ', '.join("%s: %s" % item for item in attrs.items())
        # If base can be handled by int() builtin, let it do it for us
        if 2 <= base <= 36:
            self.unbase = lambda s: int(s, base)
        else:
            # Build conversion dictionary cache
            try:
                self.dictionary = dict(
                    (cipher, index) for index, cipher in enumerate(self.ALPHABET[base]))
            except KeyError:
                raise TypeError('Unsupported base encoding.')
            self.unbase = self._dictunbaser

    def __call__(self, s):
        return self.unbase(s)

    def _dictunbaser(self, s):
        """Decodes a  value to an integer."""
        ret = 0
        for index, cipher in enumerate(s[::-1]):
            ret += (self.base ** index) * self.dictionary[cipher]
        return ret


def unpack_packer(text: str) -> str:
    """unpack p.a.c.k.e.r"""
    packer = Packer()
    packer_list = unpack_packer_re.findall(text)
    if packer_list:
        for data in packer_list:
            if packer.detect(data):
                try:
                    unpacked = packer.unpack(data).replace('\\', '')
                    text = text.replace(data, unpacked)
                except UnpackingError:
                    pass
    return text


def unpack_obfuscatorhtml(text: str) -> str:
    """
    Unpacker for Obfuscator HTML https://github.com/BlueEyesHF/Obfuscator-HTML
    """
    while True:
        m = obfuscatorhtml_re.search(text)
        if m:
            unpacked = ""
            chunks = obfuscatorhtml_chunk_re.findall(m.group('chunks'))
            minus = int(m.group('minus'))
            for chunk in chunks:
                int_chunk = int(re.sub(r'\D', '', str(base64.b64decode(chunk))))
                unpacked += chr(int_chunk - int(minus))
            text = text.replace(m.group(0), unpacked)
        else:
            break
    return text


def unpack_unescape(text: str) -> str:
    while True:
        m = unpack_unescape_re.search(text)
        if m:
            text = text.replace(m.group(0), unquote(m.group(1)))
        else:
            break
    return text


def unpack_source_url(text: str, _unpack_source_url_re: Pattern) -> str:
    while True:
        m1 = _unpack_source_url_re.search(text)
        if m1:
            try:
                atob = base64.b64decode(m1.group("atob")).decode("utf-8")
            except Exception:
                atob = 'INVALID unpack_source_url'

            try:
                atob = "{q}{atob}{q}".format(q=m1.group("q"), atob=atob)
                text = text.replace(m1.group("replace"), atob)
            except Exception:
                pass
        else:
            break
    return text


def unpack_u_m3u8(text: str) -> str:
    def _unicode_escape(s: str) -> str:
        unicode_escape = codecs.getdecoder('unicode_escape')
        return re.sub(r'\\u[0-9a-fA-F]{4}', lambda m: unicode_escape(m.group(0))[0], s)

    while True:
        m = unpack_u_m3u8_re.search(text)
        if m:
            text = text.replace(m.group(0), _unicode_escape(m.group(0)))
        else:
            break
    return text


def unpack(text: str) -> str:
    """ unpack html source code """
    text = unpack_packer(text)
    text = unpack_obfuscatorhtml(text)
    text = unpack_unescape(text)
    text = unpack_source_url(text, unpack_source_url_re_1)
    text = unpack_source_url(text, unpack_source_url_re_2)
    text = unpack_source_url(text, unpack_source_url_re_3)
    text = unpack_u_m3u8(text)
    return text


class GenericCache(object):
    '''GenericCache is useded as a temporary session cache
       - GenericCache.blacklist_path
       - GenericCache.cache_url_list
       - GenericCache.whitelist_path
    '''
    pass


@pluginmatcher(re.compile(r'((?:generic|resolve)://)(?P<url>.+)'), priority=HIGH_PRIORITY)
@pluginmatcher(re.compile(r'(?P<url>.+)'), priority=1)
class Generic(Plugin):
    # iframes
    _iframe_re = re.compile(r'''(?isx)
        <ifr(?:["']\s?\+\s?["'])?ame
        (?!\sname=["']g_iFrame).*?src=
        ["'](?P<url>[^"'\s<>]+)\s?["']
        [^<>]*?>
    ''')
    # playlists
    _playlist_re = re.compile(r'''(?sx)
        (?:["']|=|&quot;)(?P<url>
            (?<!title=["'])
            (?<!["']title["']:["'])
                [^"'<>\s\;{}]+\.(?:m3u8|mp3|mp4|mpd)
            (?:\?[^"'<>\s\\{}]+)?)/?
        (?:\\?["']|(?<!;)\s|>|\\&quot;)
    ''')
    # mp3 and mp4 files
    _httpstream_bitrate_re = re.compile(r'''(?x)
        (?:_|\.|/|-)
        (?:
            (?P<bitrate>\d{1,4})(?:k)?
            |
            (?P<resolution>\d{1,4}p)
            (?:\.h26(?:4|5))?
        )
        \.mp(?:3|4)
    ''')
    _httpstream_common_resolution_list = [
        '2160', '1440', '1080', '720', '576', '480', '360', '240',
    ]
    # javascript redirection
    _window_location_re = re.compile(r'''(?sx)
        <script[^<]+window\.location\.href\s?=\s?["']
        (?P<url>[^"']+)["'];[^<>]+
    ''')
    # obviously ad paths
    _ads_path_re = re.compile(r'''(?x)
        /ads?/?(?:\w+)?
        (?:\d+x\d+)?
        (?:_\w+)?\.(?:html?|php)$
    ''')

    # START - _make_url_list
    # Not allowed at the end of the parsed url path
    blacklist_endswith = (
        '.gif',
        '.jpg',
        '.png',
        '.svg',
        '.vtt',
        '/chat.html',
        '/chat',
        '/novideo.mp4',
        '/vidthumb.mp4',
        '/ads-iframe-display.php',
    )
    # Not allowed at the end of the parsed url netloc
    blacklist_netloc = (
        '127.0.0.1',
        'a.adtng.com',
        'about:blank',
        'abv.bg',
        'adfox.ru',
        'cbox.ws',
        'googletagmanager.com',
        'javascript:false',
        'accounts.google.com',
    )
    # END - _make_url_list

    arguments = PluginArguments(
        PluginArgument(
            'playlist-max',
            metavar='NUMBER',
            type=num(int, min=0, max=25),
            default=5,
            help='''
            Number of how many playlist URLs of the same type
            are allowed to be resolved with this plugin.

            Default is 5
            '''
        ),
        PluginArgument(
            'playlist-referer',
            metavar='URL',
            help='''
            Set a custom referer URL for the playlist URLs.

            This only affects playlist URLs of this plugin.

            Default is the URL of the last website.
            '''
        ),
        PluginArgument(
            'blacklist-netloc',
            metavar='NETLOC',
            type=comma_list,
            help='''
            Blacklist domains that should not be used,
            by using a comma-separated list:

              'example.com,localhost,google.com'

            Useful for websites with a lot of iframes.
            '''
        ),
        PluginArgument(
            'blacklist-path',
            metavar='PATH',
            type=comma_list,
            help='''
            Blacklist the path of a domain that should not be used,
            by using a comma-separated list:

              'example.com/mypath,localhost/example,google.com/folder'

            Useful for websites with different iframes of the same domain.
            '''
        ),
        PluginArgument(
            'blacklist-filepath',
            metavar='FILEPATH',
            type=comma_list,
            help='''
            Blacklist file names for iframes and playlists
            by using a comma-separated list:

              'index.html,ignore.m3u8,/ad/master.m3u8'

            Sometimes there are invalid URLs in the result list,
            this can be used to remove them.
            '''
        ),
        PluginArgument(
            'whitelist-netloc',
            metavar='NETLOC',
            type=comma_list,
            help='''
            Whitelist domains that should only be searched for iframes,
            by using a comma-separated list:

              'example.com,localhost,google.com'

            Useful for websites with lots of iframes,
            where the main iframe always has the same hosting domain.
            '''
        ),
        PluginArgument(
            'whitelist-path',
            metavar='PATH',
            type=comma_list,
            help='''
            Whitelist the path of a domain that should only be searched
            for iframes, by using a comma-separated list:

              'example.com/mypath,localhost/example,google.com/folder'

            Useful for websites with different iframes of the same domain,
            where the main iframe always has the same path.
            '''
        ),
        PluginArgument(
            'ignore-same-url',
            action='store_true',
            help='''
            Do not remove URLs from the valid list if they were already used.

            Sometimes needed as a workaround for --player-external-http issues.

            Be careful this might result in an infinity loop.
            '''
        ),
        PluginArgument(
            'ytdl-disable',
            action='store_true',
            help='''
            Disable youtube-dl fallback.
            '''
        ),
        PluginArgument(
            'ytdl-only',
            action='store_true',
            help='''
            Disable generic plugin and use only youtube-dl.
            '''
        ),
        PluginArgument(
            'debug',
            action='store_true',
            help='''
            Developer Command!

            Saves unpacked HTML code of all opened URLs to the local hard drive for easier debugging.
            '''
        ),
    )

    def __init__(self, url):
        super(Generic, self).__init__(url)
        self.url = update_scheme('http://', self.match.group('url'), force=False)
        self.html_text = ''

        # START - cache every used url and set a referer
        if hasattr(GenericCache, 'cache_url_list'):
            GenericCache.cache_url_list += [self.url]
            # set the last url as a referer
            self.referer = GenericCache.cache_url_list[-2]
        else:
            GenericCache.cache_url_list = [self.url]
            self.referer = self.url
        self.session.http.headers.update({'Referer': self.referer})
        # END

        # START - how often _get_streams already run
        self._run = len(GenericCache.cache_url_list)
        # END

    def compare_url_path(self, parsed_url, check_list,
                         path_status='startswith'):
        status = False
        for netloc, path in check_list:
            if path_status == '==':
                if (parsed_url.netloc.endswith(netloc) and parsed_url.path == path):
                    status = True
                    break
            elif path_status == 'startswith':
                if (parsed_url.netloc.endswith(netloc) and parsed_url.path.startswith(path)):
                    status = True
                    break

        return status

    def merge_path_list(self, static, user):
        for _path_url in user:
            if not _path_url.startswith(('http', '//')):
                _path_url = update_scheme('http://', _path_url, force=False)
            _parsed_path_url = urlparse(_path_url)
            if _parsed_path_url.netloc and _parsed_path_url.path:
                static += [(_parsed_path_url.netloc, _parsed_path_url.path)]
        return static

    def repair_url(self, url, base_url, stream_base=''):
        # remove \
        new_url = url.replace('\\', '')
        # repairs broken scheme
        if new_url.startswith('http&#58;//'):
            new_url = 'http:' + new_url[9:]
        elif new_url.startswith('https&#58;//'):
            new_url = 'https:' + new_url[10:]
        new_url = unquote(new_url)
        # creates a valid url from path only urls
        # and adds missing scheme for // urls
        if stream_base and new_url[1] != '/':
            if new_url[0] == '/':
                new_url = new_url[1:]
            new_url = urljoin(stream_base, new_url)
        else:
            new_url = urljoin(base_url, new_url)
        return new_url

    def _make_url_list(self, old_list, base_url, url_type=''):
        # START - List for not allowed URL Paths
        # --generic-blacklist-path
        if not hasattr(GenericCache, 'blacklist_path'):

            # static list
            blacklist_path = [
                ('facebook.com', '/connect'),
                ('facebook.com', '/plugins'),
                ('google.com', '/recaptcha/'),
                ('haber7.com', '/radyohome/station-widget/'),
                ('static.tvr.by', '/upload/video/atn/promo'),
                ('twitter.com', '/widgets'),
                ('vesti.ru', '/native_widget.html'),
                ('www.blogger.com', '/static'),
                ('youtube.com', '/['),
            ]

            # merge user and static list
            blacklist_path_user = self.get_option('blacklist_path')
            if blacklist_path_user is not None:
                blacklist_path = self.merge_path_list(
                    blacklist_path, blacklist_path_user)

            GenericCache.blacklist_path = blacklist_path
        # END

        blacklist_path_same = [
            ('player.vimeo.com', '/video/'),
            ('youtube.com', '/embed/'),
        ]

        # START - List of only allowed URL Paths for Iframes
        # --generic-whitelist-path
        if not hasattr(GenericCache, 'whitelist_path'):
            whitelist_path = []
            whitelist_path_user = self.get_option('whitelist_path')
            if whitelist_path_user is not None:
                whitelist_path = self.merge_path_list(
                    [], whitelist_path_user)
            GenericCache.whitelist_path = whitelist_path
        # END

        allow_same_url = (self.get_option('ignore_same_url'))

        new_list = []
        for url in old_list:
            new_url = self.repair_url(url, base_url)
            # parse the url
            parse_new_url = urlparse(new_url)

            # START
            REMOVE = False
            if new_url in GenericCache.cache_url_list and not allow_same_url:
                # Removes an already used url
                # ignored if --hls-session-reload is used
                REMOVE = 'SAME-URL'
            elif (not parse_new_url.scheme.startswith(('http'))):
                # Allow only an url with a valid scheme
                REMOVE = 'SCHEME'
            elif (url_type == 'iframe'
                    and self.get_option('whitelist_netloc')
                    and parse_new_url.netloc.endswith(tuple(self.get_option('whitelist_netloc'))) is False):
                # Allow only whitelisted domains for iFrames
                # --generic-whitelist-netloc
                REMOVE = 'WL-netloc'
            elif (url_type == 'iframe'
                    and GenericCache.whitelist_path
                    and self.compare_url_path(parse_new_url, GenericCache.whitelist_path) is False):
                # Allow only whitelisted paths from a domain for iFrames
                # --generic-whitelist-path
                REMOVE = 'WL-path'
            elif (parse_new_url.netloc.endswith(self.blacklist_netloc)):
                # Removes blacklisted domains from a static list
                # self.blacklist_netloc
                REMOVE = 'BL-static'
            elif (self.get_option('blacklist_netloc')
                  and parse_new_url.netloc.endswith(tuple(self.get_option('blacklist_netloc')))):
                # Removes blacklisted domains
                # --generic-blacklist-netloc
                REMOVE = 'BL-netloc'
            elif (self.compare_url_path(parse_new_url, GenericCache.blacklist_path) is True):
                # Removes blacklisted paths from a domain
                # --generic-blacklist-path
                REMOVE = 'BL-path'
            elif (parse_new_url.path.endswith(self.blacklist_endswith)):
                # Removes unwanted endswith images and chatrooms
                REMOVE = 'BL-ew'
            elif (self.get_option('blacklist_filepath')
                  and parse_new_url.path.endswith(tuple(self.get_option('blacklist_filepath')))):
                # Removes blacklisted file paths
                # --generic-blacklist-filepath
                REMOVE = 'BL-filepath'
            elif (self._ads_path_re.search(parse_new_url.path) or parse_new_url.netloc.startswith(('ads.'))):
                # Removes obviously AD URL
                REMOVE = 'ADS'
            elif (self.compare_url_path(parse_new_url, blacklist_path_same, path_status='==') is True):
                # Removes blacklisted same paths from a domain
                REMOVE = 'BL-path-same'
            elif parse_new_url.netloc == 'cdn.embedly.com' and parse_new_url.path == '/widgets/media.html':
                # do not use the direct URL for 'cdn.embedly.com', search the query for a new URL
                params = dict(parse_qsl(parse_new_url.query))
                embedly_new_url = params.get('url') or params.get('src')
                if embedly_new_url:
                    new_list += [embedly_new_url]
                else:
                    log.error('Missing params URL or SRC for {0}'.format(new_url))
                continue
            else:
                # valid URL
                new_list += [new_url]
                continue

            log.debug('{0} - Removed: {1}'.format(REMOVE, new_url))
            # END

        # Remove duplicates
        log.debug('List length: {0} (with duplicates)'.format(len(new_list)))
        new_list = sorted(list(set(new_list)))
        return new_list

    def _window_location(self):
        match = self._window_location_re.search(self.html_text)
        if match:
            temp_url = urljoin(self.url, match.group('url'))
            if temp_url not in GenericCache.cache_url_list:
                log.debug('Found window_location: {0}'.format(temp_url))
                return temp_url

        log.trace('No window_location')
        return False

    def _resolve_playlist(self, playlist_all):
        playlist_referer = self.get_option('playlist_referer') or self.url
        self.session.http.headers.update({'Referer': playlist_referer})

        playlist_max = self.get_option('playlist_max') or 5
        count_playlist = {
            'dash': 0,
            'hls': 0,
            'http': 0,
        }

        o = urlparse(self.url)
        origin_tuple = (
            '.cloudfront.net',
        )

        for url in playlist_all:
            parsed_url = urlparse(url)
            if parsed_url.netloc.endswith(origin_tuple):
                self.session.http.headers.update({
                    'Origin': '{0}://{1}'.format(o.scheme, o.netloc),
                })

            if (parsed_url.path.endswith(('.m3u8'))
                    or parsed_url.query.endswith(('.m3u8'))):
                if count_playlist['hls'] >= playlist_max:
                    log.debug('Skip - {0}'.format(url))
                    continue
                try:
                    streams = HLSStream.parse_variant_playlist(self.session, url).items()
                    if not streams:
                        yield 'live', HLSStream(self.session, url)
                    for s in streams:
                        yield s
                    log.debug('HLS URL - {0}'.format(url))
                    count_playlist['hls'] += 1
                except Exception as e:
                    log.error('Skip HLS with error {0}'.format(str(e)))
            elif (parsed_url.path.endswith(('.mp3', '.mp4'))
                    or parsed_url.query.endswith(('.mp3', '.mp4'))):
                if count_playlist['http'] >= playlist_max:
                    log.debug('Skip - {0}'.format(url))
                    continue
                try:
                    name = 'vod'
                    m = self._httpstream_bitrate_re.search(url)
                    if m:
                        bitrate = m.group('bitrate')
                        resolution = m.group('resolution')
                        if bitrate:
                            if bitrate in self._httpstream_common_resolution_list:
                                name = '{0}p'.format(m.group('bitrate'))
                            else:
                                name = '{0}k'.format(m.group('bitrate'))
                        elif resolution:
                            name = resolution
                    yield name, HTTPStream(self.session, url)
                    log.debug('HTTP URL - {0}'.format(url))
                    count_playlist['http'] += 1
                except Exception as e:
                    log.error('Skip HTTP with error {0}'.format(str(e)))
            elif (parsed_url.path.endswith(('.mpd'))
                    or parsed_url.query.endswith(('.mpd'))):
                if count_playlist['dash'] >= playlist_max:
                    log.debug('Skip - {0}'.format(url))
                    continue
                try:
                    for s in DASHStream.parse_manifest(self.session,
                                                       url).items():
                        yield s
                    log.debug('DASH URL - {0}'.format(url))
                    count_playlist['dash'] += 1
                except Exception as e:
                    log.error('Skip DASH with error {0}'.format(str(e)))
            else:
                log.error('parsed URL - {0}'.format(url))

    def _res_text(self, url):
        try:
            res = self.session.http.get(url, allow_redirects=True)
        except Exception as e:
            if 'Received response with content-encoding: gzip' in str(e):
                headers = {
                    'User-Agent': useragents.FIREFOX,
                    'Accept-Encoding': 'deflate'
                }
                res = self.session.http.get(url, headers=headers, allow_redirects=True)
            elif '403 Client Error' in str(e):
                log.error('Website Access Denied/Forbidden, you might be geo-'
                          'blocked or other params are missing.')
                raise NoStreamsError(self.url)
            elif '404 Client Error' in str(e):
                log.error('Website was not found, the link is broken or dead.')
                raise NoStreamsError(self.url)
            else:
                raise e

        if res.history:
            for resp in res.history:
                log.debug('Redirect: {0} - {1}'.format(resp.status_code, resp.url))
            log.debug('URL: {0}'.format(res.url))
        return res.text

    def get_author(self):
        parsed = urlparse(self.url)
        split_username = list(filter(None, parsed.path.split('/')))
        if len(split_username) == 1:
            return split_username[0]
        elif parsed.fragment:
            return parsed.fragment
        return super().get_author()

    def get_title(self):
        if self.title is None:
            if not self.html_text:
                self.html_text = self._res_text(self.url)
            _og_title_re = re.compile(r'<meta\s*property="og:title"\s*content="(?P<title>[^<>]+)"\s*/?>')
            _title_re = re.compile(r'<title[^<>]*>(?P<title>[^<>]+)</title>')
            m = _og_title_re.search(self.html_text) or _title_re.search(self.html_text)
            if m:
                self.title = re.sub(r'[\s]+', ' ', m.group('title'))
                self.title = re.sub(r'^\s*|\s*$', '', self.title)
                self.title = html_unescape(self.title)
            if self.title is None:
                # fallback if there is no <title>
                self.title = self.url
        return self.title

    def ytdl_fallback(self):
        '''Basic support for m3u8 URLs with youtube-dl'''
        log.debug(f'Fallback {youtube_dl.__name__} {youtube_dl.version.__version__}')

        class YTDL_Logger(object):
            def debug(self, msg):
                log.debug(msg)

            def warning(self, msg):
                log.warning(msg)

            def error(self, msg):
                log.trace(msg)

        ydl_opts = {
            'call_home': False,
            'forcejson': True,
            'logger': YTDL_Logger(),
            'no_color': True,
            'noplaylist': True,
            'no_warnings': True,
            'verbose': False,
            'quiet': True,
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(self.url, download=False)
            except Exception:
                return

            if not info or not info.get('formats'):
                return

        self.title = info['title']

        streams = []
        for stream in info['formats']:
            if stream['protocol'] in ['m3u8', 'm3u8_native'] and stream['ext'] == 'mp4':
                log.trace('{0!r}'.format(stream))
                name = stream.get('height') or stream.get('width')
                if name:
                    name = '{0}p'.format(name)
                    streams.append((name, HLSStream(self.session,
                                                    stream['url'],
                                                    headers=stream['http_headers'])))

        if not streams:
            if ('youtube.com' in self.url
                    and info.get('requested_formats')
                    and len(info.get('requested_formats')) == 2
                    and MuxedStream.is_usable(self.session)):
                audio_url = audio_format = video_url = video_format = video_name = None
                for stream in info.get('requested_formats'):
                    if stream.get('format_id') == '135':
                        url = stream.get('manifest_url')
                        if not url:
                            return
                        return DASHStream.parse_manifest(self.session, url).items()
                    if not stream.get('height'):
                        audio_url = stream.get('url')
                        audio_format = stream.get('format_id')
                    if stream.get('height'):
                        video_url = stream.get('url')
                        video_format = stream.get('format_id')
                        video_name = '{0}p'.format(stream.get('height'))

                log.debug('MuxedStream: v {video} a {audio} = {name}'.format(
                    audio=audio_format,
                    name=video_name,
                    video=video_format,
                ))
                streams.append((video_name,
                                MuxedStream(self.session,
                                            HTTPStream(self.session, video_url, headers=stream['http_headers']),
                                            HTTPStream(self.session, audio_url, headers=stream['http_headers']))
                                ))
        return streams

    def _get_streams(self):
        if HAS_YTDL and not self.get_option('ytdl-disable') and self.get_option('ytdl-only'):
            ___streams = self.ytdl_fallback()
            if ___streams and len(___streams) >= 1:
                return (s for s in ___streams)
            if self.get_option('ytdl-only'):
                return

        if self._run <= 1:
            log.info('Version {0} - https://github.com/back-to/generic'.format(GENERIC_VERSION))

        new_url = False
        log.info('  {0}. URL={1}'.format(self._run, self.url))

        # GET website content
        self.html_text = self._res_text(self.url)
        # unpack common javascript codes
        self.html_text = unpack(self.html_text)

        if self.get_option('debug'):
            _valid_filepath = re.sub(r'(?u)[^-\w.]', '', str(self.url).strip().replace(' ', '_'))
            _new_file = os.path.join(Path().absolute(),
                                     f'{self._run}_{_valid_filepath}.html')
            log.warning(f'NEW DEBUG FILE! {_new_file}')
            try:
                with open(_new_file, 'w+') as f:
                    f.write(str(self.html_text))
            except OSError:
                pass

        # Playlist URL
        playlist_all = self._playlist_re.findall(self.html_text)
        if playlist_all:
            log.debug('Found Playlists: {0}'.format(len(playlist_all)))
            playlist_list = self._make_url_list(playlist_all,
                                                self.url,
                                                url_type='playlist',
                                                )
            if playlist_list:
                log.info('Found Playlists: {0} (valid)'.format(
                    len(playlist_list)))
                return self._resolve_playlist(playlist_list)
        else:
            log.trace('No Playlists')

        # iFrame URL
        iframe_list = self._iframe_re.findall(self.html_text)
        if iframe_list:
            log.debug('Found Iframes: {0}'.format(len(iframe_list)))
            # repair and filter iframe url list
            new_iframe_list = self._make_url_list(iframe_list,
                                                  self.url,
                                                  url_type='iframe')
            if new_iframe_list:
                number_iframes = len(new_iframe_list)
                if number_iframes == 1:
                    new_url = new_iframe_list[0]
                else:
                    log.info('--- IFRAMES ---')
                    for i, item in enumerate(new_iframe_list, start=1):
                        log.info('{0} - {1}'.format(i, item))
                    log.info('--- IFRAMES ---')

                    try:
                        number = int(self.input_ask(
                            'Choose an iframe number from above').split(' ')[0])
                        new_url = new_iframe_list[number - 1]
                    except FatalPluginError:
                        new_url = new_iframe_list[0]
                    except ValueError:
                        log.error('invalid input answer')
                    except (IndexError, TypeError):
                        log.error('invalid input number')

                    if not new_url:
                        new_url = new_iframe_list[0]
        else:
            log.trace('No iframes')

        if not new_url:
            # search for window.location.href
            new_url = self._window_location()

        if new_url:
            # the Dailymotion Plugin does not work with this Referer
            if 'dailymotion.com' in new_url:
                del self.session.http.headers['Referer']
            return self.session.streams(new_url)

        if HAS_YTDL and not self.get_option('ytdl-disable') and not self.get_option('ytdl-only'):
            ___streams = self.ytdl_fallback()
            if ___streams and len(___streams) >= 1:
                return (s for s in ___streams)

        raise NoPluginError


__plugin__ = Generic
