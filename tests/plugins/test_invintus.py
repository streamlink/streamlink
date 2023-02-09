from streamlink.plugins.invintus import InvintusMedia
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlInvintusMedia(PluginCanHandleUrl):
    __plugin__ = InvintusMedia

    should_match = [
        "https://player.invintus.com/?clientID=9375922947&eventID=2020031185",
        "https://player.invintus.com/?clientID=9375922947&eventID=2020031184",
        "https://player.invintus.com/?clientID=9375922947&eventID=2020031183",
        "https://player.invintus.com/?clientID=9375922947&eventID=2020031182",
        "https://player.invintus.com/?clientID=9375922947&eventID=2020031181",
    ]
