from streamlink.plugins.tvazteca import TVAzteca
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTVAzteca(PluginCanHandleUrl):
    __plugin__ = TVAzteca

    should_match = [
        ("tvazteca", "https://www.tvazteca.com/azteca7/peliculas/envivo"),
        ("tvazteca", "https://www.tvazteca.com/aztecanoticias/transmisiones-especiales-fia"),
        ("adn40", "https://www.adn40.mx/tv-en-vivo/"),
        (
            "adn40",
            "https://www.adn40.mx/videoteca/2026-05-12/sashenka-gutierrez-detras-de-la-lente-que-retrata-el-poder-la-protesta-y-la-realidad-de-mexico/",
        ),
        ("envivo_live", "https://envivo.tvazteca.com/watch/live/6994be4d5caab0723aaab37c"),
        ("envivo_vod", "https://envivo.tvazteca.com/watch/media/un-dia-para-vivir-querida-mama"),
        ("envivo_vod", "https://envivo.tvazteca.com/watch/media/615a01f48d57e30df2f84daf"),
    ]
