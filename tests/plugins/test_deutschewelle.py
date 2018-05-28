# -*- coding: utf-8 -*-

import unittest

from streamlink.plugins.deutschewelle import DeutscheWelle


class TestPluginDeutscheWelle(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(DeutscheWelle.can_handle_url("http://www.dw.com/en/media-center/live-tv/s-100825"))
        self.assertTrue(DeutscheWelle.can_handle_url("http://www.dw.com/fr/médiathèque/direct-tv/s-100948?channel=5"))
        self.assertTrue(DeutscheWelle.can_handle_url("http://www.dw.com/de/tim-bendzko-deutsch-pop-darling-auf-tour/av-39101077"))
        self.assertTrue(DeutscheWelle.can_handle_url("http://www.dw.com/de/trump-sagt-nein-die-welt-schüttelt-den-kopf/av-39096724"))
        self.assertTrue(DeutscheWelle.can_handle_url("http://www.dw.com/el/ο-τραμπ-θεωρεί-την-ευρώπη-ανταγωνιστή-όχι-εταίρο/av-39103742"))
        self.assertTrue(DeutscheWelle.can_handle_url("http://www.dw.com/ar/أي-البروتينات-صحية-الحيوانية-أم-النباتية/av-39095317"))

        # shouldn't match
        self.assertFalse(DeutscheWelle.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(DeutscheWelle.can_handle_url("http://www.youtube.com/"))
