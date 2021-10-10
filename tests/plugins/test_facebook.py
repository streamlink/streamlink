from streamlink.plugins.facebook import Facebook
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlFacebook(PluginCanHandleUrl):
    __plugin__ = Facebook

    should_match = [
        "https://www.facebook.com/nos/videos/1725546430794241/",
        "https://www.facebook.com/nytfood/videos/1485091228202006/",
        "https://www.facebook.com/SporTurkTR/videos/798553173631138/",
        "https://www.facebook.com/119555411802156/posts/500665313691162/",
        "https://www.facebookwkhpilnemxj7asaniu7vnjjbiltxjqhye3mhbshg7kx5tfyd.onion/SporTurkTR/videos/798553173631138/",
    ]

    should_not_match = [
        "https://www.facebook.com",
    ]
