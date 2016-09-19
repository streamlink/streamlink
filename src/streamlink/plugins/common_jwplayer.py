import re

from functools import partial

from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import parse_json

__all__ = ["parse_playlist"]

_playlist_re = re.compile("\(?\{.*playlist: (\[.*\]),.*?\}\)?;", re.DOTALL)
_js_to_json = partial(re.compile("(\w+):\s").sub, r'"\1":')

_playlist_schema = validate.Schema(
    validate.transform(_playlist_re.search),
    validate.any(
        None,
        validate.all(
            validate.get(1),
            validate.transform(_js_to_json),
            validate.transform(parse_json),
            [{
                "sources": [{
                    "file": validate.text,
                    validate.optional("label"): validate.text
                }]
            }]
        )
    )
)


def parse_playlist(res):
    """Attempts to parse a JWPlayer playlist in a HTTP response body."""
    return _playlist_schema.validate(res.text)
