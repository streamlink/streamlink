from typing import Dict, List, Sequence, Tuple, Type, Union

from streamlink.plugin import Plugin


generic_negative_matches = [
    "http://example.com/",
    "https://example.com/",
    "https://example.com/index.html",
]


class PluginCanHandleUrl:
    __plugin__: Type[Plugin]

    # A list of URLs that should match any of the plugin's URL regexes.
    #   ["https://foo", "https://bar"]
    should_match: List[str] = []

    # A list of URL+capturegroup tuples, where capturegroup can be a dict (re.Match.groupdict()) or a tuple (re.Match.groups()).
    # URLs defined in this list automatically get appended to the should_match list.
    # Values in capturegroup dictionaries that are None get ignored when comparing and can be omitted in the test fixtures.
    #   [("https://foo", {"foo": "foo"}), ("https://bar", ("bar", None))]
    should_match_groups: List[Union[Tuple[str, Dict], Tuple[str, Sequence]]] = []

    # A list of URLs that should not match any of the plugin's URL regexes.
    #   ["https://foo", "https://bar"]
    should_not_match: List[str] = []

    def test_class_setup(self):
        assert issubclass(self.__plugin__, Plugin), "Test has a __plugin__ that is a subclass of streamlink.plugin.Plugin"
        assert len(self.should_match) + len(self.should_match_groups) > 0, "Test has at least one positive URL"

    def test_matchers(self):
        should_match = self.should_match + [url for url, groups in self.should_match_groups]
        assert all(
            any(
                matcher.pattern.match(url)
                for url in should_match
            )
            for matcher in self.__plugin__.matchers
        ), "All plugin matchers should match"

    # parametrized dynamically via conftest.py
    def test_can_handle_url_positive(self, url):
        assert any(  # pragma: no branch
            matcher.pattern.match(url)
            for matcher in self.__plugin__.matchers
        ), "URL matches"

    # parametrized dynamically via conftest.py
    def test_can_handle_url_negative(self, url):
        assert not any(  # pragma: no branch
            matcher.pattern.match(url)
            for matcher in self.__plugin__.matchers
        ), "URL does not match"

    # parametrized dynamically via conftest.py
    def test_capture_groups(self, url, groups):
        for matcher in self.__plugin__.matchers:
            match = matcher.pattern.match(url)
            if match:  # pragma: no branch
                res = (
                    # ignore None values in capture group dicts
                    {k: v for k, v in match.groupdict().items() if v is not None}
                    if type(groups) is dict else
                    # capture group tuples
                    match.groups()
                )
                assert res == groups, "URL capture groups match"
