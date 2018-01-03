import unittest

from streamlink.plugins.neulion import Neulion
from streamlink.plugins.neulion import js_to_json_regex_fallback


class TestRegexFallback(unittest.TestCase):
    def test_js_to_json_regex_fallback(self):
        regex_test_list = [
            {
                "data": """
                        var currentVideo = {};
                          currentVideo = {
                            id: 689825,
                            name: "All-Access: NBA in Africa 2017",
                            image: "2017/08/07/689825_es.jpg",
                            seoName: "2017/08/07/all-access-nba-africa-2017",
                            description: "It was an exciting week id...",
                            releaseDate: "2017-08-07 00:00:00.0",
                            sequence: 689825,
                            runtime: 262,
                            category: ""
                          };
                        """,
                "result": {"id": "689825", "name": "All-Access: NBA in Africa 2017"}
            },
            {
                "data": """
                        var video = {
                        id: "27687",
                        name: "5/27 Bologna v Juventus highlight",
                        description: "",
                        image: "https://neulionsmbnyc-a.akamaihd.net/u/m...",
                        type: "video"
                        };
                        """,
                "result": {"id": "27687", "name": "5/27 Bologna v Juventus highlight",  "type": "video"}
            },
            {
                "data": """
                        var video = {id:"27687", name:"5/27 Bologna v Juventus highlight", description:"", image: "https://neulionsmbnyc-a.akamaihd.net", type: "video"}
                        """,
                "result": {"id": "27687", "name": "5/27 Bologna v Juventus highlight", "type": "video"}
            },
            {
                "data": """
                        var program = {id:"50694", name:"5 najbardziej spektakularnych goli z dystansu w Bundeslidze", description:"Zobacz najlepsze trafienia w lidze niemieckiej ostatnich lat!", image: "https://neulionsmbnyc-a.akamaihd.net/, type: "video"};
                        """,
                "result": {"id": "50694", "name": "5 najbardziej spektakularnych goli z dystansu w Bundeslidze", "type": "video"}
            },
            {
                "data": """
                        <script>
                          var LOC_SWF = "http://neulionms-a.akamaihd.net/mt/v4/base/site_4/channel.swf";
                          var LOC_EPG = "http://smb.cdnak.neulion.com/fs/tennischannel/epg/tennis-channel/";
                          var g_currentDate = "2017/12/12";
                          var g_channel = {id:"19",name:"Tennis Channel",isLive:true,type:"channel"};
                        </script>
                        """,
                "result": {"id": "19", "name": "Tennis Channel", "type": "channel"}
            },
            {
                "data": """
                        {id:"68950", name:"Miracle on the Plains", description:"On April 23, 2013, the oaks at Toomer's Corner had to be removed.", image: "https://neulionsmbnyc-a.akamaihd.net/", type: "video"}
                        """,
                "result": {"id": "68950", "name": "Miracle on the Plains", "type": "video"}
            },
            {
                "data": """
                        {id:"68956", name:"When The Garden Was Eden", description:"In the early 1970s. ther: Madison Square Garden. \"When The Garden Was Eden\" (based on the book by", type: "video"};
                        """,
                "result": {"id": "68956", "name": "When The Garden Was Eden", "type": "video"}
            },
            {
                "data": """
                        {
                            'id': 762769,
                            'name': 'Phoenix Suns vs. Philadelphia 76ers - Game Highlights',
                            'image': '2017/12/31/762769_es.jpg',
                            'seoName': 'channels/highlights/381c9a84-47a9-41ac-a138-761c15afb58f.nba',
                            'description': 'Phoenix Suns vs. Philadelphia 76ers - Game Highlights',
                            'releaseDate': '2018-12-31 12:00:00.0',
                            'sequence': 762769,
                            'runtime': 301,
                            'purchaseTypeId': '3',
                            'category': 'latest'
                        }
                        """,
                "result": {"id": "762769", "name": "Phoenix Suns vs. Philadelphia 76ers - Game Highlights"}
            },
            {
                "data": """
                        {
                            id: 762769,
                            name: "Phoenix Suns vs. Philadelphia 76ers - Game Highlights",
                            image: "2017/12/31/762769_es.jpg",
                            seoName: "channels/highlights/381c9a84-47a9-41ac-a138-761c15afb58f.nba",
                            description: "Phoenix Suns vs. Philadelphia 76ers - Game Highlights",
                            releaseDate: "2018-12-31 12:00:00.0",
                            sequence: 762769,
                            runtime: 301,
                            purchaseTypeId: '3',
                            category: "latest"
                          }
                        """,
                "result": {"id": "762769", "name": "Phoenix Suns vs. Philadelphia 76ers - Game Highlights"}
            },
            {
                "data": """
                        {
                            id: 696211,
                            name: "Video Archives: Rockets vs Sonics Game 6 Hakeem 49/25 in 2OT (Pop-up)",
                            image: "2017/09/12/696211_es.jpg",
                            seoName: "video-archives-rockets-vs-sonics-game-6-hakeem-49/25-in-2otpop-up",
                            description: "Rockets vs. Supersonics",
                            releaseDate: "2017-09-12 19:36:00.0",
                            sequence: 696211,
                            runtime: 3513,
                            purchaseTypeId: '1',
                            category: "videoarchives"
                        }
                        """,
                "result": {"id": "696211", "name": "Video Archives: Rockets vs Sonics Game 6 Hakeem 49/25 in 2OT (Pop-up)"}
            },
        ]
        for test_dict in regex_test_list:
            return_data = js_to_json_regex_fallback(test_dict.get("data"))
            self.assertIsNotNone(return_data)
            self.assertDictEqual(test_dict.get("result"), return_data)


class TestPluginNeulion(unittest.TestCase):
    """Tests for neulion domains in neulion.py"""

    def test_can_handle_url(self):
        should_match = [
            "https://fanpass.co.nz/channel/sky-sport-1",
            "https://watch.nba.com/channel/nbatvlive",
            "https://watch.nba.com/video/2017/08/07/all-access-nba-africa-2017",
            "https://watch.rugbypass.com/game/raiders-at-warriors-on-08122017",
            "https://www.elevensports.be/channel/eleven-fr",
            "https://www.elevensports.lu/channel/eleven",
            "https://www.elevensports.pl/channel/eleven",
            "https://www.elevensports.sg/channel/eleven",
            "https://www.elevensports.tw/channel/eleven-zh",
            "https://www.elevensports.tw/video/5/27-bologna-v-juventus-highlight",
            "https://www.tennischanneleverywhere.com/channel/tennis-channel",
            "https://www.ufc.tv/video/ufc-auckland-2017"
        ]
        for url in should_match:
            self.assertTrue(Neulion.can_handle_url(url))

        should_not_match = [
            "https://www.fanpass.co.nz/channel/sky-sport-1",
            "https://nba.com/channel/nbatvlive",
            "https://nba.com/video/2017/08/07/all-access-nba-africa-2017",
            "https://rugbypass.com/game/raiders-at-warriors-on-08122017",
            "https://elevensports.be/channel/eleven-fr",
            "https://elevensports.lu/channel/eleven",
            "https://elevensports.pl/channel/eleven",
            "https://elevensports.sg/channel/eleven",
            "https://elevensports.tw/channel/eleven-zh",
            "https://elevensports.tw/video/5/27-bologna-v-juventus-highlight",
            "https://tennischanneleverywhere.com/channel/tennis-channel",
            "https://ufc.tv/video/ufc-auckland-2017"
        ]
        for url in should_not_match:
            self.assertFalse(Neulion.can_handle_url(url))

    def test_domain(self):
        regex_test_list = [
            {
                "data": "https://fanpass.co.nz/channel/sky-sport-1",
                "result": "fanpass.co.nz"
            },
            {
                "data": "https://watch.nba.com/video/2017/08/07/all-access-nba-africa-2017",
                "result": "watch.nba.com"
            },
            {
                "data": "https://watch.rugbypass.com/game/raiders-at-warriors-on-08122017",
                "result": "watch.rugbypass.com"
            },
            {
                "data": "https://www.elevensports.be/channel/eleven-fr",
                "result": "www.elevensports.be"
            },
            {
                "data": "https://www.tennischanneleverywhere.com/channel/tennis-channel",
                "result": "www.tennischanneleverywhere.com"
            }
        ]
        for test_dict in regex_test_list:
            test_class = Neulion(test_dict.get("data"))
            _domain = test_class._domain
            self.assertIsNotNone(_domain)
            self.assertEqual(test_dict.get("result"), _domain)

    def test_vtype(self):
        regex_test_list = [
            {
                "data": "https://fanpass.co.nz/channel/sky-sport-1",
                "result": "channel"
            },
            {
                "data": "https://watch.nba.com/video/2017/08/07/all-access-nba-africa-2017",
                "result": "video"
            },
            {
                "data": "https://watch.rugbypass.com/game/raiders-at-warriors-on-08122017",
                "result": "game"
            },
            {
                "data": "https://www.elevensports.be/channel/eleven-fr",
                "result": "channel"
            },
            {
                "data": "https://www.tennischanneleverywhere.com/channel/tennis-channel",
                "result": "channel"
            }
        ]

        for test_dict in regex_test_list:
            test_class = Neulion(test_dict.get("data"))
            _vtype = test_class._vtype
            self.assertIsNotNone(_vtype)
            self.assertEqual(test_dict.get("result"), _vtype)
