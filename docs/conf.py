# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path

from streamlink import __version__ as streamlink_version


sys.path.insert(0, str(Path(__file__).resolve().parent / "sphinxext"))


# -- Project information -------------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Streamlink"
project_copyright = "2025, Streamlink"
author = "Streamlink"
version = streamlink_version.split("+")[0]
release = streamlink_version


# -- General configuration -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

needs_sphinx = "6.0"

extensions = [
    # Sphinx-internal
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.intersphinx",
    # third-party
    "myst_parser",
    "sphinx_design",
    # custom
    "ext_html_template_vars",
    "ext_argparse",
    "ext_github",
    "ext_plugins",
    "ext_releaseref",
]
if "no_intersphinx" in tags:  # type: ignore[name-defined]  # noqa: F821
    extensions.remove("sphinx.ext.intersphinx")

exclude_patterns = ["_build", "_applications.rst"]

templates_path = ["_templates"]


# -- Options for autodoc -------------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html

autodoc_default_options = {
    "show-inheritance": True,
    "members": True,
    "member-order": "groupwise",  # autodoc_member_order
    "class-doc-from": "both",  # autoclass_content
}
autodoc_inherit_docstrings = False
autodoc_typehints = "description"


# -- Options for autosectionlabel ----------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autosectionlabel.html

autosectionlabel_prefix_document = True


# -- Options for intersphinx ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html

intersphinx_mapping = {
    # "python": ("https://docs.python.org/3", None),
    "requests": ("https://requests.readthedocs.io/en/stable/", None),
}

intersphinx_timeout = 60


# -- Options for ext_github ----------------------------------------------------
# file://./sphinxext/ext_github.py

github_project = "streamlink/streamlink"


# -- Options for ext_html_template_vars ----------------------------------------
# file://./sphinxext/ext_html_template_vars.py

html_template_vars = {
    "oneliner": (
        "A command-line utility that extracts streams from various services and pipes them into a video player of choice."
    ),
}


# -- Options for HTML output ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_theme_options = {
    "source_repository": "https://github.com/streamlink/streamlink/",
    "source_branch": "master",
    "source_directory": "docs/",
    "light_logo": "icon.svg",
    "dark_logo": "icon.svg",
}

html_logo = "../icon.svg"

html_css_files = [
    "styles/custom.css",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.3.0/css/fontawesome.min.css",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.3.0/css/solid.min.css",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.3.0/css/brands.min.css",
]

html_static_path = ["_static"]

html_sidebars = {
    "**": [
        "sidebar/scroll-start.html",
        "sidebar/brand.html",
        "sidebar/search.html",
        "sidebar/navigation.html",
        "sidebar/github-buttons.html",
        "sidebar/scroll-end.html",
    ],
}
if "no_github_buttons" in tags:  # type: ignore[name-defined]  # noqa: F821
    html_sidebars.get("**", []).remove("sidebar/github-buttons.html")

html_domain_indices = False
html_show_sourcelink = False


# -- Options for manual page output --------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-manual-page-output

# Only include the man page in builds with the "man" tag set: via `-t man` (see Makefile)
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-tags
if "man" not in tags:  # type: ignore[name-defined]  # noqa: F821
    exclude_patterns.append("_man.rst")

man_pages = [
    (
        "_man",
        "streamlink",
        "extracts streams from various services and pipes them into a video player of choice",
        ["Streamlink Contributors"],
        1,
    ),
]

man_make_section_directory = False
