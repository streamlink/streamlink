import importlib.abc
import importlib.util
from contextlib import nullcontext
from textwrap import dedent
from types import ModuleType

import pytest

from streamlink.exceptions import StreamlinkDeprecationWarning


class TestDeprecated:
    class _Loader(importlib.abc.SourceLoader):
        def __init__(self, filename: str, content: str):
            super().__init__()
            self._filename = filename
            self._content = content

        def get_filename(self, fullname):
            return self._filename

        def get_data(self, path):
            return self._content

    @pytest.fixture()
    def module(self, request: pytest.FixtureRequest):
        content = getattr(request, "param", "")
        loader = self._Loader("mocked_module.py", content)
        spec = importlib.util.spec_from_loader("mocked_module", loader)
        assert spec
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)

        return mod

    @pytest.mark.parametrize(
        ("module", "attr", "has_attr", "warnings", "raises_on_missing"),
        [
            pytest.param(
                dedent("""
                    from streamlink.compat import deprecated
                    deprecated({
                        "Streamlink": ("streamlink.session.Streamlink", None, None),
                    })
                """).strip(),
                "Streamlink",
                False,
                [(__file__, StreamlinkDeprecationWarning, "'mocked_module.Streamlink' has been deprecated")],
                pytest.raises(AttributeError),
                id="import-path",
            ),
            pytest.param(
                dedent("""
                    from streamlink.compat import deprecated
                    deprecated({
                        "Streamlink": ("streamlink.session.Streamlink", None, "custom warning"),
                    })
                """).strip(),
                "Streamlink",
                False,
                [(__file__, StreamlinkDeprecationWarning, "custom warning")],
                pytest.raises(AttributeError),
                id="import-path-custom-msg",
            ),
            pytest.param(
                dedent("""
                    from streamlink.compat import deprecated
                    from streamlink.session import Streamlink
                    deprecated({
                        "Streamlink": (None, Streamlink, None),
                    })
                """).strip(),
                "Streamlink",
                False,
                [(__file__, StreamlinkDeprecationWarning, "'mocked_module.Streamlink' has been deprecated")],
                pytest.raises(AttributeError),
                id="import-obj",
            ),
            pytest.param(
                dedent("""
                    from streamlink.compat import deprecated
                    from streamlink.session import Streamlink
                    deprecated({
                        "Streamlink": (None, Streamlink, "custom warning"),
                    })
                """).strip(),
                "Streamlink",
                False,
                [(__file__, StreamlinkDeprecationWarning, "custom warning")],
                pytest.raises(AttributeError),
                id="import-obj-custom-msg",
            ),
            pytest.param(
                dedent("""
                    from streamlink.compat import deprecated
                    foo = 1
                    deprecated({
                        "Streamlink": ("streamlink.session.Streamlink", None, None),
                    })
                """).strip(),
                "foo",
                True,
                [],
                pytest.raises(AttributeError),
                id="no-warning-has-attr",
            ),
            pytest.param(
                dedent("""
                    from streamlink.compat import deprecated
                    def __getattr__(name):
                        return "foo"
                    deprecated({
                        "Streamlink": ("streamlink.session.Streamlink", None, None),
                    })
                """).strip(),
                "foo",
                False,
                [],
                nullcontext(),
                id="no-warning-has-getattr",
            ),
        ],
        indirect=["module"],
    )
    def test_deprecated(
        self,
        recwarn: pytest.WarningsRecorder,
        module: ModuleType,
        attr: str,
        has_attr: bool,
        warnings: list,
        raises_on_missing: nullcontext,
    ):
        assert recwarn.list == []

        assert (attr in dir(module)) is has_attr
        assert "deprecated" not in dir(module)

        assert getattr(module, attr)
        assert [(record.filename, record.category, str(record.message)) for record in recwarn.list] == warnings

        with raises_on_missing:
            # noinspection PyStatementEffect
            module.does_not_exist  # noqa: B018
