import re
import shutil
from pathlib import Path

import pytest

from build_backend.onbuild import onbuild


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
    shutil.copy(PROJECT_ROOT / "src" / "streamlink" / "_version.py", pkg_dir / "streamlink" / "_version.py")

    onbuild(tmp_path, is_source, template_fields, {})

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
    assert (build / "src" / "streamlink" / "_version.py").read_text(encoding="utf-8") \
        == "__version__ = \"1.2.3+fake\"\n", \
        "streamlink._version exports a static version string"


@pytest.mark.parametrize("build", [pytest.param({"is_source": False}, id="is_source=False")], indirect=True)
def test_bdist(build: Path):
    assert (build / "pyproject.toml").read_text(encoding="utf-8") \
        == (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"), \
        "Doesn't touch pyproject.toml (irrelevant for non-sdist)"
    assert (build / "setup.py").read_text(encoding="utf-8") \
        == (PROJECT_ROOT / "setup.py").read_text(encoding="utf-8"), \
        "Doesn't touch setup.py (irrelevant for non-sdist)"
    assert (build / "streamlink" / "_version.py").read_text(encoding="utf-8") \
        == "__version__ = \"1.2.3+fake\"\n", \
        "streamlink._version exports a static version string"
