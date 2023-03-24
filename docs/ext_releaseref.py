"""Creates links that allows substituting the current release
within the title or target."""

import os.path

from docutils import nodes
from sphinx.util.nodes import split_explicit_title


def releaseref_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    config = inliner.document.settings.env.config
    text = text.replace("|version|", config.version)
    text = text.replace("|release|", config.release)

    has_explicit_title, title, target = split_explicit_title(text)
    if not has_explicit_title:
        title = os.path.basename(target)

    node = nodes.reference(rawtext, title, refuri=target, **(options or {}))

    return [node], []


def setup(app):
    app.add_role("releaseref", releaseref_role)
