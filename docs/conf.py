import os
import sys
from datetime import datetime


sys.path.insert(0, os.path.abspath(".."))

project = "Wove"
author = "curvedinf"
copyright = f"{datetime.now().year}, {author}"
release = "2.0.0"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autosummary_generate = True
napoleon_google_docstring = True
napoleon_numpy_docstring = False
autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": False,
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

html_theme = "shibuya"
html_title = "Wove Documentation"
html_logo = "_static/wove.svg"
html_favicon = "_static/wove.svg"
html_static_path = ["_static"]
html_css_files = ["wove-docs.css"]
html_theme_options = {
    "github_url": "https://github.com/curvedinf/wove",
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

nitpick_ignore = [
    ("py:class", "wove.helpers.R"),
]
