from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, cast

from docutils import nodes


if TYPE_CHECKING:
    from sphinx.application import Sphinx


_ROOT = Path(__file__).parent.parent
_RE_RELEASE_TITLE = re.compile(r"^streamlink (?P<version>.+?) \((?P<date>\d{4}-\d{2}-\d{2})\)")


def fix_changelog(_app: Sphinx, doctree: nodes.document):
    match Path(doctree.get("source")).relative_to(_ROOT).parts:
        case ["changelog.md"]:
            strip_header_paragraph(doctree)
            fix_subsections(doctree)
        case ["changelog", file] if file.endswith(".md"):
            fix_subsections(doctree)


def strip_header_paragraph(doctree: nodes.document):
    body = cast("nodes.section", doctree.children[0])
    # remove paragraph about old changelogs
    body.children = [child for child in body.children if isinstance(child, (nodes.title, nodes.section))]


def fix_subsections(doctree: nodes.document):
    body = cast("nodes.section", doctree.children[0])

    for section in body.children:
        if (
            not isinstance(section, nodes.section)
            or not section.children
            or not (release_title := section.children[0])
            or not isinstance(release_title, nodes.title)
            or not (match := _RE_RELEASE_TITLE.match(release_title.astext()))
        ):
            continue

        subsection_title: nodes.title
        iterator = section.findall(lambda node: node is not release_title and isinstance(node, nodes.title))
        for subsection_title in iterator:  # type: ignore[assignment, ty:invalid-assignment]
            stack = _nested_subsection_titles(subsection_title, release_title)
            subsection_id = nodes.make_id("-".join([*reversed(stack), match["version"]]))
            subsection_title.parent["ids"] = [subsection_id]
            subsection_title.rawsource = subsection_id


def _nested_subsection_titles(node: nodes.title, release_title: nodes.title) -> list[str]:
    titles: list[str] = []
    while node is not release_title:
        titles.append(node.astext().strip())
        if node.parent and node.parent.parent and isinstance(parent_title := node.parent.parent[0], nodes.title):
            node = parent_title
        else:
            break

    return titles


def setup(app: Sphinx):
    # use a higher priority than autosectionlabel
    app.connect("doctree-read", fix_changelog, priority=400)

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
