from streamlink.plugin import Plugin


generic_negative_matches = [
    "http://example.com/",
    "https://example.com/",
    "https://example.com/index.html",
]


class PluginCanHandleUrl:
    __plugin__ = None

    should_match = []
    should_not_match = []

    def test_class_setup(self):
        assert issubclass(self.__plugin__, Plugin), "Test has a __plugin__ that is a subclass of streamlink.plugin.Plugin"
        assert len(self.should_match) > 0, "Test has at least one positive URL"

    # parametrized dynamically via conftest.py
    def test_can_handle_url_positive(self, url):
        assert any(matcher.pattern.match(url) for matcher in self.__plugin__.matchers), "URL matches"

    # parametrized dynamically via conftest.py
    def test_can_handle_url_negative(self, url):
        assert not any(matcher.pattern.match(url) for matcher in self.__plugin__.matchers), "URL does not match"
