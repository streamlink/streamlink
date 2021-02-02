from streamlink.plugins.googledrive import GoogleDocs
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlGoogleDocs(PluginCanHandleUrl):
    __plugin__ = GoogleDocs

    should_match = [
        'https://drive.google.com/file/d/123123/preview?start=1',
    ]
