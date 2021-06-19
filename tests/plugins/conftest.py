from tests.plugins import PluginCanHandleUrl, generic_negative_matches


def pytest_generate_tests(metafunc):
    if metafunc.cls is not None and issubclass(metafunc.cls, PluginCanHandleUrl):  # pragma: no branch
        if metafunc.function.__name__ == "test_can_handle_url_positive":
            metafunc.parametrize("url", metafunc.cls.should_match)
        elif metafunc.function.__name__ == "test_can_handle_url_negative":
            metafunc.parametrize("url", metafunc.cls.should_not_match + generic_negative_matches)
