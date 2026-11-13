from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from docutils import nodes


if TYPE_CHECKING:
    from sphinx.application import Sphinx


_ROOT = Path(__file__).parent.parent


def remove_changelog_header(_app: Sphinx, doctree: nodes.document):
    file_path = Path(doctree.get("source")).relative_to(_ROOT)
    if str(file_path) != "changelog.md":
        return

    body = cast("nodes.section", doctree.children[0])
    # remove paragraph about old changelogs
    body.children = [child for child in body.children if isinstance(child, (nodes.title, nodes.section))]


def setup(app: Sphinx):
    app.connect("doctree-read", remove_changelog_header)

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
