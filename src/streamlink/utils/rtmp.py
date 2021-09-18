from streamlink.compat import urlparse


def escape_librtmp(value):  # pragma: no cover
    if isinstance(value, bool):
        value = "1" if value else "0"
    if isinstance(value, int):
        value = str(value)

    # librtmp expects some characters to be escaped
    value = value.replace("\\", "\\5c")
    value = value.replace(" ", "\\20")
    value = value.replace('"', "\\22")

    return value


def rtmpparse(url):
    parse = urlparse(url)
    netloc = "{0}:{1}".format(parse.hostname, parse.port or 1935)
    split = list(filter(None, parse.path.split("/")))
    playpath = None
    if len(split) > 2:
        app = "/".join(split[:2])
        playpath = "/".join(split[2:])
    elif len(split) == 2:
        app, playpath = split
    else:
        app = split[0]

    if len(parse.query) > 0:
        playpath += "?{0}".format(parse.query)

    tcurl = "{0}://{1}/{2}".format(parse.scheme, netloc, app)

    return tcurl, playpath
