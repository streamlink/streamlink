import unittest

from streamlink.plugins.qq import QQ


class TestPluginQQ(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://live.qq.com/10003715",
            "http://live.qq.com/10007266",
            "http://live.qq.com/10039165",
            "http://m.live.qq.com/10003715",
            "http://m.live.qq.com/10007266",
            "http://m.live.qq.com/10039165"
        ]
        for url in should_match:
            self.assertTrue(QQ.can_handle_url(url))

        should_not_match = [
            "http://live.qq.com/",
            "http://qq.com/",
            "http://www.qq.com/"
        ]
        for url in should_not_match:
            self.assertFalse(QQ.can_handle_url(url))

    def test_url_re(self):
        regex_match_list = [
            {
                "data": "http://live.qq.com/10003715",
                "result": "10003715"
            },
            {
                "data": "http://m.live.qq.com/10039165",
                "result": "10039165"
            }
        ]
        for m_test in regex_match_list:
            m = QQ._url_re.match(m_test.get("data"))
            self.assertIsNotNone(m)
            self.assertEqual(m_test.get("result"), m.group("room_id"))
