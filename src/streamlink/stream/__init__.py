# ruff: noqa: RUF067
from streamlink.compat import deprecated


_msg = "Importing from the 'streamlink.stream' package has been deprecated. Import from its submodules instead."

deprecated({
    "DASHStream": ("streamlink.stream.dash.dash", None, _msg),
    "MuxedStream": ("streamlink.stream.ffmpegmux", None, _msg),
    "HLSStream": ("streamlink.stream.hls.hls", None, _msg),
    "MuxedHLSStream": ("streamlink.stream.hls.hls", None, _msg),
    "HTTPStream": ("streamlink.stream.http", None, _msg),
    "Stream": ("streamlink.stream.stream", None, _msg),
    "StreamIO": ("streamlink.stream.stream", None, _msg),
    "StreamIOIterWrapper": ("streamlink.stream.wrappers", None, _msg),
    "StreamIOThreadWrapper": ("streamlink.stream.wrappers", None, _msg),
    "StreamIOWrapper": ("streamlink.stream.wrappers", None, _msg),
})

del _msg
