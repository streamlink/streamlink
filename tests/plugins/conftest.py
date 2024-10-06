from __future__ import annotations

from collections.abc import Callable

import pytest

from streamlink.plugin.plugin import Matcher
from tests.plugins import PluginCanHandleUrl


def pytest_collection_modifyitems(items: list[pytest.Item]):  # pragma: no cover
    # remove empty parametrized tests
    items[:] = [
        item
        for item in items
        if not any(
            marker.name == "skip" and str(marker.kwargs.get("reason", "")).startswith("got empty parameter set")
            for marker in item.own_markers
        )
    ]


def pytest_generate_tests(metafunc: pytest.Metafunc):
    if metafunc.cls is not None and issubclass(metafunc.cls, PluginCanHandleUrl):
        name: str = f"_parametrize_plugincanhandleurl_{metafunc.function.__name__}"
        parametrizer: Callable[[pytest.Metafunc], None] | None = globals().get(name)
        if parametrizer:
            parametrizer(metafunc)


def _parametrize_plugincanhandleurl_test_all_matchers_match(metafunc: pytest.Metafunc):
    matchers: list[tuple[int, Matcher]] = list(enumerate(metafunc.cls.matchers()))
    metafunc.parametrize(
        "matcher",
        [m for i, m in matchers],
        ids=[m.name or f"#{i}" for i, m in matchers],
    )


def _parametrize_plugincanhandleurl_test_all_named_matchers_have_tests(metafunc: pytest.Metafunc):
    matchers: list[Matcher] = [m for m in metafunc.cls.matchers() if m.name is not None]
    metafunc.parametrize(
        "matcher",
        matchers,
        ids=[m.name for m in matchers],
    )


def _parametrize_plugincanhandleurl_test_url_matches_positive_unnamed(metafunc: pytest.Metafunc):
    metafunc.parametrize(
        "url",
        metafunc.cls.urls_unnamed(),
    )


def _parametrize_plugincanhandleurl_test_url_matches_positive_named(metafunc: pytest.Metafunc):
    urls = metafunc.cls.urls_named()
    metafunc.parametrize(
        "name,url",
        urls,
        ids=[f"NAME={name} URL={url}" for name, url in urls],
    )


def _parametrize_plugincanhandleurl_test_url_matches_groups_unnamed(metafunc: pytest.Metafunc):
    urlgroups = metafunc.cls.urlgroups_unnamed()
    metafunc.parametrize(
        "url,groups",
        urlgroups,
        ids=[f"URL={url} GROUPS={groups}" for url, groups in urlgroups],
    )


def _parametrize_plugincanhandleurl_test_url_matches_groups_named(metafunc: pytest.Metafunc):
    urlgroups = metafunc.cls.urlgroups_named()
    metafunc.parametrize(
        "name,url,groups",
        urlgroups,
        ids=[f"NAME={name} URL={url} GROUPS={groups}" for name, url, groups in urlgroups],
    )


def _parametrize_plugincanhandleurl_test_url_matches_negative(metafunc: pytest.Metafunc):
    metafunc.parametrize(
        "url",
        metafunc.cls.urls_negative(),
    )
