import re
import shutil
from pathlib import Path

import pytest

from build_backend.onbuild import onbuild


try:
    # noinspection PyProtectedMember
    from versioningit.onbuild import SetuptoolsFileProvider  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    _HAS_ONBUILD_FILE_PROVIDER = False
else:
    _HAS_ONBUILD_FILE_PROVIDER = True


PROJECT_ROOT = Path(__file__).parents[1]


@pytest.fixture()
def template_fields(request: pytest.FixtureRequest) -> dict:
    template_fields = {
        "version": "1.2.3+fake",
    }
    template_fields.update(getattr(request, "param", {}))

    return template_fields


@pytest.fixture(autouse=True)
def build(request: pytest.FixtureRequest, tmp_path: Path, template_fields: dict) -> Path:
    param = getattr(request, "param", {})
    is_source = param.get("is_source", True)
    pkg_dir = tmp_path / "src" if is_source else tmp_path

    (pkg_dir / "streamlink").mkdir(parents=True)
    shutil.copy(PROJECT_ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    shutil.copy(PROJECT_ROOT / "setup.py", tmp_path / "setup.py")

    # Lookup for the path from the root source directory
    if Path(PROJECT_ROOT / "src" / "streamlink" / "_version.py").exists():
        shutil.copy(PROJECT_ROOT / "src" / "streamlink" / "_version.py", pkg_dir / "streamlink" / "_version.py")
    else:  # pragma: no cover
        # We didn't find it, use the build location
        shutil.copy(PROJECT_ROOT / "streamlink" / "_version.py", pkg_dir / "streamlink" / "_version.py")

    options = dict(
        is_source=is_source,
        template_fields=template_fields,
        params={},
    )
    if _HAS_ONBUILD_FILE_PROVIDER:
        options["file_provider"] = SetuptoolsFileProvider(build_dir=tmp_path)
    else:  # pragma: no cover
        options["build_dir"] = tmp_path

    onbuild(**options)

    return tmp_path


@pytest.mark.parametrize("build", [pytest.param({"is_source": True}, id="is_source=True")], indirect=True)
def test_sdist(build: Path):
    assert re.search(
        r"^(\s*)# (\"versioningit\b.+?\",).*$",
        (build / "pyproject.toml").read_text(encoding="utf-8"),
        re.MULTILINE,
    ), "versioningit is not a build-requirement"
    assert re.search(
        # Check for any version string, and not just the fake one,
        # because tests can be run from the sdist where the version string was already set.
        # The onbuild hook does only replace the template in `setup.py`.
        r"^(\s*)(version=\"[^\"]+\",).*$",
        (build / "setup.py").read_text(encoding="utf-8"),
        re.MULTILINE,
    ), "setup() call defines a static version string"
    assert (
        (build / "src" / "streamlink" / "_version.py").read_text(encoding="utf-8")
        == '__version__ = "1.2.3+fake"\n'
    ), "streamlink._version exports a static version string"  # fmt: skip


@pytest.mark.parametrize("build", [pytest.param({"is_source": False}, id="is_source=False")], indirect=True)
def test_bdist(build: Path):
    assert (
        (build / "pyproject.toml").read_text(encoding="utf-8") == (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    ), "Doesn't touch pyproject.toml (irrelevant for non-sdist)"  # fmt: skip
    assert (
        (build / "setup.py").read_text(encoding="utf-8") == (PROJECT_ROOT / "setup.py").read_text(encoding="utf-8")
    ), "Doesn't touch setup.py (irrelevant for non-sdist)"  # fmt: skip
    assert (
        (build / "streamlink" / "_version.py").read_text(encoding="utf-8") == '__version__ = "1.2.3+fake"\n'
    ), "streamlink._version exports a static version string"  # fmt: skip
