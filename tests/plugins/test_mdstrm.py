from streamlink.plugins.mdstrm import MDStrm
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlMDStrm(PluginCanHandleUrl):
    __plugin__ = MDStrm

    should_match = [
        "https://mdstrm.com/live-stream/57b4dbf5dbbfc8f16bb63ce1",
        "https://mdstrm.com/live-stream/5a7b1e63a8da282c34d65445",
        "https://mdstrm.com/live-stream/5ce7109c7398b977dc0744cd",
        "https://mdstrm.com/live-stream/60b578b060947317de7b57ac",
        "https://mdstrm.com/live-stream/61e1e088d04d7744686afc42",
        "https://saltillo.multimedios.com/video/monterrey-tv-en-vivo/v7567",
        "https://www.latina.pe/tvenvivo",
    ]
