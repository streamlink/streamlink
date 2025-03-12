from __future__ import annotations

from collections.abc import Sequence
from re import Match
from typing import TYPE_CHECKING

import pytest

from streamlink.plugin.plugin import Matcher, Plugin


if TYPE_CHECKING:
    from typing_extensions import TypeAlias


generic_negative_matches = [
    "http://example.com/",
    "https://example.com/",
    "https://example.com/index.html",
]


TUrl: TypeAlias = str
TName: TypeAlias = str
TUrlNamed: TypeAlias = "tuple[TName, TUrl]"
TUrlOrNamedUrl: TypeAlias = "TUrl | TUrlNamed"
TMatchGroup: TypeAlias = "dict[str, str] | Sequence[str | None]"


_plugin_can_handle_url_classnames: set[str] = set()


class PluginCanHandleUrl:
    __plugin__: type[Plugin]

    should_match: list[TUrlOrNamedUrl] = []
    """
    A list of URLs that should match any of the plugin's URL regexes.
    URL can be a tuple of a matcher name and the URL itself.

    Example:
    should_match = [
        "https://foo",
        ("bar", "https://bar"),
    ]
    """

    should_match_groups: list[tuple[TUrlOrNamedUrl, TMatchGroup]] = []
    """
    A list of URL+capturegroup tuples, where capturegroup can be a dict (re.Match.groupdict()) or a tuple (re.Match.groups()).
    URL can be a tuple of a matcher name and the URL itself.

    URLs defined in this list automatically get appended to the should_match list.
    Values in capturegroup dictionaries that are None get ignored when comparing and must be omitted in the test fixtures.

    Example:
    [
        ("https://foo", {"foo": "foo"}),
        ("https://bar", ("bar", None)),
        ("https://bar/baz", ("bar", "baz")),
        (("qux", "https://qux"), {"qux": "qux"}),
    ]
    """

    should_not_match: list[TUrl] = []
    """
    A list of URLs that should not match any of the plugin's URL regexes.
    Generic negative URL matches are appended to this list automatically and must not be defined.

    Example:
    [
        "https://foo",
    ]
    """

    # ---- test utils

    @classmethod
    def matchers(cls) -> list[Matcher]:
        empty: list[Matcher] = []
        return cls.__plugin__.matchers or empty

    @classmethod
    def urls_all(cls) -> list[TUrlOrNamedUrl]:
        return cls.should_match + [item for item, groups in cls.should_match_groups]

    @classmethod
    def urls_unnamed(cls) -> list[TUrl]:
        return [item for item in cls.urls_all() if type(item) is str]

    @classmethod
    def urls_named(cls) -> list[TUrlNamed]:
        return [item for item in cls.urls_all() if type(item) is tuple]

    @classmethod
    def urlgroups_unnamed(cls) -> list[tuple[TUrl, TMatchGroup]]:
        return [(item, groups) for item, groups in cls.should_match_groups if type(item) is str]

    @classmethod
    def urlgroups_named(cls) -> list[tuple[TName, TUrl, TMatchGroup]]:
        return [(item[0], item[1], groups) for item, groups in cls.should_match_groups if type(item) is tuple]

    @classmethod
    def urls_negative(cls) -> list[TUrl]:
        return cls.should_not_match + generic_negative_matches

    @staticmethod
    def _get_match_groups(match: Match, grouptype: type[TMatchGroup]) -> TMatchGroup:
        return (
            # ignore None values in capture group dicts
            {k: v for k, v in match.groupdict().items() if v is not None}
            if grouptype is dict
            # capture group tuples
            else match.groups()
        )

    # ---- misc fixtures

    @pytest.fixture()
    def classnames(self):
        yield _plugin_can_handle_url_classnames
        _plugin_can_handle_url_classnames.add(self.__class__.__name__)

    # ---- tests

    def test_class_setup(self):
        assert hasattr(self, "__plugin__"), "Test has a __plugin__ attribute"
        assert issubclass(self.__plugin__, Plugin), "Test has a __plugin__ that is a subclass of the Plugin class"
        assert self.should_match or self.should_match_groups, "Test has at least one positive URL"

    def test_class_name(self, classnames: set[str]):
        assert self.__class__.__name__ not in classnames

    # ---- all tests below are parametrized dynamically via conftest.py

    def test_all_matchers_match(self, matcher: Matcher):
        assert any(  # pragma: no branch
            matcher.pattern.match(url)
            for url in [(item if type(item) is str else item[1]) for item in self.urls_all()]
        ), "Matcher matches at least one URL"  # fmt: skip

    def test_all_named_matchers_have_tests(self, matcher: Matcher):
        assert any(  # pragma: no branch
            name == matcher.name
            for name, url in self.urls_named()
        ), "Named matcher does have a test"  # fmt: skip

    def test_url_matches_positive_unnamed(self, url: TUrl):
        assert any(  # pragma: no branch
            matcher.pattern.match(url)
            for matcher in self.matchers()
        ), "Unnamed URL test matches at least one unnamed matcher"  # fmt: skip

    def test_url_matches_positive_named(self, name: TName, url: TUrl):
        assert [  # pragma: no branch
            matcher.name
            for matcher in self.matchers()
            if matcher.pattern.match(url)
        ] == [name], "Named URL test exactly matches one named matcher"  # fmt: skip

    def test_url_matches_groups_unnamed(self, url: TUrl, groups: TMatchGroup):
        matches = [matcher.pattern.match(url) for matcher in self.matchers() if matcher.name is None]
        match = next((match for match in matches if match), None)  # pragma: no branch
        result = None if not match else self._get_match_groups(match, type(groups))
        assert result == groups, "URL capture groups match the results of the first matching unnamed matcher"

    def test_url_matches_groups_named(self, name: TName, url: TUrl, groups: TMatchGroup):
        matches = [(matcher.name, matcher.pattern.match(url)) for matcher in self.matchers() if matcher.name is not None]
        mname, match = next(((mname, match) for mname, match in matches if match), (None, None))  # pragma: no branch
        result = None if not match else self._get_match_groups(match, type(groups))
        assert (mname, result) == (name, groups), "URL capture groups match the results of the matching named matcher"

    def test_url_matches_negative(self, url: TUrl):
        assert not any(  # pragma: no branch
            matcher.pattern.match(url)
            for matcher in self.matchers()
        ), "URL does not match any matcher"  # fmt: skip
