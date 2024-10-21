from __future__ import annotations

import re
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypeVar


try:
    # noinspection PyProtectedMember
    from versioningit.onbuild import SetuptoolsFileProvider  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover

    @dataclass
    class SetuptoolsFileProvider:  # type: ignore[no-redef]
        build_dir: Path


# noinspection PyUnusedLocal
def onbuild(
    *,
    is_source: bool,
    template_fields: dict[str, Any],
    params: dict[str, Any],
    # backward compatibility for `versioningit <3.0.0`
    build_dir: str | Path | None = None,
    file_provider: SetuptoolsFileProvider | None = None,
):
    """
    Remove the ``versioningit`` build-requirement from Streamlink's source distribution.
    Also set the static version string in the :mod:`streamlink._version` module when building the sdist/bdist.

    The version string already gets set by ``versioningit`` when building, so the sdist doesn't need to have
    ``versioningit`` added as a build-requirement. Previously, the generated version string was only applied
    to the :mod:`streamlink._version` module while ``versioningit`` was still set as a build-requirement.

    This custom onbuild hook gets called via the ``tool.versioningit.onbuild`` config in ``pyproject.toml``,
    since ``versioningit`` does only support modifying one file via its default onbuild hook configuration.
    """

    base_dir: Path
    if file_provider:
        base_dir = file_provider.build_dir.resolve()
    elif build_dir:  # pragma: no cover
        base_dir = Path(build_dir).resolve()
    else:  # pragma: no cover
        raise RuntimeError("Missing file_provider or build_dir")

    pkg_dir: Path = base_dir / "src" if is_source else base_dir
    version: str = template_fields["version"]
    cmproxy: Proxy[str]

    # Remove versioningit from ``build-system.requires`` in ``pyproject.toml``
    if is_source:
        with update_file(base_dir / "pyproject.toml") as cmproxy:
            cmproxy.set(
                re.sub(
                    r"^(\s*)(\"versioningit\b.+?\",).*$",
                    "\\1# \\2",
                    cmproxy.get(),
                    flags=re.MULTILINE,
                    count=1,
                ),
            )

    # Set the static version string that gets passed directly to setuptools via ``setup.py``.
    # This is much easier compared to adding the ``project.version`` field and removing "version" from ``project.dynamic``
    # in ``pyproject.toml``.
    if is_source:
        with update_file(base_dir / "setup.py") as cmproxy:
            cmproxy.set(
                re.sub(
                    r"^(\s*)# (version=\"\",).*$",
                    f'\\1version="{version}",',
                    cmproxy.get(),
                    flags=re.MULTILINE,
                    count=1,
                ),
            )

    # Overwrite the entire ``streamlink._version`` module
    with update_file(pkg_dir / "streamlink" / "_version.py") as cmproxy:
        cmproxy.set(f'__version__ = "{version}"\n')


TProxyItem = TypeVar("TProxyItem")


class Proxy(Generic[TProxyItem]):
    def __init__(self, data: TProxyItem):
        self._data = data

    def get(self) -> TProxyItem:
        return self._data

    def set(self, data: TProxyItem) -> None:
        self._data = data


@contextmanager
def update_file(file: Path) -> Generator[Proxy[str], None, None]:
    with file.open("r+", encoding="utf-8") as fh:
        proxy = Proxy(fh.read())
        yield proxy
        fh.seek(0)
        fh.write(proxy.get())
        fh.truncate()
