from streamlink.plugins.pluto import Pluto
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPluto(PluginCanHandleUrl):
    __plugin__ = Pluto

    should_match = [
        'http://www.pluto.tv/live-tv/channel-lineup',
        'http://pluto.tv/live-tv/channel',
        'http://pluto.tv/live-tv/channel/',
        'https://pluto.tv/live-tv/red-bull-tv-2',
        'https://pluto.tv/live-tv/4k-tv',
        'http://www.pluto.tv/on-demand/series/leverage/season/1/episode/the-nigerian-job-2009-1-1',
        'http://pluto.tv/on-demand/series/fear-factor-usa-(lf)/season/5/episode/underwater-safe-bob-car-ramp-2004-5-3',
        'https://www.pluto.tv/on-demand/movies/dr.-no-1963-1-1',
        'http://pluto.tv/on-demand/movies/the-last-dragon-(1985)-1-1',
        'http://www.pluto.tv/lc/live-tv/channel-lineup',
        'http://pluto.tv/lc/live-tv/channel',
        'http://pluto.tv/lc/live-tv/channel/',
        'https://pluto.tv/lc/live-tv/red-bull-tv-2',
        'https://pluto.tv/lc/live-tv/4k-tv',
        'http://www.pluto.tv/lc/on-demand/series/leverage/season/1/episode/the-nigerian-job-2009-1-1',
        'http://pluto.tv/lc/on-demand/series/fear-factor-usa-(lf)/season/5/episode/underwater-safe-bob-car-ramp-2004-5-3',
        'https://www.pluto.tv/lc/on-demand/movies/dr.-no-1963-1-1',
        'https://www.pluto.tv/lc/on-demand/movies/dr.-no-1963-1-1/',
        'http://pluto.tv/lc/on-demand/movies/the-last-dragon-(1985)-1-1',
        'http://pluto.tv/lc/on-demand/movies/the-last-dragon-(1985)-1-1/',
        'https://pluto.tv/en/on-demand/series/great-british-menu-ptv1/episode/north-west-fish-2009-5-7-ptv1',
        'https://pluto.tv/en/on-demand/series/great-british-menu-ptv1/episode/north-west-fish-2009-5-7-ptv1/',
        'https://www.pluto.tv/en/on-demand/series/great-british-menu-ptv1/episode/north-west-fish-2009-5-7-ptv1',
        'https://www.pluto.tv/en/on-demand/series/great-british-menu-ptv1/episode/north-west-fish-2009-5-7-ptv1/',
    ]

    should_not_match = [
        'https://fake.pluto.tv/live-tv/hello',
        'http://www.pluto.tv/live-tv/channel-lineup/extra',
        'https://www.pluto.tv/live-tv',
        'https://pluto.tv/live-tv',
        'https://www.pluto.com/live-tv/swag',
        'http://pluto.tv/movies/dr.-no-1963-1-1',
        'http://pluto.tv/on-demand/movies/dr.-no-1/963-1-1',
        'http://pluto.tv/on-demand/series/dr.-no-1963-1-1',
        'http://pluto.tv/on-demand/movies/leverage/season/1/episode/the-nigerian-job-2009-1-1',
        'http://pluto.tv/on-demand/fear-factor-usa-(lf)/season/5/episode/underwater-safe-bob-car-ramp-2004-5-3',
        'https://fake.pluto.tv/lc/live-tv/hello',
        'http://www.pluto.tv/lc/live-tv/channel-lineup/extra',
        'https://www.pluto.tv/lc/live-tv',
        'https://pluto.tv/lc/live-tv',
        'https://www.pluto.com/lc/live-tv/swag',
        'http://pluto.tv/lc/movies/dr.-no-1963-1-1',
        'http://pluto.tv/lc/on-demand/movies/dr.-no-1/963-1-1',
        'http://pluto.tv/lc/on-demand/series/dr.-no-1963-1-1',
        'http://pluto.tv/lc/on-demand/movies/leverage/season/1/episode/the-nigerian-job-2009-1-1',
        'http://pluto.tv/lc/on-demand/fear-factor-usa-(lf)/season/5/episode/underwater-safe-bob-car-ramp-2004-5-3',
        'https://pluto.tv/en/on-demand/series/great-british-menu-ptv1/episode/north-west-fish-2009-5-7-ptv1/extra',
        'https://pluto.tv/en/on-demand/series/great-british-menu-ptv1/season/5/episode/north-west-fish-2009-5-7-ptv1/extra',
        'https://www.pluto.tv/en/on-demand/series/great-british-menu-ptv1/episode/north-west-fish-2009-5-7-ptv1/extra',
        'https://www.pluto.tv/en/on-demand/series/great-british-menu-ptv1/season/5/episode/north-west-fish-2009-5-7-ptv1/extra',
    ]
