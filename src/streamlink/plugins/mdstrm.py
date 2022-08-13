"""
$description CDN hosting live content for various websites in the Americas.
$url mdstrm.com
$url latina.pe/tvenvivo
$url saltillo.multimedios.com/video
$type live
"""
import logging
import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_scheme

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https://(?:www\.)?latina\.pe/tvenvivo"
))
@pluginmatcher(re.compile(
    r"https://saltillo\.multimedios\.com/video"
))
@pluginmatcher(re.compile(
    r"https://mdstrm\.com/live-stream/\w+"
))
class MDStrm(Plugin):
    @staticmethod
    def get_script_str(root, search_string, custom_pattern=None, custom_schema=None):
        if custom_pattern:
            pattern = custom_pattern
        else:
            pattern = fr"{search_string}\s*=\s*'([^']+)';"
        _schema = validate.Schema(
            validate.xml_xpath_string(
                ".//script[@type='text/javascript'][contains(text(),$search_string)]/text()",
                search_string=search_string,
            ),
            validate.none_or_all(
                re.compile(pattern),
                validate.none_or_all(validate.get(1)),
            ),
        )
        _string = _schema.validate(root)
        if not _string:
            log.debug(f"Failed to find {search_string}")
        if custom_schema:
            try:
                _string = custom_schema.validate(_string)
            except ValueError:
                pass
        return _string

    def _get_streams(self):
        p_netloc = urlparse(self.url).netloc
        if p_netloc == "mdstrm.com":
            url_iframe = self.url
        else:
            url_iframe = self.session.http.get(
                url=self.url,
                schema=validate.Schema(
                    validate.parse_html(),
                    validate.xml_xpath_string("normalize-space(.//iframe[contains(@src,'mdstrm.com')]/@src)"),
                ),
            )
            if not url_iframe:
                return

        url_iframe = update_scheme("https://", url_iframe, force=False)
        log.debug(f"iframe={url_iframe}")
        root = self.session.http.get(
            url_iframe,
            schema=validate.Schema(validate.parse_html()),
        )

        schema = validate.Schema(validate.xml_xpath_string(".//div[@id='message']/text()"))
        error_msg = schema.validate(root)
        if error_msg:
            log.error(f"{error_msg}")

        schema_options = validate.Schema(
            validate.parse_json(),
            {
                "id": str,
                "isOnline": bool,
                "src": {"hls": validate.url()},
                "type": str,
                "without_cookies": bool,
                "title": str,
            },
        )
        options = self.get_script_str(
            root,
            "window.MDSTRM.OPTIONS",
            r"window\.MDSTRM\.OPTIONS\s*=\s*({.*?});",
            custom_schema=schema_options,
        )
        if not options or not isinstance(options, dict):
            return

        sid = self.get_script_str(root, "window.MDSTRMSID")
        pid = self.get_script_str(root, "window.MDSTRMPID")
        uid = self.get_script_str(root, "window.MDSTRMUID")
        av = self.get_script_str(root, "window.VERSION")
        if not (sid and pid and uid and av):
            return

        params = {
            "sid": sid,
            "uid": uid,
            "pid": pid,
            "av": av,
            "an": "screen",
            "at": "web-app",
            "res": "1280x720",
            "dnt": "true",
            "without_cookies": "false",
        }

        schema = validate.Schema(
            validate.xml_xpath_string(
                "normalize-space(.//iframe[contains(@src,'mdstrm.com')][@id='programmatic']/@src)",
            ),
        )
        programmatic_url = schema.validate(root)
        if programmatic_url:
            programmatic_url = update_scheme("https://", programmatic_url, force=False)
            log.debug(f"programmatic_url={programmatic_url}")

            ad = self.session.http.get(
                programmatic_url,
                schema=validate.Schema(
                    validate.parse_html(),
                    validate.xml_xpath_string(".//script[contains(text(),'parent._dai_session')]/text()"),
                    validate.none_or_all(
                        re.compile(r"""parent\._dai_session\s*=\s*(?P<q>['"])(?P<dai_session>.+?)(?P=q);"""),
                        validate.none_or_all(validate.get("dai_session")),
                    ),
                ),
            )
            if ad:
                params.update({"adInsertionSessionId": ad})
            else:
                log.debug("Failed to find 'parent._dai_session'")

        log.trace(f"{params!r}")
        self.id = options["id"]
        self.title = options["title"]
        return HLSStream.parse_variant_playlist(
            self.session,
            options["src"]["hls"],
            headers={"Referer": "https://mdstrm.com/"},
            params=params,
        )


__plugin__ = MDStrm
