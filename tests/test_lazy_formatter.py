import unittest
from unittest.mock import MagicMock

from streamlink.utils import LazyFormatter


class TestLazyFormat(unittest.TestCase):
    def _get_fake_plugin(self):
        plugin = MagicMock()
        plugin.get_title.return_value = "title"
        plugin.get_author.return_value = "author"
        plugin.get_game.return_value = "game"
        plugin.url = "url"

        return plugin

    def test_format_lazy_title(self):
        plugin = self._get_fake_plugin()

        res = LazyFormatter.format("{title}",
                                   title=plugin.get_title,
                                   author=plugin.get_author,
                                   game=plugin.get_game,
                                   url=plugin.url)

        self.assertEqual("title", res)

        plugin.get_title.assert_called()
        plugin.get_author.assert_not_called()
        plugin.get_game.assert_not_called()

    def test_format_lazy_title_author(self):
        plugin = self._get_fake_plugin()

        res = LazyFormatter.format("{title} - {author}",
                                   title=plugin.get_title,
                                   author=plugin.get_author,
                                   game=plugin.get_game,
                                   url=plugin.url)

        self.assertEqual("title - author", res)

        plugin.get_title.assert_called()
        plugin.get_author.assert_called()

        plugin.get_game.assert_not_called()

    def test_format_lazy_title_author_game(self):
        plugin = self._get_fake_plugin()

        res = LazyFormatter.format("{title} - {author} - {game}",
                                   title=plugin.get_title,
                                   author=plugin.get_author,
                                   game=plugin.get_game,
                                   url=plugin.url)

        self.assertEqual("title - author - game", res)

        plugin.get_title.assert_called()
        plugin.get_author.assert_called()
        plugin.get_game.assert_called()

    def test_format_lazy_title_author_game_url(self):
        plugin = self._get_fake_plugin()

        res = LazyFormatter.format("{title} - {author} - {game} - {url}",
                                   title=plugin.get_title,
                                   author=plugin.get_author,
                                   game=plugin.get_game,
                                   url=plugin.url)

        self.assertEqual("title - author - game - url", res)

        plugin.get_title.assert_called()
        plugin.get_author.assert_called()
        plugin.get_game.assert_called()

    def test_format_lazy_title_not_callable(self):
        res = LazyFormatter.format("{title}",
                                   title="title")

        self.assertEqual("title", res)

    def test_format_lazy_title_default(self):
        plugin = self._get_fake_plugin()
        plugin.get_title.return_value = None
        res = LazyFormatter.format("{title}",
                                   title=lambda: plugin.get_title() or "default_title")

        self.assertEqual("default_title", res)

        plugin.get_title.assert_called()
        plugin.get_author.assert_not_called()
        plugin.get_game.assert_not_called()

    def test_format_fmt_prop(self):
        self.assertEqual("test",
                         LazyFormatter.format("{fmt}", fmt="test"))

    def test_format_invalid_args(self):
        self.assertRaises(TypeError, LazyFormatter.format, fmt="test")
        self.assertRaises(TypeError, LazyFormatter.format, "test", "test2", fmt="test")
