# Always get the current version in "editable" installs
# `pip install -e .` / `python setup.py develop`
def _get_version() -> str:
    from pathlib import Path
    from versioningit import get_version
    import streamlink

    return get_version(
        project_dir=Path(streamlink.__file__).parents[2]
    )


# The following _get_version() call will get replaced by versioningit with a static version string when building streamlink
# `pip install .` / `pip wheel .` / `python setup.py build` / `python setup.py bdist_wheel` / etc.
__version__ = _get_version()
