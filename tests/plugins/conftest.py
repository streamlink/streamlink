from tests.plugins import PluginCanHandleUrl, generic_negative_matches


def pytest_collection_modifyitems(session, config, items):  # pragma: no cover
    # remove empty parametrized tests
    session.items = list(filter(lambda item: not any(
        marker.name == "skip" and str(marker.kwargs.get("reason", "")).startswith("got empty parameter set")
        for marker in item.own_markers
    ), items))


def pytest_generate_tests(metafunc):  # pragma: no cover
    if metafunc.cls is not None and issubclass(metafunc.cls, PluginCanHandleUrl):
        if metafunc.function.__name__ == "test_can_handle_url_positive":
            metafunc.parametrize("url", metafunc.cls.should_match + [url for url, groups in metafunc.cls.should_match_groups])

        elif metafunc.function.__name__ == "test_can_handle_url_negative":
            metafunc.parametrize("url", metafunc.cls.should_not_match + generic_negative_matches)

        elif metafunc.function.__name__ == "test_capture_groups":
            metafunc.parametrize("url,groups", metafunc.cls.should_match_groups, ids=[
                f"URL={url} GROUPS={groups}"
                for url, groups in metafunc.cls.should_match_groups
            ])
