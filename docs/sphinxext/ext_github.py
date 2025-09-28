"""Creates Github links from @user and #issue text.

Bascially a much simplified version of sphinxcontrib.issuetracker
with support for @user.
"""

import re

from docutils import nodes
from docutils.transforms import Transform


GITHUB_ISSUE_URL = "https://github.com/{0}/issues/{1}"
GITHUB_USER_URL = "https://github.com/{1}"


class GithubReferences(Transform):
    default_priority = 999

    def apply(self):
        config = self.document.settings.env.config
        issue_re = re.compile(config.github_issue_pattern)
        mention_re = re.compile(config.github_mention_pattern)

        self._replace_pattern(issue_re, GITHUB_ISSUE_URL)
        self._replace_pattern(mention_re, GITHUB_USER_URL)

    def _replace_pattern(self, pattern, url_format):
        project = self.document.settings.env.config.github_project

        for node in self.document.traverse(nodes.Text):
            parent = node.parent
            if isinstance(parent, (nodes.reference, nodes.literal, nodes.FixedTextElement)):
                continue

            text = str(node)
            new_nodes = []
            last_ref_end = 0
            for match in pattern.finditer(text):
                head = text[last_ref_end : match.start()]
                if head:
                    new_nodes.append(nodes.Text(head))

                last_ref_end = match.end()
                ref = url_format.format(project, match.group(1))
                link = nodes.reference(
                    match.group(0),
                    match.group(0),
                    refuri=ref,
                )
                new_nodes.append(link)

            if not new_nodes:
                continue

            tail = text[last_ref_end:]
            if tail:
                new_nodes.append(nodes.Text(tail))

            parent.replace(node, new_nodes)


def setup(app):
    app.add_config_value("github_project", None, "env")
    app.add_config_value("github_issue_pattern", r"#(\d+)", "env")
    app.add_config_value("github_mention_pattern", r"@([\w-]+)", "env")
    app.add_transform(GithubReferences)
