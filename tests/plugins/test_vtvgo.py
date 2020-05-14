import unittest

from streamlink.plugins.vtvgo import VTVgo


class TestPluginVTVgo(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://vtvgo.vn/xem-truc-tuyen-kenh-vtv1-1.html',
            'https://vtvgo.vn/xem-truc-tuyen-kenh-vtv2-2.html',
            'https://vtvgo.vn/xem-truc-tuyen-kenh-vtv3-3.html',
            'https://vtvgo.vn/xem-truc-tuyen-kenh-vtv4-4.html',
            'https://vtvgo.vn/xem-truc-tuyen-kenh-vtv5-5.html',
            'https://vtvgo.vn/xem-truc-tuyen-kenh-vtv6-6.html',
            'https://vtvgo.vn/xem-truc-tuyen-kenh-vtv7-27.html',
            'https://vtvgo.vn/xem-truc-tuyen-kenh-vtv8-36.html',
            'https://vtvgo.vn/xem-truc-tuyen-kenh-vtv9-39.html',
            'https://vtvgo.vn/xem-truc-tuyen-kenh-vtv5-t%C3%A2y-nam-b%E1%BB%99-7.html',
            'https://vtvgo.vn/xem-truc-tuyen-kenh-k%C3%AAnh-vtv5-t%C3%A2y-nguy%C3%AAn-163.html',
        ]
        for url in should_match:
            self.assertTrue(VTVgo.can_handle_url(url))

        should_not_match = [
            'https://example.com/index.html',
            # POST request will error with www.
            'https://www.vtvgo.vn/xem-truc-tuyen-kenh-vtv1-1.html',
            # POST request will error with http://
            'http://vtvgo.vn/xem-truc-tuyen-kenh-vtv1-1.html',
        ]
        for url in should_not_match:
            self.assertFalse(VTVgo.can_handle_url(url))
